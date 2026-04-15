"""
Search state representation for A* search on Futoshiki puzzles.

A SearchState holds a partial assignment (grid), per-cell domains,
and cost components g (violations) and h (heuristic estimate).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class SearchState:
    """
    Represents a node in the A* search tree.

    Attributes
    ----------
    grid : np.ndarray
        Shape (N, N), dtype int.  0 = unassigned cell.
    domains : dict[tuple[int, int], set[int]]
        For each *unassigned* cell ``(i, j)`` the set of values still
        considered possible.  Assigned cells are absent from this dict.
    g : int
        Actual cost -- number of constraint violations in the current
        partial assignment.
    h : int
        Heuristic estimate of remaining cost to reach a goal state.
    parent : SearchState or None
        Back-pointer for solution reconstruction (unused by the engine
        itself but kept for debugging / tracing).
    """

    grid: np.ndarray
    domains: dict[tuple[int, int], set[int]]
    g: int = 0
    h: int = 0
    parent: Optional[SearchState] = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def f(self) -> int:
        """Total estimated cost: f(n) = g(n) + h(n)."""
        return self.g + self.h

    @property
    def is_complete(self) -> bool:
        """True when every cell in the grid has been assigned a value."""
        return bool(np.all(self.grid != 0))

    @property
    def unassigned_cells(self) -> list[tuple[int, int]]:
        """Return a list of ``(row, col)`` pairs for cells with value 0."""
        rows, cols = np.nonzero(self.grid == 0)
        return [(int(r), int(c)) for r, c in zip(rows, cols)]

    # ------------------------------------------------------------------
    # Priority-queue ordering
    # ------------------------------------------------------------------

    def __lt__(self, other: SearchState) -> bool:
        """
        Priority: lower ``f`` wins.  Break ties by lower ``g``
        (prefer states with fewer violations).
        """
        if self.f == other.f:
            return self.g < other.g
        return self.f < other.f

    # ------------------------------------------------------------------
    # Hashing (for closed-set membership)
    # ------------------------------------------------------------------

    def __hash__(self) -> int:
        return hash(self.grid.tobytes())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SearchState):
            return NotImplemented
        return np.array_equal(self.grid, other.grid)

    # ------------------------------------------------------------------
    # Copy
    # ------------------------------------------------------------------

    def copy(self) -> SearchState:
        """
        Return a deep copy suitable for creating a child state.

        The grid and every domain set are independently copied so that
        mutations on the child do not affect this state.
        """
        return SearchState(
            grid=self.grid.copy(),
            domains={k: set(v) for k, v in self.domains.items()},
            g=self.g,
            h=self.h,
            parent=self,
        )
