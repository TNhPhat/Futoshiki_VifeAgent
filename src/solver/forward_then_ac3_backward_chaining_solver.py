"""
Hybrid solver: Forward Chaining propagation, then AC3 + Backward Chaining.
"""

from __future__ import annotations

from core.puzzle import Puzzle
from utils import Stats

from .ac3_backward_chaining_solver import AC3BackwardChaining
from .base_solver import BaseSolver
from .forward_chaining_solver import ForwardChaining


class ForwardThenAC3BackwardChaining(BaseSolver):
    def __init__(self):
        self._forward = ForwardChaining()
        self._ac3_backward = AC3BackwardChaining()

    def solve(self, puzzle: Puzzle, on_step=None) -> tuple[Puzzle | None, Stats]:
        initial_unsolved_mask = puzzle.grid == 0

        fc_solution, fc_stats = self._forward.solve(puzzle.copy(), on_step=on_step)
        ac3_stats = Stats(0, 0, 0, 0, 0)

        final_solution = fc_solution
        if not self._is_valid_complete(fc_solution):
            ac3_input = fc_solution.copy() if fc_solution is not None else puzzle.copy()
            ac3_solution, ac3_stats = self._ac3_backward.solve(ac3_input)
            if ac3_solution is not None:
                final_solution = ac3_solution
                # Replay the BC phase: reveal each newly-filled cell one by one.
                if on_step is not None:
                    base = ac3_input.grid.copy()
                    for r in range(puzzle.N):
                        for c in range(puzzle.N):
                            if ac3_solution.grid[r, c] != 0 and base[r, c] == 0:
                                base[r, c] = ac3_solution.grid[r, c]
                                on_step(base.copy())
            elif fc_solution is None:
                final_solution = None

        return final_solution, Stats(
            time_ms=fc_stats.time_ms + ac3_stats.time_ms,
            memory_kb=max(fc_stats.memory_kb, ac3_stats.memory_kb),
            inference_count=fc_stats.inference_count + ac3_stats.inference_count,
            node_expansions=fc_stats.node_expansions + ac3_stats.node_expansions,
            backtracks=fc_stats.backtracks + ac3_stats.backtracks,
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
        return "Forward Chaining -> Backward Chaining + AC3"
