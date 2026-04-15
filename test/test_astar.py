"""
Tests for A* Search Solver (AStarSolver) and engine components.

Tests:
  1. SearchState — ordering, completeness, copy, hashing
  2. AStarEngine — domain initialisation, violation counting, MRV
  3. AStarSolver — end-to-end solving on 2x2, 3x3, 4x4 puzzles
  4. Solution properties — row/col uniqueness, constraint satisfaction
  5. Unsolvable puzzles — contradiction detection
  6. Stats — node expansions, timing
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constraints.inequality_constraint import InequalityConstraint
from core.parser import Parser
from core.puzzle import Puzzle
from heuristics import (
    EmptyCellHeuristic,
    DomainSizeHeuristic,
    MinConflictsHeuristic,
)
from search.state import SearchState
from search.astar import AStarEngine
from solver.astar_solver import AStarSolver
from utils import Stats

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# ===========================================================================
# Helpers
# ===========================================================================


def make_puzzle(N, grid, h=None, v=None):
    h_constraints = [
        InequalityConstraint(cell1=(r, c), cell2=(r, c + 1), direction=d)
        for r, c, d in (h or [])
    ]
    v_constraints = [
        InequalityConstraint(cell1=(r, c), cell2=(r + 1, c), direction=d)
        for r, c, d in (v or [])
    ]
    return Puzzle(
        N=N,
        grid=np.array(grid, dtype=int),
        h_constraints=h_constraints,
        v_constraints=v_constraints,
    )


def _check_solution(puzzle, solved):
    """Return True if solved satisfies all Futoshiki rules."""
    N = solved.N
    g = solved.grid
    if np.any(g == 0):
        return False
    for i in range(N):
        if sorted(g[i]) != list(range(1, N + 1)):
            return False
    for j in range(N):
        if sorted(g[:, j]) != list(range(1, N + 1)):
            return False
    for c in puzzle.h_constraints + puzzle.v_constraints:
        if not c.is_satisfied(solved):
            return False
    return True


# ===========================================================================
# Group 1 — SearchState
# ===========================================================================


class TestSearchState:
    def test_f_property(self):
        state = SearchState(
            grid=np.zeros((2, 2), dtype=int), domains={}, g=3, h=5,
        )
        assert state.f == 8

    def test_is_complete_true(self):
        state = SearchState(
            grid=np.array([[1, 2], [2, 1]]), domains={},
        )
        assert state.is_complete

    def test_is_complete_false(self):
        state = SearchState(
            grid=np.array([[1, 0], [2, 1]]), domains={},
        )
        assert not state.is_complete

    def test_ordering_by_f(self):
        s1 = SearchState(grid=np.zeros((2,2), dtype=int), domains={}, g=1, h=2)
        s2 = SearchState(grid=np.zeros((2,2), dtype=int), domains={}, g=2, h=3)
        assert s1 < s2  # f=3 < f=5

    def test_ordering_tie_break_by_g(self):
        s1 = SearchState(grid=np.zeros((2,2), dtype=int), domains={}, g=1, h=3)
        s2 = SearchState(grid=np.zeros((2,2), dtype=int), domains={}, g=2, h=2)
        # Both f=4; s1.g=1 < s2.g=2 → s1 wins
        assert s1 < s2

    def test_copy_independence(self):
        state = SearchState(
            grid=np.array([[1, 0], [0, 0]]),
            domains={(0, 1): {2}, (1, 0): {2}, (1, 1): {1, 2}},
        )
        child = state.copy()
        child.grid[0, 1] = 2
        child.domains[(1, 1)].discard(2)

        assert state.grid[0, 1] == 0  # original unchanged
        assert 2 in state.domains[(1, 1)]  # original unchanged

    def test_hash_equal_for_same_grid(self):
        s1 = SearchState(grid=np.array([[1, 2], [2, 1]]), domains={})
        s2 = SearchState(grid=np.array([[1, 2], [2, 1]]), domains={})
        assert hash(s1) == hash(s2)
        assert s1 == s2

    def test_hash_different_for_different_grid(self):
        s1 = SearchState(grid=np.array([[1, 2], [2, 1]]), domains={})
        s2 = SearchState(grid=np.array([[2, 1], [1, 2]]), domains={})
        assert s1 != s2

    def test_unassigned_cells(self):
        state = SearchState(
            grid=np.array([[1, 0], [0, 1]]), domains={},
        )
        cells = state.unassigned_cells
        assert sorted(cells) == [(0, 1), (1, 0)]


# ===========================================================================
# Group 2 — AStarEngine internals
# ===========================================================================


class TestAStarEngineInternals:
    def test_compute_violations_valid(self):
        grid = np.array([[1, 2], [2, 1]])
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        violations = AStarEngine._compute_violations(grid, 2, puzzle)
        assert violations == 0

    def test_compute_violations_row_dup(self):
        grid = np.array([[1, 1], [2, 2]])
        puzzle = make_puzzle(2, grid.tolist())
        violations = AStarEngine._compute_violations(grid, 2, puzzle)
        assert violations >= 2  # row dups + col dups

    def test_compute_violations_inequality(self):
        # cell(0,0) < cell(0,1) but 2 < 1 is False → 1 violation
        grid = np.array([[2, 1], [1, 2]])
        puzzle = make_puzzle(2, grid.tolist(), h=[(0, 0, "<")])
        violations = AStarEngine._compute_violations(grid, 2, puzzle)
        assert violations >= 1

    def test_mrv_selects_smallest_domain(self):
        state = SearchState(
            grid=np.array([[0, 0], [0, 0]]),
            domains={
                (0, 0): {1, 2},
                (0, 1): {1},
                (1, 0): {1, 2},
                (1, 1): {1, 2},
            },
        )
        cell = AStarEngine._select_mrv_cell(state)
        assert cell == (0, 1)  # domain size = 1

    def test_eliminate_from_peers_row(self):
        domains = {(0, 1): {1, 2, 3}}
        grid = np.array([[1, 0, 0]])
        puzzle = make_puzzle(1, [[1, 0, 0]])  # N doesn't matter for the test
        AStarEngine._eliminate_from_peers(
            domains, grid, 3, 0, 0, 1, puzzle,
        )
        assert 1 not in domains[(0, 1)]


# ===========================================================================
# Group 3 — AStarSolver end-to-end
# ===========================================================================


class TestAStarSolver2x2:
    """2x2 puzzles — fast, covers basic correctness."""

    def test_solve_with_h1(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]], h=[(0, 0, "<")])
        solver = AStarSolver(EmptyCellHeuristic())
        solution, stats = solver.solve(puzzle)
        assert solution is not None
        assert solution.is_complete()
        assert _check_solution(puzzle, solution)

    def test_solve_with_h2(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]], h=[(0, 0, "<")])
        solver = AStarSolver(DomainSizeHeuristic())
        solution, stats = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)

    def test_solve_with_h3(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]], h=[(0, 0, "<")])
        solver = AStarSolver(MinConflictsHeuristic())
        solution, stats = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)

    def test_known_solution(self):
        """2x2 with given (0,0)=1 and (0,0)<(0,1) → [[1,2],[2,1]]."""
        puzzle = make_puzzle(2, [[1, 0], [0, 0]], h=[(0, 0, "<")])
        solver = AStarSolver()
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        expected = np.array([[1, 2], [2, 1]])
        assert np.array_equal(solution.grid, expected)

    def test_already_complete(self):
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        solver = AStarSolver()
        solution, stats = solver.solve(puzzle)
        assert solution is not None
        assert np.array_equal(solution.grid, puzzle.grid)


class TestAStarSolver3x3:
    """3x3 puzzles — moderate complexity."""

    def test_solve_no_constraints(self):
        puzzle = make_puzzle(3, [
            [2, 0, 0],
            [0, 0, 3],
            [0, 1, 0],
        ])
        solver = AStarSolver()
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)

    def test_solve_with_inequality(self):
        puzzle = make_puzzle(3, [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ], h=[(0, 0, "<")])
        solver = AStarSolver()
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)
        assert solution.grid[0, 0] < solution.grid[0, 1]

    def test_fixture_bf_3x3(self):
        fixture = os.path.join(FIXTURE_DIR, "bf_3x3.txt")
        if not os.path.exists(fixture):
            pytest.skip("bf_3x3.txt fixture not found")
        puzzle = Parser().parse(fixture)
        solver = AStarSolver()
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        expected = np.array([[1, 2, 3], [2, 3, 1], [3, 1, 2]])
        assert np.array_equal(solution.grid, expected)


class TestAStarSolver4x4:
    """4x4 puzzle to test scalability."""

    def test_solve_with_givens(self):
        puzzle = make_puzzle(4, [
            [1, 2, 3, 0],
            [2, 3, 0, 1],
            [3, 0, 1, 2],
            [0, 1, 2, 3],
        ])
        solver = AStarSolver()
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)

    def test_solve_with_constraints(self):
        puzzle = make_puzzle(4, [
            [1, 2, 0, 0],
            [2, 0, 4, 0],
            [0, 4, 0, 2],
            [4, 0, 2, 0],
        ], h=[(0, 0, "<")], v=[(0, 0, "<")])
        solver = AStarSolver()
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)
        assert solution.grid[0, 0] < solution.grid[0, 1]
        assert solution.grid[0, 0] < solution.grid[1, 0]


# ===========================================================================
# Group 4 — Solution properties
# ===========================================================================


class TestSolutionProperties:
    def test_no_empty_cells(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]], h=[(0, 0, "<")])
        solution, _ = AStarSolver().solve(puzzle)
        assert solution is not None
        assert not np.any(solution.grid == 0)

    def test_given_cells_preserved(self):
        puzzle = make_puzzle(3, [
            [2, 0, 0],
            [0, 0, 3],
            [0, 1, 0],
        ])
        solution, _ = AStarSolver().solve(puzzle)
        assert solution is not None
        assert solution.grid[0, 0] == 2
        assert solution.grid[1, 2] == 3
        assert solution.grid[2, 1] == 1

    def test_row_uniqueness(self):
        puzzle = make_puzzle(3, [[2, 0, 0], [0, 0, 3], [0, 1, 0]])
        solution, _ = AStarSolver().solve(puzzle)
        assert solution is not None
        N = solution.N
        for i in range(N):
            assert sorted(solution.grid[i]) == list(range(1, N + 1))

    def test_col_uniqueness(self):
        puzzle = make_puzzle(3, [[2, 0, 0], [0, 0, 3], [0, 1, 0]])
        solution, _ = AStarSolver().solve(puzzle)
        assert solution is not None
        N = solution.N
        for j in range(N):
            assert sorted(solution.grid[:, j]) == list(range(1, N + 1))


# ===========================================================================
# Group 5 — Unsolvable puzzles
# ===========================================================================


class TestUnsolvable:
    def test_contradictory_givens(self):
        """Same value in same row → no solution."""
        puzzle = make_puzzle(3, [
            [1, 1, 0],
            [0, 0, 0],
            [0, 0, 0],
        ])
        solution, _ = AStarSolver().solve(puzzle)
        assert solution is None

    def test_impossible_inequality(self):
        """Conflicting < and > on same pair."""
        impossible = Puzzle(
            N=2,
            grid=np.zeros((2, 2), dtype=int),
            h_constraints=[
                InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction="<"),
                InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction=">"),
            ],
            v_constraints=[],
        )
        solution, _ = AStarSolver().solve(impossible)
        assert solution is None


# ===========================================================================
# Group 6 — Stats
# ===========================================================================


class TestStats:
    def test_returns_tuple(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        result = AStarSolver().solve(puzzle)
        assert isinstance(result, tuple) and len(result) == 2
        solution, stats = result
        assert solution is None or isinstance(solution, Puzzle)
        assert isinstance(stats, Stats)

    def test_time_nonneg(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        _, stats = AStarSolver().solve(puzzle)
        assert stats.time_ms >= 0

    def test_node_expansions_positive(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        _, stats = AStarSolver().solve(puzzle)
        assert stats.node_expansions >= 1

    def test_memory_nonneg(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        _, stats = AStarSolver().solve(puzzle)
        assert stats.memory_kb >= 0

    def test_solver_name_contains_astar(self):
        solver = AStarSolver()
        assert "A*" in solver.get_name()

    def test_solver_name_contains_heuristic(self):
        solver = AStarSolver(EmptyCellHeuristic())
        assert "h1" in solver.get_name()


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
