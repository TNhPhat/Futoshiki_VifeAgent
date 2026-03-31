from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Puzzle:
    """
    Immutable problem definition for a Futoshiki puzzle.

    Stores the initial grid clues and all inequality constraints.
    This is the problem description, not the mutable solver state —
    solvers receive a ``Puzzle`` and return a separate solution grid.

    Parameters
    ----------
    N : int
        Grid size; the grid contains integer values 1..N.
    grid : np.ndarray
        Shape (N, N), dtype int.
        0 = empty cell; 1..N = pre-filled clue value.
    h_constraints : np.ndarray
        Shape (N, N-1), dtype int.
        Horizontal constraint immediately to the right of cell (i, j):
        0 = none, 1 = '<' (left < right), -1 = '>' (left > right).
    v_constraints : np.ndarray
        Shape (N-1, N), dtype int.
        Vertical constraint immediately below cell (i, j):
        0 = none, 1 = '<' (top < bottom), -1 = '>' (top > bottom).
    """

    N: int
    grid: np.ndarray        # shape: (N, N)
    h_constraints: np.ndarray  # shape: (N, N-1)
    v_constraints: np.ndarray  # shape: (N-1, N)

    # Cached cell lists — computed once in __post_init__, not constructor args
    _given_cells: list[tuple[int, int, int]] = field(
        default_factory=list, init=False, repr=False
    )
    _empty_cells: list[tuple[int, int]] = field(
        default_factory=list, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Pre-compute and cache given and empty cell lists from the grid."""
        given_rows, given_cols = np.nonzero(self.grid)       # nonzero → given
        self._given_cells = [
            (int(r), int(c), int(self.grid[r, c]))
            for r, c in zip(given_rows, given_cols)
        ]

        empty_rows, empty_cols = np.nonzero(self.grid == 0)  # zero → empty
        self._empty_cells = [
            (int(r), int(c))
            for r, c in zip(empty_rows, empty_cols)
        ]

    # ------------------------------------------------------------------
    # Cell queries
    # ------------------------------------------------------------------

    def is_complete(self) -> bool:
        """
        Check whether every cell has been assigned a value.

        Returns
        -------
        bool
            True if no cell in the grid is 0 (empty).
        """
        return bool(np.all(self.grid != 0))

    def is_given(self, i: int, j: int) -> bool:
        """
        Check whether cell (i, j) carries a pre-filled clue.

        Parameters
        ----------
        i : int
            Row index (0-based).
        j : int
            Column index (0-based).

        Returns
        -------
        bool
            True if the cell was provided as a clue in the original puzzle.
        """
        return int(self.grid[i, j]) != 0

    def get_given_cells(self) -> list[tuple[int, int, int]]:
        """
        Return all pre-filled clue cells as (row, col, value) triples.

        The list is computed once at construction time and cached.

        Returns
        -------
        list of tuple[int, int, int]
            Each element is ``(i, j, v)`` where ``grid[i, j] == v > 0``.
        """
        return self._given_cells

    def get_empty_cells(self) -> list[tuple[int, int]]:
        """
        Return all empty cells as (row, col) pairs.

        The list is computed once at construction time and cached.

        Returns
        -------
        list of tuple[int, int]
            Each element is ``(i, j)`` where ``grid[i, j] == 0``.
        """
        return self._empty_cells

    # ------------------------------------------------------------------
    # Constraint queries
    # ------------------------------------------------------------------

    def get_h_constraint(self, i: int, j: int) -> int:
        """
        Return the horizontal constraint between cell (i, j) and (i, j+1).

        Parameters
        ----------
        i : int
            Row index (0-based).
        j : int
            Column index of the *left* cell (0-based); must be < N-1.

        Returns
        -------
        int
            0 = no constraint, 1 = '<' (left < right), -1 = '>' (left > right).
        """
        return int(self.h_constraints[i, j])

    def get_v_constraint(self, i: int, j: int) -> int:
        """
        Return the vertical constraint between cell (i, j) and (i+1, j).

        Parameters
        ----------
        i : int
            Row index of the *top* cell (0-based); must be < N-1.
        j : int
            Column index (0-based).

        Returns
        -------
        int
            0 = no constraint, 1 = '<' (top < bottom), -1 = '>' (top > bottom).
        """
        return int(self.v_constraints[i, j])

    # ------------------------------------------------------------------
    # Copy
    # ------------------------------------------------------------------

    def copy(self) -> Puzzle:
        """
        Return a deep copy of this puzzle with independent numpy arrays.

        Mutating the copy's ``grid`` does not affect the original, which
        is important for solvers that fill in values incrementally.

        Returns
        -------
        Puzzle
            A new ``Puzzle`` instance with copied arrays.
        """
        return Puzzle(
            N=self.N,
            grid=self.grid.copy(),
            h_constraints=self.h_constraints.copy(),
            v_constraints=self.v_constraints.copy(),
        )

    # ------------------------------------------------------------------
    # Debug representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Return a human-readable string showing the grid and constraints.

        Returns
        -------
        str
            Multi-line string with grid rows, inline horizontal constraint
            symbols, and vertical constraint lines between rows.
        """
        lines: list[str] = []
        for i in range(self.N):
            row_parts: list[str] = []
            for j in range(self.N):
                cell = self.grid[i, j]
                row_parts.append(str(cell) if cell != 0 else ".")
                if j < self.N - 1:
                    h = self.h_constraints[i, j]
                    row_parts.append("<" if h == 1 else (">" if h == -1 else " "))
            lines.append(" ".join(row_parts))

            if i < self.N - 1:
                vert_parts: list[str] = []
                for j in range(self.N):
                    v = self.v_constraints[i, j]
                    vert_parts.append("^" if v == 1 else ("v" if v == -1 else " "))
                    if j < self.N - 1:
                        vert_parts.append(" ")
                lines.append(" ".join(vert_parts))

        return "\n".join(lines)
