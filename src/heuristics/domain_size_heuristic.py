"""
Heuristic h2: Domain Sum Minus One.

For each unassigned cell, contributes ``(|domain| - 1)`` to the total.
A cell with a singleton domain (already determined) contributes 0;
a cell with all N values still possible contributes N-1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base_heuristic import BaseHeuristic

if TYPE_CHECKING:
    from search.state import SearchState
    from core.puzzle import Puzzle


class DomainSizeHeuristic(BaseHeuristic):
    """
    h2(n) = Sigma (|domain(i,j)| - 1) for all unassigned cells.

    Complexity: O(N2).
    """

    def estimate(self, state: SearchState, puzzle: Puzzle) -> int:
        """
        Sum the excess domain sizes across all unassigned cells.

        Parameters
        ----------
        state : SearchState
            Current search state with domain map.
        puzzle : Puzzle
            Original puzzle (unused by this heuristic).

        Returns
        -------
        int
            Sigma (|domain(i,j)| - 1) for all unassigned cells.
        """
        total = 0
        for (i, j), domain in state.domains.items():
            if state.grid[i, j] == 0:
                total += max(0, len(domain) - 1)
        return total

    def get_name(self) -> str:
        return "h2: Domain Sum"
