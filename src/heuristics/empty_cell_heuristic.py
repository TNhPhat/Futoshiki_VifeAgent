"""
Heuristic h₁: Empty Cell Count.

The simplest admissible heuristic — counts unassigned cells.
Admissible because each empty cell requires at least one assignment
step, and the best case for each step is zero new violations.

Verdict: ✅ Admissible, but weak — essentially makes A* behave like BFS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .base_heuristic import BaseHeuristic

if TYPE_CHECKING:
    from search.state import SearchState
    from core.puzzle import Puzzle


class EmptyCellHeuristic(BaseHeuristic):
    """
    h₁(n) = number of unassigned cells.

    Complexity: O(N²).
    """

    def estimate(self, state: SearchState, puzzle: Puzzle) -> int:
        """
        Count cells in the grid that are still 0 (unassigned).

        Parameters
        ----------
        state : SearchState
            Current search state.
        puzzle : Puzzle
            Original puzzle (unused by this heuristic).

        Returns
        -------
        int
            Number of empty cells.
        """
        return int(np.count_nonzero(state.grid == 0))

    def get_name(self) -> str:
        return "h1: Empty Cells"
