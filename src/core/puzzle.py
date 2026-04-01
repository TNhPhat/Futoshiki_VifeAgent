from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from constraints.inequality_constraint import InequalityConstraint


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
    h_constraints : list of InequalityConstraint
        All horizontal inequality constraints.  Each entry records
        cell1=(i, j), cell2=(i, j+1), and direction ``'<'`` or ``'>'``.
    v_constraints : list of InequalityConstraint
        All vertical inequality constraints.  Each entry records
        cell1=(i, j), cell2=(i+1, j), and direction ``'<'`` or ``'>'``.
    """

    N: int
    grid: np.ndarray                        # shape: (N, N)
    h_constraints: list[InequalityConstraint]
    v_constraints: list[InequalityConstraint]

    # Private lookup maps — keyed by the left/top cell (i, j)
    _h_map: dict[tuple[int, int], InequalityConstraint] = field(
        default_factory=dict, init=False, repr=False
    )
    _v_map: dict[tuple[int, int], InequalityConstraint] = field(
        default_factory=dict, init=False, repr=False
    )

    # Cached cell lists — computed once in __post_init__, not constructor args
    _given_cells: list[tuple[int, int, int]] = field(
        default_factory=list, init=False, repr=False
    )
    _empty_cells: list[tuple[int, int]] = field(
        default_factory=list, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Pre-compute lookup maps and cached cell lists."""
        # Build O(1) constraint lookup maps
        self._h_map = {c.cell1: c for c in self.h_constraints}
        self._v_map = {c.cell1: c for c in self.v_constraints}

        # Cache given and empty cells
        given_rows, given_cols = np.nonzero(self.grid)
        self._given_cells = [
            (int(r), int(c), int(self.grid[r, c]))
            for r, c in zip(given_rows, given_cols)
        ]

        empty_rows, empty_cols = np.nonzero(self.grid == 0)
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

    def get_h_constraint(
        self, i: int, j: int
    ) -> InequalityConstraint | None:
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
        InequalityConstraint or None
            The constraint object (``direction`` is ``'<'`` or ``'>'``),
            or ``None`` if no constraint exists at this position.
        """
        return self._h_map.get((i, j))

    def get_v_constraint(
        self, i: int, j: int
    ) -> InequalityConstraint | None:
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
        InequalityConstraint or None
            The constraint object (``direction`` is ``'<'`` or ``'>'``),
            or ``None`` if no constraint exists at this position.
        """
        return self._v_map.get((i, j))

    # ------------------------------------------------------------------
    # Copy
    # ------------------------------------------------------------------

    def copy(self) -> Puzzle:
        """
        Return a deep copy of this puzzle with an independent grid array.

        Constraint objects are shared (they are immutable problem data).
        Mutating the copy's ``grid`` does not affect the original.

        Returns
        -------
        Puzzle
            A new ``Puzzle`` instance with a copied grid.
        """
        return Puzzle(
            N=self.N,
            grid=self.grid.copy(),
            h_constraints=list(self.h_constraints),
            v_constraints=list(self.v_constraints),
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
                    h = self.get_h_constraint(i, j)
                    row_parts.append(
                        h.direction if h is not None else " "
                    )
            lines.append(" ".join(row_parts))

            if i < self.N - 1:
                vert_parts: list[str] = []
                for j in range(self.N):
                    v = self.get_v_constraint(i, j)
                    if v is None:
                        vert_parts.append(" ")
                    elif v.direction == "<":
                        vert_parts.append("^")
                    else:
                        vert_parts.append("v")
                    if j < self.N - 1:
                        vert_parts.append(" ")
                lines.append(" ".join(vert_parts))

        return "\n".join(lines)
