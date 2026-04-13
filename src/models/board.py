"""
Board model: mutable solving / playing state on top of an immutable Puzzle.

Holds the user's current grid, pencil-mark notes, selected cell, error
highlights, and an undo stack.  Provides set_value / toggle_note / undo /
get_hint, and real-time conflict detection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from core.puzzle import Puzzle

if TYPE_CHECKING:
    pass


@dataclass
class Board:
    """Mutable board state wrapping an immutable Puzzle."""

    puzzle: Puzzle

    # Mutable grid: copy of puzzle.grid; user can edit non-given cells.
    grid: np.ndarray = field(init=False)

    # Pencil marks: cell → set of candidate values the user has noted.
    notes: dict[tuple[int, int], set[int]] = field(default_factory=dict)

    # Currently selected cell (row, col) or None.
    selected: tuple[int, int] | None = None

    # Cells with detected conflicts.
    errors: set[tuple[int, int]] = field(default_factory=set)

    # Undo stack of full grid snapshots (before each edit).
    undo_stack: list[np.ndarray] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.grid = self.puzzle.grid.copy()
        self._recompute_errors()

    # ------------------------------------------------------------------
    # Value entry
    # ------------------------------------------------------------------

    def set_value(self, i: int, j: int, v: int) -> None:
        """
        Set cell (i, j) to value v (0 = clear).

        Pushes a snapshot onto the undo stack, updates the grid,
        clears pencil marks for that cell, removes v from the notes of
        every peer in the same row/column, and recomputes errors.
        Given cells are silently ignored.
        """
        if self.puzzle.is_given(i, j):
            return
        self.undo_stack.append(self.grid.copy())
        self.grid[i, j] = v
        # Clear notes for this cell when a definite value is entered.
        self.notes.pop((i, j), None)
        # Remove v from all peers' notes so stale candidates disappear.
        if v != 0:
            N = self.puzzle.N
            for c in range(N):
                if c != j and (i, c) in self.notes:
                    self.notes[(i, c)].discard(v)
            for r in range(N):
                if r != i and (r, j) in self.notes:
                    self.notes[(r, j)].discard(v)
        self._recompute_errors()

    def clear_value(self, i: int, j: int) -> None:
        """Clear a user-entered value (set to 0)."""
        self.set_value(i, j, 0)

    # ------------------------------------------------------------------
    # Notes (pencil marks)
    # ------------------------------------------------------------------

    def toggle_note(self, i: int, j: int, v: int) -> None:
        """
        Toggle pencil mark v in cell (i, j).

        Only allowed on empty, non-given cells.
        Adding a value that already appears in the same row or column is
        silently ignored (the number cannot be a valid candidate there).
        Removing an existing note is always allowed.
        """
        if self.puzzle.is_given(i, j):
            return
        if self.grid[i, j] != 0:
            return  # can't note on a filled cell
        cell_notes = self.notes.setdefault((i, j), set())
        if v in cell_notes:
            cell_notes.discard(v)
        else:
            # Block adding a note that is already placed in the same row or column.
            N = self.puzzle.N
            row_has_v = any(int(self.grid[i, c]) == v for c in range(N) if c != j)
            col_has_v = any(int(self.grid[r, j]) == v for r in range(N) if r != i)
            if not row_has_v and not col_has_v:
                cell_notes.add(v)

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

    def undo(self) -> None:
        """Restore the grid to the previous state (if any)."""
        if not self.undo_stack:
            return
        self.grid = self.undo_stack.pop()
        self._recompute_errors()

    # ------------------------------------------------------------------
    # Hint
    # ------------------------------------------------------------------

    def get_hint(self) -> tuple[int, int, int] | None:
        """
        Find a cell whose value is logically forced by AC3 domain reduction.

        Returns (row, col, value) or None if no forced cell is found.
        The hint does NOT modify the board — the caller decides whether to apply it.
        """
        from fol.horn_generator import HornClauseGenerator

        # Build a temporary Puzzle reflecting the current board state.
        tmp_puzzle = Puzzle(
            N=self.puzzle.N,
            grid=self.grid.copy(),
            h_constraints=list(self.puzzle.h_constraints),
            v_constraints=list(self.puzzle.v_constraints),
        )

        try:
            domains = HornClauseGenerator._ac3_domains(tmp_puzzle)
        except Exception:
            return None

        if domains is None:
            return None

        # Find any empty cell with a singleton domain.
        for (r, c), dom in domains.items():
            if self.grid[r, c] == 0 and len(dom) == 1:
                return (r, c, next(iter(dom)))

        return None

    # ------------------------------------------------------------------
    # Completion check
    # ------------------------------------------------------------------

    def is_complete(self) -> bool:
        """Return True when all cells are filled and there are no errors."""
        return bool(np.all(self.grid != 0)) and len(self.errors) == 0

    # ------------------------------------------------------------------
    # Error detection
    # ------------------------------------------------------------------

    def _recompute_errors(self) -> None:
        """
        Recompute the set of cells that currently violate any constraint.

        A cell is in 'errors' if:
        - Its row contains a duplicate non-zero value.
        - Its column contains a duplicate non-zero value.
        - It participates in a violated inequality constraint.
        """
        N = self.puzzle.N
        new_errors: set[tuple[int, int]] = set()

        # Row uniqueness
        for r in range(N):
            seen: dict[int, list[int]] = {}
            for c in range(N):
                v = int(self.grid[r, c])
                if v != 0:
                    seen.setdefault(v, []).append(c)
            for v, cols in seen.items():
                if len(cols) > 1:
                    for c in cols:
                        new_errors.add((r, c))

        # Column uniqueness
        for c in range(N):
            seen = {}
            for r in range(N):
                v = int(self.grid[r, c])
                if v != 0:
                    seen.setdefault(v, []).append(r)
            for v, rows in seen.items():
                if len(rows) > 1:
                    for r in rows:
                        new_errors.add((r, c))

        # Inequality constraints
        for constraint in self.puzzle.h_constraints + self.puzzle.v_constraints:
            r1, c1 = constraint.cell1
            r2, c2 = constraint.cell2
            v1 = int(self.grid[r1, c1])
            v2 = int(self.grid[r2, c2])
            if v1 != 0 and v2 != 0:
                violated = (
                    (constraint.direction == "<" and not (v1 < v2))
                    or (constraint.direction == ">" and not (v1 > v2))
                )
                if violated:
                    new_errors.add((r1, c1))
                    new_errors.add((r2, c2))

        self.errors = new_errors
