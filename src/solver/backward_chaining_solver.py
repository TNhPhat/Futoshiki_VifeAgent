"""
Pure Prolog-style SLD Resolution Solver for Futoshiki.
"""

from typing import Optional
import time
import tracemalloc

import numpy as np

from futoshiki_vifeagent.core import Puzzle
from futoshiki_vifeagent.fol import HornClauseGenerator, Literal
from futoshiki_vifeagent.inference import BackwardChainingEngine
from futoshiki_vifeagent.utils import Stats

from .base_solver import BaseSolver


class BackwardChaining(BaseSolver):
    def __init__(self):
        self._t0: float = 0.0
        self._stats: Stats = Stats(0,0,0,0,0)

    def solve(self, puzzle: Puzzle, on_step=None) -> tuple[Puzzle | None, Stats]:
        self._start_trace()
        initially_unsolved = int((puzzle.grid == 0).sum())

        empty_cells = HornClauseGenerator.get_empty_cells(puzzle)
        domains = HornClauseGenerator.hidden_single_domains(
            puzzle,
            empty_cells=empty_cells,
        )
        if domains is None:
            self._end_trace()
            self._stats.completion_ratio = self._completion_ratio(
                initially_unsolved=initially_unsolved,
                solution=None,
            )
            return None, self._stats

        kb = HornClauseGenerator.generate(
            puzzle,
            domains=domains,
            use_cell_domains=True,
        )
        goal = self._generate_goal(puzzle)
        var_names = [f"v_{r}_{c}" for r, c in empty_cells]

        engine = BackwardChainingEngine(kb=kb)
        subst_callback = self._make_subst_callback(
            on_step, puzzle, empty_cells, var_names,
        ) if on_step is not None else None
        substitution = engine.prove_all([goal], on_step=subst_callback)

        self._end_trace()
        self._stats.inference_count = engine.inference_count

        if substitution is None:
            self._stats.completion_ratio = self._completion_ratio(
                initially_unsolved=initially_unsolved,
                solution=None,
            )
            return None, self._stats

        solution = puzzle.copy()
        for idx, (r, c) in enumerate(empty_cells):
            var_name = var_names[idx]
            value = self._resolve_value(var_name, substitution)
            if value is not None and isinstance(value, int):
                solution.grid[r, c] = value

        self._stats.completion_ratio = self._completion_ratio(
            initially_unsolved=initially_unsolved,
            solution=solution,
        )
        return solution, self._stats

    def _make_subst_callback(self, on_step, puzzle, empty_cells, var_names):
        """
        Return a closure that converts a partial substitution dict to a grid
        and calls on_step(grid) whenever the grid actually changes.

        The substitution grows monotonically during proof (SLD never removes
        bindings on a single path). When a branch fails and the engine
        backtracks to try an alternative, the new partial substitution may
        have fewer resolved cell variables → the grid will have fewer filled
        cells, which on_step's caller detects as a backtrack.
        """
        base_grid = puzzle.grid.copy()
        last_grid: list[np.ndarray | None] = [None]

        def _on_subst(subst: dict) -> None:
            grid = base_grid.copy()
            for idx, (r, c) in enumerate(empty_cells):
                val = self._resolve_value(var_names[idx], subst)
                if val is not None and isinstance(val, int):
                    grid[r, c] = val
            prev = last_grid[0]
            if prev is None or not np.array_equal(grid, prev):
                last_grid[0] = grid.copy()
                on_step(grid)

        return _on_subst

    def _generate_goal(self, puzzle: Puzzle) -> Literal:
        return HornClauseGenerator.get_solution_goal(puzzle)

    def _resolve_value(self, var_name: str, substitution: dict) -> Optional[int]:
        value = var_name
        visited = set()

        while isinstance(value, str) and value not in visited:
            visited.add(value)
            if value in substitution:
                value = substitution[value]
            else:
                found = False
                for key, val in substitution.items():
                    if key == value or (isinstance(key, str) and key.startswith(value + "_")):
                        value = val
                        found = True
                        break
                if not found:
                    break

        return value if isinstance(value, int) else None

    def _start_trace(self):
        self._stats = Stats(0, 0, 0, 0, 0)
        tracemalloc.start()
        self._t0 = time.perf_counter()

    def _end_trace(self):
        self._stats.time_ms = (time.perf_counter() - self._t0) * 1000
        _, self._stats.memory_kb = tracemalloc.get_traced_memory()
        self._stats.memory_kb /= 1024
        tracemalloc.stop()

    def get_name(self) -> str:
        return "Backward Chaining (Generate-and-Test SLD)"

    @staticmethod
    def _completion_ratio(initially_unsolved: int, solution: Puzzle | None) -> float:
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
