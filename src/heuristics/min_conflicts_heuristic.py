"""
Heuristic h₃: Minimum Conflicts Estimate.

For each unassigned cell, compute the minimum number of conflicts it
would cause with *already-assigned* neighbours (same row, same column,
or linked by an inequality constraint) across all values in its domain.
Sum these per-cell minima.

Verdict: ✅ Admissible, good for conflict-dense puzzles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base_heuristic import BaseHeuristic

if TYPE_CHECKING:
    from search.state import SearchState
    from core.puzzle import Puzzle


class MinConflictsHeuristic(BaseHeuristic):
    """
    h₃(n) = Σ min_conflicts(i,j) for all unassigned cells.

    Complexity: O(N² × d) where d = max domain size.
    """

    def estimate(self, state: SearchState, puzzle: Puzzle) -> int:
        """
        For each unassigned cell, try every value in its domain, count
        conflicts with assigned neighbours, and take the minimum.

        Parameters
        ----------
        state : SearchState
            Current search state with domain map.
        puzzle : Puzzle
            Original puzzle (used to look up inequality constraints).

        Returns
        -------
        int
            Σ min_conflicts(i,j) for all unassigned cells.
        """
        N = puzzle.N
        grid = state.grid
        total = 0

        for (i, j), domain in state.domains.items():
            if grid[i, j] != 0:
                continue
            if not domain:
                # Empty domain → this branch is dead; large penalty
                total += N
                continue

            min_conf = N  # upper bound: at most N conflicts
            for v in domain:
                conflicts = self._count_conflicts(
                    grid, N, i, j, v, puzzle,
                )
                if conflicts < min_conf:
                    min_conf = conflicts
                    if min_conf == 0:
                        break  # can't do better than 0

            total += min_conf

        return total

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_conflicts(
        grid, N: int, row: int, col: int, value: int, puzzle,
    ) -> int:
        """
        Count how many *assigned* neighbours would conflict if cell
        ``(row, col)`` were assigned ``value``.

        Counts:
        - Same value already assigned in the same row.
        - Same value already assigned in the same column.
        - Inequality violations with assigned neighbours.
        """
        conflicts = 0

        # Row uniqueness conflicts
        for c in range(N):
            if c != col and grid[row, c] == value:
                conflicts += 1

        # Column uniqueness conflicts
        for r in range(N):
            if r != row and grid[r, col] == value:
                conflicts += 1

        # Inequality constraint conflicts
        for constraint in puzzle.h_constraints + puzzle.v_constraints:
            r1, c1 = constraint.cell1
            r2, c2 = constraint.cell2

            if (r1, c1) == (row, col):
                other_val = int(grid[r2, c2])
                if other_val != 0:
                    if constraint.direction == "<" and not (value < other_val):
                        conflicts += 1
                    elif constraint.direction == ">" and not (value > other_val):
                        conflicts += 1

            elif (r2, c2) == (row, col):
                other_val = int(grid[r1, c1])
                if other_val != 0:
                    if constraint.direction == "<" and not (other_val < value):
                        conflicts += 1
                    elif constraint.direction == ">" and not (other_val > value):
                        conflicts += 1

        return conflicts

    def get_name(self) -> str:
        return "h3: Min Conflicts"
