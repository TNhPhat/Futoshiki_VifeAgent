"""
A* Search Solver for Futoshiki.

Wraps the AStarEngine and a pluggable BaseHeuristic into the
standard BaseSolver interface so it can be used alongside the
existing Forward Chaining, Backward Chaining and Brute Force solvers.
"""

from __future__ import annotations

import time
import tracemalloc

from futoshiki_vifeagent.core import Puzzle
from futoshiki_vifeagent.utils import Stats
from heuristics import (
    BaseHeuristic,
    DomainSizeHeuristic,
)
from search.astar import AStarEngine

from .base_solver import BaseSolver


class AStarSolver(BaseSolver):
    """
    A* search solver with a pluggable heuristic.

    Parameters
    ----------
    heuristic : BaseHeuristic, optional
        The heuristic to use for h(n) estimation.
        Defaults to ``DomainSizeHeuristic`` (h₂).
    """

    def __init__(
        self, heuristic: BaseHeuristic | None = None,
    ) -> None:
        super().__init__()
        self._heuristic = heuristic or DomainSizeHeuristic()

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        """
        Solve the puzzle using A* search.

        Parameters
        ----------
        puzzle : Puzzle
            The Futoshiki puzzle to solve.

        Returns
        -------
        tuple[Puzzle | None, Stats]
            ``(solved_puzzle, stats)`` on success, or
            ``(None, stats)`` if no solution exists.
        """
        tracemalloc.start()
        t0 = time.perf_counter()
        initially_unsolved = int((puzzle.grid == 0).sum())

        engine = AStarEngine(heuristic=self._heuristic)
        goal_state = engine.solve(puzzle)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        if goal_state is None:
            return None, Stats(
                time_ms=elapsed_ms,
                memory_kb=peak_bytes / 1024,
                inference_count=0,
                node_expansions=engine.node_expansions,
                backtracks=0,
                completion_ratio=0.0,
            )

        solution = Puzzle(
            N=puzzle.N,
            grid=goal_state.grid,
            h_constraints=list(puzzle.h_constraints),
            v_constraints=list(puzzle.v_constraints),
        )

        completion = (
            self._completion_ratio(initially_unsolved, solution)
        )

        return solution, Stats(
            time_ms=elapsed_ms,
            memory_kb=peak_bytes / 1024,
            inference_count=0,
            node_expansions=engine.node_expansions,
            backtracks=0,
            completion_ratio=completion,
        )

    def get_name(self) -> str:
        return f"A* Search ({self._heuristic.get_name()})"

    @staticmethod
    def _completion_ratio(
        initially_unsolved: int, solution: Puzzle | None,
    ) -> float:
        if initially_unsolved == 0:
            return 1.0
        if solution is None:
            return 0.0
        solved_after = int((solution.grid != 0).sum()) - (
            solution.N * solution.N - initially_unsolved
        )
        if solved_after < 0:
            return 0.0
        return solved_after / initially_unsolved
