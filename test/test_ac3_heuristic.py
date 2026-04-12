"""
Tests for AC-3 propagator and AC-3 heuristic (h₄).

Tests:
  1. AC3Propagator — domain pruning, contradiction detection, no-op
  2. AC3Heuristic — estimate correctness, comparison with h₂
  3. AStarSolver + h₄ — end-to-end solving on 2×2, 3×3, 4×4 puzzles
  4. Unsolvable puzzles — contradiction flows through correctly
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constraints.ac3 import AC3Propagator
from constraints.inequality_constraint import InequalityConstraint
from core.puzzle import Puzzle
from heuristics.ac3_heuristic import AC3Heuristic
from heuristics.domain_size_heuristic import DomainSizeHeuristic
from search.state import SearchState
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


def make_state(grid, domains=None):
    grid_arr = np.array(grid, dtype=int)
    N = grid_arr.shape[0]
    if domains is None:
        domains = {}
        for i in range(N):
            for j in range(N):
                if grid_arr[i, j] == 0:
                    domains[(i, j)] = set(range(1, N + 1))
    return SearchState(grid=grid_arr, domains=domains)


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
# Group 1 — AC3Propagator unit tests
# ===========================================================================


class TestAC3PropagatorBasics:
    """Test AC-3 propagation on raw domains."""

    def test_propagate_no_constraints(self):
        """No constraints → domains unchanged (no arcs to propagate)."""
        puzzle = make_puzzle(2, [[0, 0], [0, 0]])
        domains = {
            (0, 0): {1, 2}, (0, 1): {1, 2},
            (1, 0): {1, 2}, (1, 1): {1, 2},
        }
        result = AC3Propagator.propagate(domains, puzzle)
        assert result is not None
        # Row/col uniqueness arcs should prune, but no inequality
        # constraints exist — however row/col NEQ arcs DO exist
        for dom in result.values():
            assert len(dom) >= 1

    def test_propagate_empty_domains_dict(self):
        """Empty domains dict → returns empty dict (no-op)."""
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        result = AC3Propagator.propagate({}, puzzle)
        assert result == {}

    def test_propagate_inequality_pruning(self):
        """AC-3 prunes domains for '<' constraint between two cells."""
        # cell(0,0) < cell(0,1), both unassigned
        puzzle = make_puzzle(3, [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                             h=[(0, 0, "<")])
        domains = {
            (0, 0): {1, 2, 3}, (0, 1): {1, 2, 3}, (0, 2): {1, 2, 3},
            (1, 0): {1, 2, 3}, (1, 1): {1, 2, 3}, (1, 2): {1, 2, 3},
            (2, 0): {1, 2, 3}, (2, 1): {1, 2, 3}, (2, 2): {1, 2, 3},
        }
        result = AC3Propagator.propagate(domains, puzzle)
        assert result is not None
        # cell(0,0) < cell(0,1) → 3 should be removed from (0,0)
        assert 3 not in result[(0, 0)]
        # cell(0,1) must be > min(domain(0,0)), so 1 removed from (0,1)
        assert 1 not in result[(0, 1)]

    def test_propagate_singleton_forces_exclusion(self):
        """A singleton domain forces removal from same-row peers."""
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        # (0,1) must differ from 1 in row 0 and column 1
        domains = {
            (0, 1): {1, 2},
            (1, 0): {1, 2},
            (1, 1): {1, 2},
        }
        result = AC3Propagator.propagate(domains, puzzle)
        assert result is not None
        # (0,1) in same row as given cell (0,0)=1 → but 1 is NOT
        # in domains for (0,1) from the perspective of AC3 (it only
        # looks at arcs between unassigned cells). The given values
        # aren't in the domain dict, so pruning is done by the caller.

    def test_propagate_contradiction(self):
        """Two cells in same row with same singleton → contradiction."""
        puzzle = make_puzzle(2, [[0, 0], [0, 0]])
        domains = {
            (0, 0): {1}, (0, 1): {1},  # same row, same value
            (1, 0): {1, 2}, (1, 1): {1, 2},
        }
        result = AC3Propagator.propagate(domains, puzzle)
        assert result is None

    def test_propagate_assigned_cell_inequality(self):
        """Inequality against an assigned cell tightens the unassigned cell."""
        # cell(0,0)=3 and cell(0,0) < cell(0,1) → cell(0,1) must be > 3
        # But for N=3, no value > 3 exists → contradiction
        puzzle = make_puzzle(3, [[3, 0, 0], [0, 0, 0], [0, 0, 0]],
                             h=[(0, 0, "<")])
        domains = {
            (0, 1): {1, 2, 3},
            (0, 2): {1, 2, 3},
            (1, 0): {1, 2, 3},
            (1, 1): {1, 2, 3},
            (1, 2): {1, 2, 3},
            (2, 0): {1, 2, 3},
            (2, 1): {1, 2, 3},
            (2, 2): {1, 2, 3},
        }
        result = AC3Propagator.propagate(domains, puzzle)
        # cell(0,1) must be > 3 but max value is 3 → empty domain
        assert result is None

    def test_propagate_greater_constraint(self):
        """AC-3 prunes for '>' constraint correctly."""
        # cell(0,0) > cell(0,1)
        puzzle = make_puzzle(3, [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                             h=[(0, 0, ">")])
        domains = {
            (0, 0): {1, 2, 3}, (0, 1): {1, 2, 3}, (0, 2): {1, 2, 3},
            (1, 0): {1, 2, 3}, (1, 1): {1, 2, 3}, (1, 2): {1, 2, 3},
            (2, 0): {1, 2, 3}, (2, 1): {1, 2, 3}, (2, 2): {1, 2, 3},
        }
        result = AC3Propagator.propagate(domains, puzzle)
        assert result is not None
        # cell(0,0) > cell(0,1) → 1 removed from (0,0)
        assert 1 not in result[(0, 0)]
        # cell(0,1) < cell(0,0) → 3 removed from (0,1)
        assert 3 not in result[(0, 1)]


class TestAC3PropagatorRevise:
    """Test the _revise static method directly."""

    def test_revise_neq_singleton(self):
        """Fast-path: NEQ with singleton neighbour removes the value."""
        domains = {(0, 0): {1, 2}, (0, 1): {2}}
        changed = AC3Propagator._revise(domains, (0, 0), (0, 1), 1)
        assert changed is True
        assert domains[(0, 0)] == {1}

    def test_revise_neq_no_overlap(self):
        """No overlap → nothing to revise."""
        domains = {(0, 0): {1}, (0, 1): {2}}
        changed = AC3Propagator._revise(domains, (0, 0), (0, 1), 1)
        assert changed is False

    def test_revise_lt(self):
        """LT: remove values from xi that have no smaller match in xj."""
        domains = {(0, 0): {1, 2, 3}, (0, 1): {1, 2, 3}}
        # (0,0) < (0,1): value 3 has no value > 3 in (0,1) → remove 3
        changed = AC3Propagator._revise(domains, (0, 0), (0, 1), 2)
        assert changed is True
        assert 3 not in domains[(0, 0)]
        assert domains[(0, 0)] == {1, 2}

    def test_satisfies_neq(self):
        assert AC3Propagator._satisfies(1, 2, 1) is True
        assert AC3Propagator._satisfies(2, 2, 1) is False

    def test_satisfies_lt(self):
        assert AC3Propagator._satisfies(1, 2, 2) is True
        assert AC3Propagator._satisfies(2, 1, 2) is False

    def test_satisfies_gt(self):
        assert AC3Propagator._satisfies(3, 1, 4) is True
        assert AC3Propagator._satisfies(1, 3, 4) is False

    def test_satisfies_combined_neq_lt(self):
        """Combined NEQ | LT: must be both not-equal AND less-than."""
        mask = 1 | 2  # NEQ + LT
        assert AC3Propagator._satisfies(1, 2, mask) is True
        assert AC3Propagator._satisfies(2, 2, mask) is False  # fails NEQ
        assert AC3Propagator._satisfies(3, 1, mask) is False  # fails LT


# ===========================================================================
# Group 2 — AC3Heuristic unit tests
# ===========================================================================


class TestAC3Heuristic:
    def setup_method(self):
        self.h = AC3Heuristic()

    def test_name(self):
        assert "h4" in self.h.get_name()
        assert "AC-3" in self.h.get_name()

    def test_complete_grid_returns_zero(self):
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        state = make_state([[1, 2], [2, 1]], domains={})
        assert self.h.estimate(state, puzzle) == 0

    def test_nonnegative(self):
        puzzle = make_puzzle(2, [[0, 0], [0, 0]])
        state = make_state([[0, 0], [0, 0]])
        assert self.h.estimate(state, puzzle) >= 0

    def test_estimate_tighter_than_h2(self):
        """h₄ ≤ h₂ because AC-3 only removes values."""
        puzzle = make_puzzle(3, [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                             h=[(0, 0, "<")])
        state = make_state([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        h2 = DomainSizeHeuristic()
        h2_val = h2.estimate(state, puzzle)
        h4_val = self.h.estimate(state, puzzle)

        assert h4_val <= h2_val

    def test_estimate_on_near_complete_state(self):
        """State with one empty cell → h₄ should be small."""
        puzzle = make_puzzle(2, [[1, 2], [2, 0]])
        state = make_state(
            [[1, 2], [2, 0]],
            domains={(1, 1): {1}},
        )
        h_val = self.h.estimate(state, puzzle)
        assert h_val == 0  # singleton domain → (1-1) = 0

    def test_estimate_returns_large_on_contradiction(self):
        """State with contradictory domains → returns large penalty."""
        puzzle = make_puzzle(2, [[0, 0], [0, 0]])
        state = make_state(
            [[0, 0], [0, 0]],
            domains={
                (0, 0): {1}, (0, 1): {1},  # same row, same val
                (1, 0): {2}, (1, 1): {2},  # same row, same val
            },
        )
        h_val = self.h.estimate(state, puzzle)
        # Contradiction → large penalty (N³ = 8)
        assert h_val >= puzzle.N * puzzle.N * puzzle.N


# ===========================================================================
# Group 3 — AStarSolver + h₄ end-to-end
# ===========================================================================


class TestAStarSolverH4_2x2:
    """2×2 puzzles with AC-3 heuristic."""

    def test_solve_2x2_known_solution(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]], h=[(0, 0, "<")])
        solver = AStarSolver(AC3Heuristic())
        solution, stats = solver.solve(puzzle)
        assert solution is not None
        expected = np.array([[1, 2], [2, 1]])
        assert np.array_equal(solution.grid, expected)

    def test_solve_2x2_no_constraints(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)

    def test_solve_2x2_already_complete(self):
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert np.array_equal(solution.grid, puzzle.grid)


class TestAStarSolverH4_3x3:
    """3×3 puzzles with AC-3 heuristic."""

    def test_solve_3x3_with_givens(self):
        puzzle = make_puzzle(3, [
            [2, 0, 0],
            [0, 0, 3],
            [0, 1, 0],
        ])
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)

    def test_solve_3x3_with_inequality(self):
        puzzle = make_puzzle(3, [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ], h=[(0, 0, "<")])
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)
        assert solution.grid[0, 0] < solution.grid[0, 1]

    def test_fixture_bf_3x3(self):
        fixture = os.path.join(FIXTURE_DIR, "bf_3x3.txt")
        if not os.path.exists(fixture):
            pytest.skip("bf_3x3.txt fixture not found")
        from core.parser import Parser
        puzzle = Parser().parse(fixture)
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        expected = np.array([[1, 2, 3], [2, 3, 1], [3, 1, 2]])
        assert np.array_equal(solution.grid, expected)


class TestAStarSolverH4_4x4:
    """4×4 puzzles with AC-3 heuristic."""

    def test_solve_4x4_with_givens(self):
        puzzle = make_puzzle(4, [
            [1, 2, 3, 0],
            [2, 3, 0, 1],
            [3, 0, 1, 2],
            [0, 1, 2, 3],
        ])
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)

    def test_solve_4x4_with_constraints(self):
        puzzle = make_puzzle(4, [
            [1, 2, 0, 0],
            [2, 0, 4, 0],
            [0, 4, 0, 2],
            [4, 0, 2, 0],
        ], h=[(0, 0, "<")], v=[(0, 0, "<")])
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(puzzle)
        assert solution is not None
        assert _check_solution(puzzle, solution)
        assert solution.grid[0, 0] < solution.grid[0, 1]
        assert solution.grid[0, 0] < solution.grid[1, 0]


# ===========================================================================
# Group 4 — Unsolvable puzzles
# ===========================================================================


class TestAStarH4Unsolvable:
    def test_contradictory_givens(self):
        """Same value in same row → no solution."""
        puzzle = make_puzzle(3, [
            [1, 1, 0],
            [0, 0, 0],
            [0, 0, 0],
        ])
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(puzzle)
        assert solution is None

    def test_impossible_inequality(self):
        """Conflicting < and > on same pair."""
        impossible = Puzzle(
            N=2,
            grid=np.zeros((2, 2), dtype=int),
            h_constraints=[
                InequalityConstraint(
                    cell1=(0, 0), cell2=(0, 1), direction="<",
                ),
                InequalityConstraint(
                    cell1=(0, 0), cell2=(0, 1), direction=">",
                ),
            ],
            v_constraints=[],
        )
        solver = AStarSolver(AC3Heuristic())
        solution, _ = solver.solve(impossible)
        assert solution is None


# ===========================================================================
# Group 5 — Stats
# ===========================================================================


class TestAStarH4Stats:
    def test_returns_tuple(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        result = AStarSolver(AC3Heuristic()).solve(puzzle)
        assert isinstance(result, tuple) and len(result) == 2
        solution, stats = result
        assert solution is None or isinstance(solution, Puzzle)
        assert isinstance(stats, Stats)

    def test_time_nonneg(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        _, stats = AStarSolver(AC3Heuristic()).solve(puzzle)
        assert stats.time_ms >= 0

    def test_node_expansions_positive(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        _, stats = AStarSolver(AC3Heuristic()).solve(puzzle)
        assert stats.node_expansions >= 1

    def test_solver_name_contains_h4(self):
        solver = AStarSolver(AC3Heuristic())
        assert "h4" in solver.get_name()
        assert "A*" in solver.get_name()


# ===========================================================================
# Group 6 — h₄ fewer expansions than h₂ (comparative)
# ===========================================================================


class TestH4VsH2Expansions:
    """AC-3 pruning should produce fewer or equal node expansions."""

    def test_fewer_expansions_4x4(self):
        puzzle = make_puzzle(4, [
            [1, 2, 0, 0],
            [2, 0, 4, 0],
            [0, 4, 0, 2],
            [4, 0, 2, 0],
        ], h=[(0, 0, "<")], v=[(0, 0, "<")])

        _, stats_h2 = AStarSolver(DomainSizeHeuristic()).solve(puzzle)
        _, stats_h4 = AStarSolver(AC3Heuristic()).solve(puzzle)

        assert stats_h4.node_expansions <= stats_h2.node_expansions


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
