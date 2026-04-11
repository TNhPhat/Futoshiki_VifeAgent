"""
Data-Driven Forward Chaining Solver for Futoshiki.
"""

from collections import defaultdict
import time
import tracemalloc

from core.puzzle import Puzzle
from fol import HornClauseGenerator2, Literal, Val
from inference import ForwardChainingEngine
from utils import Stats

from .base_solver import BaseSolver


class ForwardChaining(BaseSolver):
    def __init__(self):
        self._t0: float = 0.0
        self._stats: Stats = Stats(0, 0, 0, 0, 0)

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        self._start_trace()

        all_facts, total_inference = self._derive_facts(puzzle)

        solution = self._build_solution(puzzle, all_facts)
        self._end_trace()
        self._stats.inference_count = total_inference
        self._stats.completion_ratio = self._completion_ratio(puzzle, solution)
        return solution, self._stats

    @staticmethod
    def _derive_facts(puzzle: Puzzle) -> tuple[set[Literal], int]:
        kb = HornClauseGenerator2.generate(puzzle)
        clauses = kb.get_clauses()
        initial_facts = [clause.head for clause in clauses if clause.is_fact()]
        rules = [clause for clause in clauses if not clause.is_fact()]

        all_facts: set[Literal] = set(initial_facts)
        total_inference = 0

        # FC fixed-point with deterministic promotion:
        # - derive all rule consequences
        # - promote singleton/hidden-single candidates into Val facts
        # - repeat until no new information
        max_rounds = max(1, puzzle.N * puzzle.N * 2)
        for _ in range(max_rounds):
            engine = ForwardChainingEngine(
                rules=rules,
                initial_facts=list(all_facts),
                max_iterations=5000,
            )
            all_facts = set(engine.run())
            total_inference += engine.inference_count

            promoted_vals = ForwardChaining._promote_vals(puzzle, all_facts)
            new_vals = promoted_vals - all_facts
            if not new_vals:
                break
            all_facts.update(new_vals)

        return all_facts, total_inference

    @staticmethod
    def _candidate_map(
        puzzle: Puzzle,
        facts: set[Literal],
    ) -> dict[tuple[int, int], set[int]]:
        n = puzzle.N
        all_values = set(range(1, n + 1))
        val_by_cell: dict[tuple[int, int], set[int]] = defaultdict(set)
        not_val_by_cell: dict[tuple[int, int], set[int]] = defaultdict(set)

        for fact in facts:
            if len(fact.args) != 3:
                continue
            row, col, value = fact.args
            if not (
                isinstance(row, int)
                and isinstance(col, int)
                and isinstance(value, int)
                and 0 <= row < n
                and 0 <= col < n
                and 1 <= value <= n
            ):
                continue

            if fact.name == "Val":
                val_by_cell[(row, col)].add(value)
            elif fact.name == "NotVal":
                not_val_by_cell[(row, col)].add(value)

        candidates: dict[tuple[int, int], set[int]] = {}
        for row in range(n):
            for col in range(n):
                explicit = val_by_cell.get((row, col), set())
                if explicit:
                    candidates[(row, col)] = set(explicit)
                else:
                    candidates[(row, col)] = all_values - not_val_by_cell.get(
                        (row, col), set()
                    )
        return candidates

    @staticmethod
    def _promote_vals(
        puzzle: Puzzle,
        facts: set[Literal],
    ) -> set[Literal]:
        n = puzzle.N
        promoted: set[Literal] = set()
        candidates = ForwardChaining._candidate_map(puzzle, facts)

        # Cell singleton
        for row in range(n):
            for col in range(n):
                cell_candidates = candidates[(row, col)]
                if len(cell_candidates) == 1:
                    promoted.add(Val(row, col, next(iter(cell_candidates))))

        # Row hidden singleton
        for row in range(n):
            for value in range(1, n + 1):
                cols = [
                    col for col in range(n) if value in candidates[(row, col)]
                ]
                if len(cols) == 1:
                    promoted.add(Val(row, cols[0], value))

        # Column hidden singleton
        for col in range(n):
            for value in range(1, n + 1):
                rows = [
                    row for row in range(n) if value in candidates[(row, col)]
                ]
                if len(rows) == 1:
                    promoted.add(Val(rows[0], col, value))

        return promoted

    @staticmethod
    def _build_solution(
        puzzle: Puzzle,
        facts: set[Literal],
    ) -> Puzzle:
        candidates = ForwardChaining._candidate_map(puzzle, facts)
        solution = puzzle.copy()

        for row in range(solution.N):
            for col in range(solution.N):
                cell_candidates = candidates[(row, col)]
                given_value = int(solution.grid[row, col])

                if given_value != 0:
                    continue

                if len(cell_candidates) == 1:
                    solution.grid[row, col] = next(iter(cell_candidates))
                else:
                    # Keep unresolved cells as 0 by design.
                    solution.grid[row, col] = 0

        return solution

    @staticmethod
    def _is_valid_complete_solution(solution: Puzzle) -> bool:
        n = solution.N
        expected = list(range(1, n + 1))

        for row in range(n):
            if sorted(int(v) for v in solution.grid[row, :]) != expected:
                return False

        for col in range(n):
            if sorted(int(v) for v in solution.grid[:, col]) != expected:
                return False

        for constraint in (*solution.h_constraints, *solution.v_constraints):
            if not constraint.is_satisfied(solution):
                return False

        return True

    @staticmethod
    def _completion_ratio(initial_puzzle: Puzzle, solution: Puzzle | None) -> float:
        initial_unsolved_mask = initial_puzzle.grid == 0
        initially_unsolved = int(initial_unsolved_mask.sum())
        if initially_unsolved == 0:
            return 1.0
        if solution is None:
            return 0.0
        solved_after = int((solution.grid[initial_unsolved_mask] != 0).sum())
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
        return "Forward Chaining (Data-Driven Fix-point)"
