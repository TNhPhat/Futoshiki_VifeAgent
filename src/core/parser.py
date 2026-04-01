from __future__ import annotations

import numpy as np

from constraints.inequality_constraint import InequalityConstraint
from .puzzle import Puzzle


class ParseError(ValueError):
    """
    Raised when a Futoshiki input file cannot be parsed.

    Parameters
    ----------
    message : str
        Human-readable description of what went wrong.
    file_path : str
        Path of the file that triggered the error.
    line_no : int
        1-based line number where the error was detected.
    """

    def __init__(self, message: str, file_path: str, line_no: int) -> None:
        self.file_path = file_path
        self.line_no = line_no
        super().__init__(f"{file_path}:{line_no}: {message}")


class Parser:
    """
    Reads Futoshiki puzzle input files and returns ``Puzzle`` instances.

    The expected file format is::

        N
        r0c0,r0c1,...,r0c(N-1)
        ...                          <- N grid rows
        h_r0_0,...,h_r0_(N-2)
        ...                          <- N horizontal-constraint rows (N-1 values each)
        v_r0_0,...,v_r0_(N-1)
        ...                          <- N-1 vertical-constraint rows (N values each)

    Grid encoding: ``0`` = empty cell; ``1..N`` = pre-filled clue.
    Constraint encoding: ``0`` = none; ``1`` = ``<``; ``-1`` = ``>``.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, file_path: str) -> Puzzle:
        """
        Parse a Futoshiki puzzle from an input file.

        Parameters
        ----------
        file_path : str
            Path to the input file (e.g. ``'inputs/input-01.txt'``).

        Returns
        -------
        Puzzle
            Fully initialised ``Puzzle`` with grid, constraints, and
            cached given/empty cell lists.

        Raises
        ------
        FileNotFoundError
            If *file_path* does not exist.
        ParseError
            If the file content does not match the expected format.
        """
        lines = self._read_lines(file_path)

        # --- line 0: grid size N ---
        try:
            N = int(lines[0])
        except (ValueError, IndexError):
            raise ParseError("first line must be an integer N", file_path, 1)

        if N < 2:
            raise ParseError(
                f"N must be >= 2, got {N}", file_path, 1
            )

        # --- lines 1..N: grid rows ---
        grid = self._parse_grid(lines, N, start=1, file_path=file_path)

        # --- lines N+1..2N: horizontal constraints ---
        h_constraints = self._parse_h_constraints(
            lines, N, start=N + 1, file_path=file_path
        )

        # --- lines 2N+1..3N-1: vertical constraints ---
        v_constraints = self._parse_v_constraints(
            lines, N, start=2 * N + 1, file_path=file_path
        )

        self._validate(N, grid, file_path)

        return Puzzle(
            N=N,
            grid=grid,
            h_constraints=h_constraints,
            v_constraints=v_constraints,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_lines(self, file_path: str) -> list[str]:
        """
        Open *file_path*, strip whitespace, and drop blank and comment lines.

        Lines whose first non-whitespace character is ``#`` are treated as
        comments and ignored, allowing annotated input files.

        Parameters
        ----------
        file_path : str
            Path to the file to read.

        Returns
        -------
        list of str
            Non-empty, non-comment stripped lines.
        """
        with open(file_path, encoding="utf-8") as fh:
            return [
                ln.strip()
                for ln in fh
                if ln.strip() and not ln.strip().startswith("#")
            ]

    def _parse_row(
        self,
        line: str,
        expected: int,
        line_no: int,
        file_path: str,
    ) -> list[int]:
        """
        Parse a single comma-separated integer line.

        Parameters
        ----------
        line : str
            Raw line content (already stripped).
        expected : int
            Expected number of integer tokens.
        line_no : int
            1-based line number (for error reporting).
        file_path : str
            Source file path (for error reporting).

        Returns
        -------
        list of int
            Parsed integer values.

        Raises
        ------
        ParseError
            If the token count does not match *expected* or any token is
            not a valid integer.
        """
        tokens = line.split(",")
        if len(tokens) != expected:
            raise ParseError(
                f"expected {expected} value(s), got {len(tokens)}",
                file_path,
                line_no,
            )
        values: list[int] = []
        for tok in tokens:
            try:
                values.append(int(tok.strip()))
            except ValueError:
                raise ParseError(
                    f"non-integer token {tok!r}",
                    file_path,
                    line_no,
                )
        return values

    def _parse_grid(
        self,
        lines: list[str],
        N: int,
        start: int,
        file_path: str,
    ) -> np.ndarray:
        """
        Consume N lines starting at *start* and build the grid array.

        Parameters
        ----------
        lines : list of str
            All non-blank lines from the input file.
        N : int
            Grid size.
        start : int
            0-based index into *lines* of the first grid row.
        file_path : str
            Source file path (for error reporting).

        Returns
        -------
        np.ndarray
            Shape ``(N, N)``, dtype ``int``.
        """
        self._check_enough_lines(lines, start + N - 1, file_path)
        rows: list[list[int]] = []
        for offset in range(N):
            line_no = start + offset + 1  # 1-based
            rows.append(
                self._parse_row(
                    lines[start + offset], N, line_no, file_path
                )
            )
        return np.array(rows, dtype=int)

    def _parse_h_constraints(
        self,
        lines: list[str],
        N: int,
        start: int,
        file_path: str,
    ) -> list[InequalityConstraint]:
        """
        Consume N lines of horizontal constraints starting at *start*.

        Each row contains N-1 integer values: ``0`` = none, ``1`` = ``<``,
        ``-1`` = ``>``.  Only non-zero entries produce an
        ``InequalityConstraint``.

        Parameters
        ----------
        lines : list of str
            All non-blank lines from the input file.
        N : int
            Grid size.
        start : int
            0-based index into *lines* of the first h-constraint row.
        file_path : str
            Source file path (for error reporting).

        Returns
        -------
        list of InequalityConstraint
            One entry per non-zero horizontal constraint in the puzzle.
        """
        self._check_enough_lines(lines, start + N - 1, file_path)
        constraints: list[InequalityConstraint] = []
        for i in range(N):
            line_no = start + i + 1
            values = self._parse_row(
                lines[start + i], N - 1, line_no, file_path
            )
            self._validate_constraint_row(values, line_no, file_path)
            for j, val in enumerate(values):
                if val == 1:
                    constraints.append(
                        InequalityConstraint(
                            cell1=(i, j),
                            cell2=(i, j + 1),
                            direction="<",
                        )
                    )
                elif val == -1:
                    constraints.append(
                        InequalityConstraint(
                            cell1=(i, j),
                            cell2=(i, j + 1),
                            direction=">",
                        )
                    )
        return constraints

    def _parse_v_constraints(
        self,
        lines: list[str],
        N: int,
        start: int,
        file_path: str,
    ) -> list[InequalityConstraint]:
        """
        Consume N-1 lines of vertical constraints starting at *start*.

        Each row contains N integer values: ``0`` = none, ``1`` = ``<``,
        ``-1`` = ``>``.  Only non-zero entries produce an
        ``InequalityConstraint``.

        Parameters
        ----------
        lines : list of str
            All non-blank lines from the input file.
        N : int
            Grid size.
        start : int
            0-based index into *lines* of the first v-constraint row.
        file_path : str
            Source file path (for error reporting).

        Returns
        -------
        list of InequalityConstraint
            One entry per non-zero vertical constraint in the puzzle.
        """
        self._check_enough_lines(lines, start + N - 2, file_path)
        constraints: list[InequalityConstraint] = []
        for i in range(N - 1):
            line_no = start + i + 1
            values = self._parse_row(
                lines[start + i], N, line_no, file_path
            )
            self._validate_constraint_row(values, line_no, file_path)
            for j, val in enumerate(values):
                if val == 1:
                    constraints.append(
                        InequalityConstraint(
                            cell1=(i, j),
                            cell2=(i + 1, j),
                            direction="<",
                        )
                    )
                elif val == -1:
                    constraints.append(
                        InequalityConstraint(
                            cell1=(i, j),
                            cell2=(i + 1, j),
                            direction=">",
                        )
                    )
        return constraints

    def _validate_constraint_row(
        self,
        values: list[int],
        line_no: int,
        file_path: str,
    ) -> None:
        """
        Raise ``ParseError`` if any value is not in {-1, 0, 1}.

        Parameters
        ----------
        values : list of int
            Parsed constraint values for one row.
        line_no : int
            1-based line number (for error reporting).
        file_path : str
            Source file path (for error reporting).
        """
        bad = [v for v in values if v not in (-1, 0, 1)]
        if bad:
            raise ParseError(
                f"constraint values must be in {{-1, 0, 1}}; found: {bad}",
                file_path,
                line_no,
            )

    def _validate(
        self,
        N: int,
        grid: np.ndarray,
        file_path: str,
    ) -> None:
        """
        Validate the grid array; raise ``ParseError`` on violation.

        Parameters
        ----------
        N : int
            Grid size.
        grid : np.ndarray
            Shape ``(N, N)``.
        file_path : str
            Source file path (for error reporting).

        Raises
        ------
        ParseError
            If any grid value is out of the allowed range.
        """
        if np.any(grid < 0) or np.any(grid > N):
            raise ParseError(
                f"grid values must be in {{0..{N}}}; "
                f"found out-of-range: {grid[(grid < 0) | (grid > N)].tolist()}",
                file_path,
                0,
            )

    def _check_enough_lines(
        self,
        lines: list[str],
        required_last_idx: int,
        file_path: str,
    ) -> None:
        """
        Raise ``ParseError`` if *lines* is too short to reach *required_last_idx*.

        Parameters
        ----------
        lines : list of str
            All non-blank lines.
        required_last_idx : int
            0-based index that must be reachable.
        file_path : str
            Source file path (for error reporting).

        Raises
        ------
        ParseError
            If ``len(lines) <= required_last_idx``.
        """
        if len(lines) <= required_last_idx:
            raise ParseError(
                f"file too short: need at least {required_last_idx + 1} "
                f"non-blank lines, got {len(lines)}",
                file_path,
                len(lines),
            )
