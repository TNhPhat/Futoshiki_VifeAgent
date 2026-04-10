"""
Data-Driven Forward Chaining Solver for Futoshiki.
"""

from typing import Optional
import time
import tracemalloc

from core.puzzle import Puzzle
from fol import HornClauseGenerator, Literal, Unifier
from inference import ForwardChainingEngine
from utils import Stats

from .base_solver import BaseSolver


class ForwardChaining(BaseSolver):
    def __init__(self):
        self._t0: float = 0.0
        self._stats: Stats = Stats(0, 0, 0, 0, 0)
        self._unifier = Unifier()

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        self._start_trace()

        kb = HornClauseGenerator.generate(puzzle)
        goal = HornClauseGenerator.get_solution_goal(puzzle)
        empty_cells = HornClauseGenerator.get_empty_cells(puzzle)
        var_names = [f"v_{r}_{c}" for r, c in empty_cells]

        all_clauses = kb._clause if hasattr(kb, "clauses") else kb._clause
        facts = [c.head for c in all_clauses if not c.body]
        rules = [c for c in all_clauses if c.body]

        engine = ForwardChainingEngine(rules=rules, initial_facts=facts, max_iterations=5000)
        derived_facts = engine.run()

        self._end_trace()
        self._stats.inference_count = engine.inference_count

        if not derived_facts:
            return None, self._stats

        solution_subst = None
        for fact in derived_facts:
            # Neu fact nay la ket qua khop voi goal thi lay subst de giai ma gia tri
            subst = self._unifier.unify(goal, fact, {})
            if subst is not None:
                solution_subst = subst
                break

        if solution_subst is None:
            return None, self._stats

        solution = puzzle.copy()
        for idx, (r, c) in enumerate(empty_cells):
            var_name = var_names[idx]
            value = self._resolve_value(var_name, solution_subst)
            if value is not None and isinstance(value, int):
                solution.grid[r, c] = value

        return solution, self._stats

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
        return "Forward Chaining (Data-Driven Fix-point)"