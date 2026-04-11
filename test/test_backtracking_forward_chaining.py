from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from benchmark import benchmark as benchmark_runner
from core.puzzle import Puzzle
from solver.backtracking_forward_chaining_solver import BacktrackingForwardChaining


def _is_valid_complete_solution(solution: Puzzle) -> bool:
    expected = list(range(1, solution.N + 1))
    for row in range(solution.N):
        if sorted(int(v) for v in solution.grid[row, :]) != expected:
            return False
    for col in range(solution.N):
        if sorted(int(v) for v in solution.grid[:, col]) != expected:
            return False
    for constraint in (*solution.h_constraints, *solution.v_constraints):
        if not constraint.is_satisfied(solution):
            return False
    return True


def test_solver_name():
    assert BacktrackingForwardChaining().get_name() == "Backtracking + Forward Chaining"


def test_solver_solves_sparse_4x4():
    puzzle = Puzzle(
        N=4,
        grid=np.array(
            [
                [1, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ],
            dtype=int,
        ),
        h_constraints=[],
        v_constraints=[],
    )

    solution, stats = BacktrackingForwardChaining().solve(puzzle)

    assert solution is not None
    assert solution.is_complete()
    assert _is_valid_complete_solution(solution)
    assert int(solution.grid[0, 0]) == 1
    assert stats.node_expansions > 0
    assert stats.backtracks >= 0
    assert stats.inference_count > 0
    assert stats.completion_ratio == 1.0


def test_benchmark_registry_exposes_solver_key():
    registry = benchmark_runner._solver_registry()
    assert "backtracking_forward_chaining" in registry
    solver = registry["backtracking_forward_chaining"]()
    assert isinstance(solver, BacktrackingForwardChaining)
