from __future__ import annotations

from .puzzle import Puzzle


class Formatter:
    """
    Renders a Futoshiki puzzle as a human-readable string or file.

    Uses the puzzle's own grid; empty cells (value 0) are shown as
    ``"."``.  Works for both unsolved and solved puzzles — solvers
    should write their result back into ``puzzle.grid`` before calling.

    Example output::

        1 < 3   2
            ^
        2   1 < 3

        3   2   1

    Horizontal constraint symbols (``<``, ``>``) appear inline between
    cell values.  Vertical constraint symbols (``^``, ``v``) appear on
    their own line between grid rows, aligned under their column.
    Rows with no vertical constraints produce an empty separator line.
    """

    _EMPTY_CELL = "."  # display character for unsolved cells (value 0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(self, puzzle: Puzzle) -> str:
        """
        Render a puzzle as a formatted string.

        Parameters
        ----------
        puzzle : Puzzle
            The puzzle carrying grid values and constraint information.
            Empty cells (value 0) are rendered as ``"."``.

        Returns
        -------
        str
            Multi-line string ready for printing or writing to a file.
        """
        lines: list[str] = []
        for i in range(puzzle.N):
            lines.append(self._format_value_row(puzzle, i))
            if i < puzzle.N - 1:
                lines.append(self._format_separator_row(puzzle, i))
        return "\n".join(lines)

    def write(self, file_path: str, puzzle: Puzzle) -> None:
        """
        Write a formatted puzzle to a file.

        Parameters
        ----------
        file_path : str
            Destination path (e.g. ``'outputs/output-01.txt'``).
            Parent directory must already exist.
        puzzle : Puzzle
            The puzzle carrying grid values and constraint information.

        Returns
        -------
        None
        """
        content = self.format(puzzle)
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(content + "\n")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _format_value_row(self, puzzle: Puzzle, i: int) -> str:
        """
        Format one grid row with inline horizontal constraint symbols.

        Cell values and constraint tokens are collected as separate items
        then joined with a single space.  A ``" "`` (space) token between
        two cells with no constraint produces three spaces total once the
        join separator is included, matching the expected output width.
        Empty cells (value 0) are rendered as ``"."``.

        Parameters
        ----------
        puzzle : Puzzle
            Source of grid values and constraint data.
        i : int
            0-based row index.

        Returns
        -------
        str
            Formatted row string, e.g. ``"1 < .   2"``.
        """
        parts: list[str] = []
        for j in range(puzzle.N):
            val = int(puzzle.grid[i, j])
            parts.append(self._EMPTY_CELL if val == 0 else str(val))
            if j < puzzle.N - 1:
                h = puzzle.get_h_constraint(i, j)
                parts.append("<" if h == 1 else (">" if h == -1 else " "))
        return " ".join(parts)

    def _format_separator_row(self, puzzle: Puzzle, i: int) -> str:
        """
        Format the vertical constraint row between grid rows *i* and *i+1*.

        Vertical symbols and gap tokens are collected and joined the same
        way as value rows so that each symbol aligns under its column.
        Trailing whitespace is stripped; an all-space row becomes ``""``.

        Parameters
        ----------
        puzzle : Puzzle
            Source of vertical constraint data.
        i : int
            0-based index of the upper grid row (constraint is below it).

        Returns
        -------
        str
            Formatted separator string, e.g. ``"    ^"`` or ``""``.
        """
        parts: list[str] = []
        for j in range(puzzle.N):
            v = puzzle.get_v_constraint(i, j)
            parts.append("^" if v == 1 else ("v" if v == -1 else " "))
            if j < puzzle.N - 1:
                parts.append(" ")  # column gap — mirrors h-constraint slot
        return " ".join(parts).rstrip()
