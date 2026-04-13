"""
Backtracking + Forward Chaining Solver for Futoshiki.
"""

from __future__ import annotations

from collections import defaultdict
import time
import tracemalloc

from core.puzzle import Puzzle
from fol import Literal
from utils import Stats

from .base_solver import BaseSolver
from .forward_chaining_solver import ForwardChaining


class BacktrackingForwardChaining(BaseSolver):
    def __init__(self):
        self._t0: float = 0.0
        self._stats: Stats = Stats(0, 0, 0, 0, 0)

    def solve(self, puzzle: Puzzle, on_step=None) -> tuple[Puzzle | None, Stats]:
        self._start_trace()
        initially_unsolved = int((puzzle.grid == 0).sum())

        solution = self._search(puzzle.copy(), on_step=on_step)

        self._end_trace()
        self._stats.completion_ratio = self._completion_ratio(
            initially_unsolved=initially_unsolved,
            solution=solution,
        )
        return solution, self._stats

    def _search(self, puzzle: Puzzle, on_step=None) -> Puzzle | None:
        facts, inference_count = ForwardChaining._derive_facts(puzzle)
        self._stats.inference_count += inference_count

        candidates = ForwardChaining._candidate_map(puzzle, facts)
        if self._has_fact_contradiction(puzzle, facts, candidates):
            return None

        propagated = ForwardChaining._build_solution(puzzle, facts)
        if not self._is_partial_solution_consistent(propagated):
            return None

        # Emit the state after forward-chaining propagation at this level.
        if on_step is not None:
            on_step(propagated.grid.copy())

        if propagated.is_complete():
            if ForwardChaining._is_valid_complete_solution(propagated):
                return propagated
            return None

        choice = self._choose_cell(propagated, candidates)
        if choice is None:
            return None
        row, col, domain = choice

        for value in domain:
            self._stats.node_expansions += 1
            child = propagated.copy()
            child.grid[row, col] = value

            result = self._search(child, on_step=on_step)
            if result is not None:
                return result

            # Backtrack: emit the pre-branch state so cleared cells flash orange.
            if on_step is not None:
                on_step(propagated.grid.copy(), True)
            self._stats.backtracks += 1

        return None

    @staticmethod
    def _choose_cell(
        puzzle: Puzzle,
        candidates: dict[tuple[int, int], set[int]],
    ) -> tuple[int, int, list[int]] | None:
        best_cell: tuple[int, int] | None = None
        best_domain: set[int] | None = None

        for row in range(puzzle.N):
            for col in range(puzzle.N):
                if int(puzzle.grid[row, col]) != 0:
                    continue

                domain = candidates[(row, col)]
                if len(domain) <= 1:
                    continue

                if best_domain is None or len(domain) < len(best_domain):
                    best_cell = (row, col)
                    best_domain = domain
                    if len(best_domain) == 2:
                        break
            if best_domain is not None and len(best_domain) == 2:
                break

        if best_cell is None or best_domain is None:
            return None

        row, col = best_cell
        return row, col, sorted(best_domain)

    @staticmethod
    def _has_fact_contradiction(
        puzzle: Puzzle,
        facts: set[Literal],
        candidates: dict[tuple[int, int], set[int]],
    ) -> bool:
        val_by_cell: dict[tuple[int, int], set[int]] = defaultdict(set)
        not_val_by_cell: dict[tuple[int, int], set[int]] = defaultdict(set)

        for fact in facts:
            if fact.name not in ("Val", "NotVal") or len(fact.args) != 3:
                continue

            row, col, value = fact.args
            if not (
                isinstance(row, int)
                and isinstance(col, int)
                and isinstance(value, int)
                and 0 <= row < puzzle.N
                and 0 <= col < puzzle.N
                and 1 <= value <= puzzle.N
            ):
                continue

            if fact.name == "Val":
                val_by_cell[(row, col)].add(value)
            else:
                not_val_by_cell[(row, col)].add(value)

        for row in range(puzzle.N):
            for col in range(puzzle.N):
                key = (row, col)
                vals = val_by_cell.get(key, set())
                not_vals = not_val_by_cell.get(key, set())

                if len(vals) > 1:
                    return True
                if vals and vals.intersection(not_vals):
                    return True
                if not candidates[key]:
                    return True

                fixed_value = int(puzzle.grid[row, col])
                if fixed_value != 0 and fixed_value not in candidates[key]:
                    return True

        return False

    @staticmethod
    def _is_partial_solution_consistent(puzzle: Puzzle) -> bool:
        for row in range(puzzle.N):
            values = [int(v) for v in puzzle.grid[row, :] if int(v) != 0]
            if len(values) != len(set(values)):
                return False

        for col in range(puzzle.N):
            values = [int(v) for v in puzzle.grid[:, col] if int(v) != 0]
            if len(values) != len(set(values)):
                return False

        for constraint in (*puzzle.h_constraints, *puzzle.v_constraints):
            if not constraint.is_satisfied(puzzle):
                return False

        return True

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
        return "Backtracking + Forward Chaining"
