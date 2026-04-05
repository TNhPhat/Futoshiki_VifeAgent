"""Tests for BruteForceSolver.

Fixture: test/fixtures/bf_3x3.txt
    Grid:
        1  .  3
        .  .  .
        .  .  .
    H-constraints: h(1,0) '<'  (grid(1,0) < grid(1,1))
    V-constraints: none
    Unique solution:
        1  2  3
        2  3  1
        3  1  2
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from constraints.inequality_constraint import InequalityConstraint
from core.parser import Parser
from core.puzzle import Puzzle
from solver.brute_force import BruteForceSolver
from utils import Stats

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "bf_3x3.txt")

# Known correct solution for the bf_3x3 fixture (unique)
FIXTURE_SOLUTION = np.array([
    [1, 2, 3],
    [2, 3, 1],
    [3, 1, 2],
], dtype=int)


# ===========================================================================
# Helpers
# ===========================================================================


def make_puzzle(N: int, grid: list[list[int]],
                h: list[tuple] = [],
                v: list[tuple] = []) -> Puzzle:
    """Build a Puzzle from plain lists. h/v are (i,j,direction) triples."""
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


def _check_solution(puzzle: Puzzle, solved: Puzzle) -> bool:
    """Return True if solved satisfies all Futoshiki rules."""
    N = solved.N
    g = solved.grid
    # No empty cells
    if np.any(g == 0):
        return False
    # Row uniqueness
    for i in range(N):
        if sorted(g[i]) != list(range(1, N + 1)):
            return False
    # Column uniqueness
    for j in range(N):
        if sorted(g[:, j]) != list(range(1, N + 1)):
            return False
    # Inequality constraints
    for c in puzzle.h_constraints + puzzle.v_constraints:
        if not c.is_satisfied(solved):
            return False
    return True


# ===========================================================================
# Group 1 — Solver identity
# ===========================================================================


def test_solver_name():
    assert BruteForceSolver().get_name() == "BruteForce"


def test_solve_returns_tuple():
    puzzle = make_puzzle(2, [[1, 2], [2, 1]])
    result = BruteForceSolver().solve(puzzle)
    assert isinstance(result, tuple) and len(result) == 2
    solution, stats = result
    assert solution is None or isinstance(solution, Puzzle)
    assert isinstance(stats, Stats)


# ===========================================================================
# Group 2 — Trivial / edge cases
# ===========================================================================


def test_already_complete_valid():
    """A fully filled valid 2×2 puzzle should be returned as-is in 1 expansion."""
    puzzle = make_puzzle(2, [[1, 2], [2, 1]])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert np.array_equal(solution.grid, puzzle.grid)
    assert stats.node_expansions == 1


def test_already_complete_invalid():
    """A fully filled puzzle with a row violation must return None."""
    # Row 0 has two 1s — invalid
    puzzle = make_puzzle(2, [[1, 1], [2, 2]])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is None


def test_single_empty_cell():
    """Only one empty cell — exactly one valid value fills it."""
    # 3×3: all cells given except (2,2); row 2 = [3, 1, ?], col 2 = [1, 3, ?] → must be 2
    puzzle = make_puzzle(3, [
        [2, 3, 1],
        [1, 2, 3],
        [3, 1, 0],
    ])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert solution.grid[2, 2] == 2
    assert stats.node_expansions <= 3  # tries at most N values


# ===========================================================================
# Group 3 — Correctness on small puzzles
# ===========================================================================


def test_2x2_no_constraints():
    """2×2 all-empty puzzle with no constraints — must find a valid Latin square."""
    puzzle = make_puzzle(2, [[0, 0], [0, 0]])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert _check_solution(puzzle, solution)


def test_3x3_no_constraints_with_givens():
    """3×3 with three givens and no inequalities — solution must be valid."""
    puzzle = make_puzzle(3, [
        [2, 0, 0],
        [0, 0, 3],
        [0, 1, 0],
    ])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert _check_solution(puzzle, solution)


def test_3x3_with_h_inequality():
    """3×3 with a single horizontal < constraint — solution must respect it."""
    puzzle = make_puzzle(3, [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ], h=[(0, 0, "<")])  # cell(0,0) < cell(0,1)
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert _check_solution(puzzle, solution)
    assert solution.grid[0, 0] < solution.grid[0, 1]


def test_3x3_with_v_inequality():
    """3×3 with a single vertical < constraint — solution must respect it."""
    puzzle = make_puzzle(3, [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ], v=[(0, 0, "<")])  # cell(0,0) < cell(1,0)
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert _check_solution(puzzle, solution)
    assert solution.grid[0, 0] < solution.grid[1, 0]


def test_3x3_fixture():
    """Parse the 3×3 fixture and verify the solver produces the known solution."""
    puzzle = Parser().parse(FIXTURE)
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None, "Fixture puzzle must be solvable"
    assert np.array_equal(solution.grid, FIXTURE_SOLUTION), (
        f"Expected:\n{FIXTURE_SOLUTION}\nGot:\n{solution.grid}"
    )


def test_4x4_with_givens():
    """4×4 puzzle with 12 givens (4 empty cells = 4^4=256 combinations).

    Solution (cyclic Latin square):
        1 2 3 4
        2 3 4 1
        3 4 1 2
        4 1 2 3
    One value per row/column is left empty; each is uniquely determined.
    """
    puzzle = make_puzzle(4, [
        [1, 2, 3, 0],
        [2, 3, 0, 1],
        [3, 0, 1, 2],
        [0, 1, 2, 3],
    ])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert _check_solution(puzzle, solution)
    expected = np.array([
        [1, 2, 3, 4],
        [2, 3, 4, 1],
        [3, 4, 1, 2],
        [4, 1, 2, 3],
    ], dtype=int)
    assert np.array_equal(solution.grid, expected)


def test_4x4_with_constraints():
    """4×4 with 8 givens and two inequality constraints.

    Base solution:
        1 2 3 4
        2 3 4 1
        3 4 1 2
        4 1 2 3
    Constraints added:
        h(0,0): grid(0,0) < grid(0,1)  → 1 < 2  (satisfied)
        v(0,0): grid(0,0) < grid(1,0)  → 1 < 2  (satisfied)
    """
    puzzle = make_puzzle(4, [
        [1, 2, 0, 0],
        [2, 0, 4, 0],
        [0, 4, 0, 2],
        [4, 0, 2, 0],
    ], h=[(0, 0, "<")], v=[(0, 0, "<")])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert _check_solution(puzzle, solution)
    assert solution.grid[0, 0] < solution.grid[0, 1]
    assert solution.grid[0, 0] < solution.grid[1, 0]


def test_5x5_with_givens():
    """5×5 puzzle with 20 givens (5 empty cells = 5^5=3125 combinations).

    Solution (cyclic Latin square):
        1 2 3 4 5
        2 3 4 5 1
        3 4 5 1 2
        4 5 1 2 3
        5 1 2 3 4
    One cell per row/column (main anti-diagonal) is left empty.
    """
    puzzle = make_puzzle(5, [
        [1, 2, 3, 4, 0],
        [2, 3, 4, 0, 1],
        [3, 4, 0, 1, 2],
        [4, 0, 1, 2, 3],
        [0, 1, 2, 3, 4],
    ])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert _check_solution(puzzle, solution)
    expected = np.array([
        [1, 2, 3, 4, 5],
        [2, 3, 4, 5, 1],
        [3, 4, 5, 1, 2],
        [4, 5, 1, 2, 3],
        [5, 1, 2, 3, 4],
    ], dtype=int)
    assert np.array_equal(solution.grid, expected)


def test_5x5_with_constraints():
    """5×5 with 16 givens and inequality constraints.

    Base solution:
        1 2 3 4 5
        2 3 4 5 1
        3 4 5 1 2
        4 5 1 2 3
        5 1 2 3 4
    Constraints:
        h(0,0): grid(0,0) < grid(0,1)  → 1 < 2
        v(3,4): grid(3,4) < grid(4,4)  → 3 < 4
    """
    puzzle = make_puzzle(5, [
        [1, 2, 3, 4, 0],
        [2, 3, 4, 0, 1],
        [3, 4, 0, 1, 2],
        [4, 0, 1, 2, 0],
        [0, 1, 2, 3, 4],
    ], h=[(0, 0, "<")], v=[(3, 4, "<")])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert _check_solution(puzzle, solution)
    assert solution.grid[0, 0] < solution.grid[0, 1]
    assert solution.grid[3, 4] < solution.grid[4, 4]


# ===========================================================================
# Group 4 — Solution properties
# ===========================================================================


def test_no_empty_cells():
    """The returned grid must have no zeros."""
    puzzle = Parser().parse(FIXTURE)
    solution, _ = BruteForceSolver().solve(puzzle)
    assert solution is not None
    assert not np.any(solution.grid == 0)


def test_row_uniqueness():
    """Each row of the solution must be a permutation of 1..N."""
    puzzle = Parser().parse(FIXTURE)
    solution, _ = BruteForceSolver().solve(puzzle)
    assert solution is not None
    N = solution.N
    for i in range(N):
        assert sorted(solution.grid[i]) == list(range(1, N + 1)), \
            f"Row {i} not a permutation: {solution.grid[i]}"


def test_col_uniqueness():
    """Each column of the solution must be a permutation of 1..N."""
    puzzle = Parser().parse(FIXTURE)
    solution, _ = BruteForceSolver().solve(puzzle)
    assert solution is not None
    N = solution.N
    for j in range(N):
        assert sorted(solution.grid[:, j]) == list(range(1, N + 1)), \
            f"Col {j} not a permutation: {solution.grid[:, j]}"


def test_inequality_constraints_satisfied():
    """All InequalityConstraint.is_satisfied() must return True on the solution."""
    puzzle = Parser().parse(FIXTURE)
    solution, _ = BruteForceSolver().solve(puzzle)
    assert solution is not None
    for c in puzzle.h_constraints + puzzle.v_constraints:
        assert c.is_satisfied(solution), (
            f"Constraint {c.cell1} {c.direction} {c.cell2} not satisfied"
        )


def test_given_cells_preserved():
    """Given cells must keep their original values in the solution."""
    puzzle = Parser().parse(FIXTURE)
    solution, _ = BruteForceSolver().solve(puzzle)
    assert solution is not None
    for i, j, v in puzzle.get_given_cells():
        assert solution.grid[i, j] == v, \
            f"Given cell ({i},{j}) expected {v}, got {solution.grid[i, j]}"


# ===========================================================================
# Group 5 — Unsolvable puzzles
# ===========================================================================


def test_contradictory_givens():
    """Two cells in the same row with the same value — no solution exists."""
    # Row 0: [1, 1, ?] — row duplicate, unsolvable
    puzzle = make_puzzle(3, [
        [1, 1, 0],
        [0, 0, 0],
        [0, 0, 0],
    ])
    solution, stats = BruteForceSolver().solve(puzzle)
    assert solution is None


def test_impossible_inequality_chain():
    """Circular inequality chain cell(0,0) < cell(0,1) < cell(0,0) — unsolvable."""
    puzzle = make_puzzle(2, [[0, 0], [0, 0]], h=[
        (0, 0, "<"),  # cell(0,0) < cell(0,1)
    ], v=[
        (0, 0, "<"),  # cell(0,0) < cell(1,0) — combined with row makes it tight
    ])
    # This specific puzzle IS solvable; test an actually impossible one:
    # 2×2 with cell(0,0) < cell(0,1) AND cell(0,1) < cell(0,0) simultaneously
    # We simulate via two conflicting constraints on same pair:
    impossible = Puzzle(
        N=2,
        grid=np.zeros((2, 2), dtype=int),
        h_constraints=[
            InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction="<"),
            InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction=">"),
        ],
        v_constraints=[],
    )
    solution, stats = BruteForceSolver().solve(impossible)
    assert solution is None


# ===========================================================================
# Group 6 — Stats
# ===========================================================================


def test_stats_time_positive():
    puzzle = Parser().parse(FIXTURE)
    _, stats = BruteForceSolver().solve(puzzle)
    assert stats.time_ms >= 0  # >= 0 allows very fast machines; typically > 0


def test_stats_node_expansions_gte_1():
    puzzle = Parser().parse(FIXTURE)
    _, stats = BruteForceSolver().solve(puzzle)
    assert stats.node_expansions >= 1


def test_stats_memory_nonneg():
    puzzle = Parser().parse(FIXTURE)
    _, stats = BruteForceSolver().solve(puzzle)
    assert stats.memory_kb >= 0


def test_stats_inference_and_backtracks_zero():
    """BruteForce never fires inference rules or backtracks."""
    puzzle = Parser().parse(FIXTURE)
    _, stats = BruteForceSolver().solve(puzzle)
    assert stats.inference_count == 0
    assert stats.backtracks == 0


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    tests = [
        test_solver_name,
        test_solve_returns_tuple,
        test_already_complete_valid,
        test_already_complete_invalid,
        test_single_empty_cell,
        test_2x2_no_constraints,
        test_3x3_no_constraints_with_givens,
        test_3x3_with_h_inequality,
        test_3x3_with_v_inequality,
        test_3x3_fixture,
        test_4x4_with_givens,
        test_4x4_with_constraints,
        test_5x5_with_givens,
        test_5x5_with_constraints,
        test_no_empty_cells,
        test_row_uniqueness,
        test_col_uniqueness,
        test_inequality_constraints_satisfied,
        test_given_cells_preserved,
        test_contradictory_givens,
        test_impossible_inequality_chain,
        test_stats_time_positive,
        test_stats_node_expansions_gte_1,
        test_stats_memory_nonneg,
        test_stats_inference_and_backtracks_zero,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {t.__name__}: {exc}")
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
