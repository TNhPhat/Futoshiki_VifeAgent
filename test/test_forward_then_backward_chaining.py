from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from benchmark import benchmark as benchmark_runner
from core.puzzle import Puzzle
from solver.forward_chaining_solver import ForwardChaining
from solver.forward_then_backward_chaining_solver import (
    ForwardThenBackwardChaining,
)


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
    solver = ForwardThenBackwardChaining()
    assert solver.get_name() == "Forward Chaining -> Backward Chaining"


def test_solver_fc_then_backward_chaining_solves_sparse_4x4():
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

    fc_solution, _ = ForwardChaining().solve(puzzle.copy())
    hybrid_solution, stats = ForwardThenBackwardChaining().solve(puzzle.copy())

    assert fc_solution is not None
    assert not fc_solution.is_complete()

    assert hybrid_solution is not None
    assert hybrid_solution.is_complete()
    assert _is_valid_complete_solution(hybrid_solution)
    assert int(hybrid_solution.grid[0, 0]) == 1
    assert stats.inference_count > 0
    assert stats.completion_ratio == 1.0


def test_benchmark_registry_exposes_hybrid_solver_key():
    registry = benchmark_runner._solver_registry()
    assert "forward_then_backward_chaining" in registry
    solver = registry["forward_then_backward_chaining"]()
    assert isinstance(solver, ForwardThenBackwardChaining)
    assert solver.get_name() == "Forward Chaining -> Backward Chaining"
