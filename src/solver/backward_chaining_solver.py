"""
Pure Prolog-style SLD Resolution Solver for Futoshiki.
"""

from typing import Optional
import time
import tracemalloc

from futoshiki_vifeagent.core import Puzzle
from futoshiki_vifeagent.fol import HornClauseGenerator, Literal
from futoshiki_vifeagent.inference import BackwardChainingEngine
from futoshiki_vifeagent.utils import Stats

from .base_solver import BaseSolver


class BackwardChaining(BaseSolver):
    def __init__(self):
        self._t0: float = 0.0
        self._stats: Stats = Stats(0,0,0,0,0)

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        self._start_trace()

        kb = HornClauseGenerator.generate(puzzle)
        goal = self._generate_goal(puzzle)
        empty_cells = HornClauseGenerator.get_empty_cells(puzzle)
        var_names = [f"v_{r}_{c}" for r, c in empty_cells]

        engine = BackwardChainingEngine(kb=kb)
        substitution = engine.prove_all([goal])

        self._end_trace()
        self._stats.inference_count = engine.inference_count

        if substitution is None:
            return None, self._stats

        solution = puzzle.copy()
        for idx, (r, c) in enumerate(empty_cells):
            var_name = var_names[idx]
            value = self._resolve_value(var_name, substitution)
            if value is not None and isinstance(value, int):
                solution.grid[r, c] = value

        return solution, self._stats

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
