from __future__ import annotations

import time
import tracemalloc
from itertools import product

from futoshiki_vifeagent.core import Puzzle
from futoshiki_vifeagent.utils import Stats
from .base_solver import BaseSolver


class BruteForceSolver(BaseSolver):
    """
    Exhaustive brute-force Futoshiki solver.

    Enumerates every possible assignment of values 1..N to the empty cells
    (in row-major order) and returns the first assignment that satisfies all
    constraints (row/column uniqueness and all inequality constraints).

    Complexity: O(N^K) where K = number of empty cells.
    Practical only for small grids (N ≤ 4).
    """

    def get_name(self) -> str:
        """Return the solver's display name."""
        return "BruteForce"

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        """
        Solve *puzzle* by exhaustive enumeration.

        Parameters
        ----------
        puzzle : Puzzle
            The puzzle to solve; given cells are treated as fixed.

        Returns
        -------
        tuple[Puzzle | None, Stats]
            ``(solved_puzzle, stats)`` on success, or ``(None, stats)`` if no
            valid assignment exists.
        """
        tracemalloc.start()
        t0 = time.perf_counter()
        expansions = 0

        empty_cells = puzzle.get_empty_cells()
        domain = range(1, puzzle.N + 1)

        result: Puzzle | None = None
        for assignment in product(domain, repeat=len(empty_cells)):
            expansions += 1
            candidate = puzzle.copy()
            for (i, j), v in zip(empty_cells, assignment):
                candidate.grid[i, j] = v
            if self._is_valid(candidate):
                result = candidate
                break

        elapsed_ms = (time.perf_counter() - t0) * 1000
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        stats = Stats(
            time_ms=elapsed_ms,
            memory_kb=peak_bytes / 1024,
            inference_count=0,
            node_expansions=expansions,
            backtracks=0,
        )
        return result, stats

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_valid(self, puzzle: Puzzle) -> bool:
        """
        Check whether a fully assigned puzzle satisfies all Futoshiki rules.

        Parameters
        ----------
        puzzle : Puzzle
            A puzzle whose grid has no empty (0) cells.

        Returns
        -------
        bool
            True iff every row and column is a permutation of 1..N and every
            inequality constraint is satisfied.
        """
        N = puzzle.N
        g = puzzle.grid
        expected = list(range(1, N + 1))

        for i in range(N):
            if sorted(g[i]) != expected:
                return False

        for j in range(N):
            if sorted(g[:, j]) != expected:
                return False

        for c in puzzle.h_constraints + puzzle.v_constraints:
            if not c.is_satisfied(puzzle):
                return False

        return True
