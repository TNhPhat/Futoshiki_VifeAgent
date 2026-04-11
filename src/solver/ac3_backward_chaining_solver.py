from __future__ import annotations



from futoshiki_vifeagent.core import Puzzle
from futoshiki_vifeagent.fol import HornClauseGenerator
from futoshiki_vifeagent.inference import BackwardChainingEngine
from futoshiki_vifeagent.utils import Stats

from .backward_chaining_solver import BackwardChaining


class AC3BackwardChaining(BackwardChaining):
    """
    Backward chaining solver variant with AC-3 domain pruning.
    """

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        self._start_trace()
        initially_unsolved = int((puzzle.grid == 0).sum())

        empty_cells = list(puzzle.get_empty_cells())
        if not empty_cells:
            self._end_trace()
            solved = puzzle.copy()
            self._stats.completion_ratio = self._completion_ratio(
                initially_unsolved=initially_unsolved,
                solution=solved,
            )
            return solved, self._stats

        domains = HornClauseGenerator._ac3_domains(puzzle, empty_cells=empty_cells)
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
        substitution = engine.prove_all([goal])

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
            value = self._resolve_value(var_names[idx], substitution)
            if value is not None and isinstance(value, int):
                solution.grid[r, c] = value
        self._stats.completion_ratio = self._completion_ratio(
            initially_unsolved=initially_unsolved,
            solution=solution,
        )
        return solution, self._stats

    def get_name(self) -> str:
        return "Backward Chaining + AC3 Pruning"
