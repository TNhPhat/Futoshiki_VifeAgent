"""
Hybrid solver: Forward Chaining propagation, then Backward Chaining.
"""

from __future__ import annotations

from core.puzzle import Puzzle
from solver.backward_chaining_solver import BackwardChaining
from utils import Stats

from .base_solver import BaseSolver
from .forward_chaining_solver import ForwardChaining


class ForwardThenBackwardChaining(BaseSolver):
    def __init__(self):
        self._forward = ForwardChaining()
        self._backward = BackwardChaining()

    def solve(self, puzzle: Puzzle, on_step=None) -> tuple[Puzzle | None, Stats]:
        initial_unsolved_mask = puzzle.grid == 0

        fc_solution, fc_stats = self._forward.solve(puzzle.copy(), on_step=on_step)
        backward_stats = Stats(0, 0, 0, 0, 0)

        final_solution = fc_solution
        if not self._is_valid_complete(fc_solution):
            backward_input = (
                fc_solution.copy() if fc_solution is not None else puzzle.copy()
            )
            backward_solution, backward_stats = self._backward.solve(backward_input)
            if backward_solution is not None:
                final_solution = backward_solution
                # Replay the BC phase: reveal each newly-filled cell one by one.
                if on_step is not None:
                    base = backward_input.grid.copy()
                    for r in range(puzzle.N):
                        for c in range(puzzle.N):
                            if backward_solution.grid[r, c] != 0 and base[r, c] == 0:
                                base[r, c] = backward_solution.grid[r, c]
                                on_step(base.copy())
            elif fc_solution is None:
                final_solution = None

        return final_solution, Stats(
            time_ms=fc_stats.time_ms + backward_stats.time_ms,
            memory_kb=max(fc_stats.memory_kb, backward_stats.memory_kb),
            inference_count=fc_stats.inference_count + backward_stats.inference_count,
            node_expansions=fc_stats.node_expansions + backward_stats.node_expansions,
            backtracks=fc_stats.backtracks + backward_stats.backtracks,
            completion_ratio=self._completion_ratio(initial_unsolved_mask, final_solution),
        )

    @staticmethod
    def _is_valid_complete(solution: Puzzle | None) -> bool:
        return (
            solution is not None
            and solution.is_complete()
            and ForwardChaining._is_valid_complete_solution(solution)
        )

    @staticmethod
    def _completion_ratio(initial_unsolved_mask, solution: Puzzle | None) -> float:
        initially_unsolved = int(initial_unsolved_mask.sum())
        if initially_unsolved == 0:
            return 1.0
        if solution is None:
            return 0.0
        solved_after = int((solution.grid[initial_unsolved_mask] != 0).sum())
        return solved_after / initially_unsolved

    def get_name(self) -> str:
        return "Forward Chaining -> Backward Chaining"
