from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

from .predicates import Clause, GreaterH, GreaterV, Less, LessH, LessV, Val

if TYPE_CHECKING:
    from core.puzzle import Puzzle


class Axioms:
    """
    Ground CNF clause generators for the Futoshiki FOL axiom system.

    Each static method corresponds to one axiom (A1–A16) from the
    specification and returns a list of CNF clauses.  Methods that
    depend on puzzle-specific data (constraints, given clues) accept
    a ``Puzzle`` parameter; the rest only need the grid size ``N``.

    All cell indices ``(i, j)`` are 0-based.
    All cell values ``v`` are 1-based (range ``1..N``).
    """

    # ==============================================================
    # Cell Constraints
    # ==============================================================

    @staticmethod
    def a1_cell_existence(N: int) -> list[Clause]:
        """
        A1 — Every cell must hold at least one value.

        For each cell ``(i, j)``, emits the clause:
        ``Val(i,j,1) ∨ Val(i,j,2) ∨ … ∨ Val(i,j,N)``.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            N² clauses, each a disjunction of N literals.
        """
        clauses: list[Clause] = []
        for i in range(N):
            for j in range(N):
                clause = [Val(i, j, v) for v in range(1, N + 1)]
                clauses.append(clause)
        return clauses

    @staticmethod
    def a2_cell_uniqueness(N: int) -> list[Clause]:
        """
        A2 — A cell cannot hold two different values at once.

        For each cell ``(i, j)`` and each pair ``v1 < v2``, emits:
        ``¬Val(i,j,v1) ∨ ¬Val(i,j,v2)``.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            N² x C(N,2) clauses, each a binary clause.
        """
        clauses: list[Clause] = []
        for i in range(N):
            for j in range(N):
                for v1, v2 in combinations(range(1, N + 1), 2):
                    clauses.append([~Val(i, j, v1), ~Val(i, j, v2)])
        return clauses

    # ==============================================================
    # Permutation Constraints
    # ==============================================================

    @staticmethod
    def a3_row_uniqueness(N: int) -> list[Clause]:
        """
        A3 — No value repeats in the same row.

        For each row ``i``, each column pair ``j1 < j2``, and each
        value ``v``, emits: ``¬Val(i,j1,v) ∨ ¬Val(i,j2,v)``.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            N x C(N,2) x N clauses.
        """
        clauses: list[Clause] = []
        for i in range(N):
            for j1, j2 in combinations(range(N), 2):
                for v in range(1, N + 1):
                    clauses.append(
                        [~Val(i, j1, v), ~Val(i, j2, v)]
                    )
        return clauses

    @staticmethod
    def a4_col_uniqueness(N: int) -> list[Clause]:
        """
        A4 — No value repeats in the same column.

        For each column ``j``, each row pair ``i1 < i2``, and each
        value ``v``, emits: ``¬Val(i1,j,v) ∨ ¬Val(i2,j,v)``.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            N x C(N,2) x N clauses.
        """
        clauses: list[Clause] = []
        for j in range(N):
            for i1, i2 in combinations(range(N), 2):
                for v in range(1, N + 1):
                    clauses.append(
                        [~Val(i1, j, v), ~Val(i2, j, v)]
                    )
        return clauses

    @staticmethod
    def a12_row_surjection(N: int) -> list[Clause]:
        """
        A12 — Every value 1..N must appear in each row.

        For each row ``i`` and each value ``v``, emits:
        ``Val(i,0,v) ∨ Val(i,1,v) ∨ … ∨ Val(i,N-1,v)``.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            N² clauses, each a disjunction of N literals.
        """
        clauses: list[Clause] = []
        for i in range(N):
            for v in range(1, N + 1):
                clause = [Val(i, j, v) for j in range(N)]
                clauses.append(clause)
        return clauses

    @staticmethod
    def a13_col_surjection(N: int) -> list[Clause]:
        """
        A13 — Every value 1..N must appear in each column.

        For each column ``j`` and each value ``v``, emits:
        ``Val(0,j,v) ∨ Val(1,j,v) ∨ … ∨ Val(N-1,j,v)``.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            N² clauses, each a disjunction of N literals.
        """
        clauses: list[Clause] = []
        for j in range(N):
            for v in range(1, N + 1):
                clause = [Val(i, j, v) for i in range(N)]
                clauses.append(clause)
        return clauses

    # ==============================================================
    # Inequality Constraints
    # ==============================================================

    @staticmethod
    def a5_vertical_less(N: int, puzzle: Puzzle) -> list[Clause]:
        """
        A5 — Vertical ``<`` constraint enforcement.

        For each cell ``(i, j)`` where ``LessV(i, j)`` exists
        (``v_constraints[i, j] == 1``), and for each value pair
        ``(v1, v2)``, emits:
        ``¬Val(i,j,v1) ∨ ¬Val(i+1,j,v2) ∨ Less(v1,v2)``.

        Parameters
        ----------
        N : int
            Grid size.
        puzzle : Puzzle
            Puzzle instance carrying constraint arrays.

        Returns
        -------
        list of Clause
            Three-literal clauses for each constraint position
            and value pair.
        """
        clauses: list[Clause] = []
        for c in puzzle.v_constraints:
            if c.direction != "<":
                continue
            (i, j), (i2, _) = c.cell1, c.cell2
            for v1 in range(1, N + 1):
                for v2 in range(1, N + 1):
                    clauses.append([
                        ~Val(i, j, v1),
                        ~Val(i2, j, v2),
                        Less(v1, v2),
                    ])
        return clauses

    @staticmethod
    def a6_vertical_greater(
        N: int, puzzle: Puzzle
    ) -> list[Clause]:
        """
        A6 — Vertical ``>`` constraint enforcement.

        For each cell ``(i, j)`` where ``GreaterV(i, j)`` exists
        (``v_constraints`` entry with ``direction == '>'``), and for each
        value pair ``(v1, v2)``, emits:
        ``¬Val(i,j,v1) ∨ ¬Val(i+1,j,v2) ∨ Less(v2,v1)``.

        Parameters
        ----------
        N : int
            Grid size.
        puzzle : Puzzle
            Puzzle instance carrying constraint lists.

        Returns
        -------
        list of Clause
            Three-literal clauses for each constraint position
            and value pair.
        """
        clauses: list[Clause] = []
        for c in puzzle.v_constraints:
            if c.direction != ">":
                continue
            (i, j), (i2, _) = c.cell1, c.cell2
            for v1 in range(1, N + 1):
                for v2 in range(1, N + 1):
                    clauses.append([
                        ~Val(i, j, v1),
                        ~Val(i2, j, v2),
                        Less(v2, v1),
                    ])
        return clauses

    @staticmethod
    def a7_horizontal_less(
        N: int, puzzle: Puzzle
    ) -> list[Clause]:
        """
        A7 — Horizontal ``<`` constraint enforcement.

        For each cell ``(i, j)`` where ``LessH(i, j)`` exists
        (``h_constraints`` entry with ``direction == '<'``), and for each
        value pair ``(v1, v2)``, emits:
        ``¬Val(i,j,v1) ∨ ¬Val(i,j+1,v2) ∨ Less(v1,v2)``.

        Parameters
        ----------
        N : int
            Grid size.
        puzzle : Puzzle
            Puzzle instance carrying constraint lists.

        Returns
        -------
        list of Clause
            Three-literal clauses for each constraint position
            and value pair.
        """
        clauses: list[Clause] = []
        for c in puzzle.h_constraints:
            if c.direction != "<":
                continue
            (i, j), (_, j2) = c.cell1, c.cell2
            for v1 in range(1, N + 1):
                for v2 in range(1, N + 1):
                    clauses.append([
                        ~Val(i, j, v1),
                        ~Val(i, j2, v2),
                        Less(v1, v2),
                    ])
        return clauses

    @staticmethod
    def a8_horizontal_greater(
        N: int, puzzle: Puzzle
    ) -> list[Clause]:
        """
        A8 — Horizontal ``>`` constraint enforcement.

        For each cell ``(i, j)`` where ``GreaterH(i, j)`` exists
        (``h_constraints`` entry with ``direction == '>'``), and for each
        value pair ``(v1, v2)``, emits:
        ``¬Val(i,j,v1) ∨ ¬Val(i,j+1,v2) ∨ Less(v2,v1)``.

        Parameters
        ----------
        N : int
            Grid size.
        puzzle : Puzzle
            Puzzle instance carrying constraint lists.

        Returns
        -------
        list of Clause
            Three-literal clauses for each constraint position
            and value pair.
        """
        clauses: list[Clause] = []
        for c in puzzle.h_constraints:
            if c.direction != ">":
                continue
            (i, j), (_, j2) = c.cell1, c.cell2
            for v1 in range(1, N + 1):
                for v2 in range(1, N + 1):
                    clauses.append([
                        ~Val(i, j, v1),
                        ~Val(i, j2, v2),
                        Less(v2, v1),
                    ])
        return clauses

    @staticmethod
    def a_constraint_facts(puzzle: "Puzzle") -> list[Clause]:
        """
        Unit clauses asserting each inequality constraint in the puzzle.

        For each horizontal ``<`` constraint at ``(i, j)`` emits ``[LessH(i,j)]``;
        for ``>`` emits ``[GreaterH(i,j)]``.  Similarly for vertical constraints.

        These unit facts make each constraint directly visible in the KB facts
        list and allow the UI to highlight the two cells it involves.

        Parameters
        ----------
        puzzle : Puzzle
            Puzzle instance carrying ``h_constraints`` and ``v_constraints``.

        Returns
        -------
        list of Clause
            One unit clause per inequality constraint.
        """
        clauses: list[Clause] = []
        for c in puzzle.h_constraints:
            i, j = c.cell1
            clauses.append([LessH(i, j) if c.direction == "<" else GreaterH(i, j)])
        for c in puzzle.v_constraints:
            i, j = c.cell1
            clauses.append([LessV(i, j) if c.direction == "<" else GreaterV(i, j)])
        return clauses

    # ==============================================================
    # Clues & Domain
    # ==============================================================

    @staticmethod
    def a9_given_clues(N: int, puzzle: "Puzzle") -> list[Clause]:
        """
        A9 — Pre-filled cells must keep their given value.

        For each given cell ``(i, j, v)`` in the puzzle, emits
        a unit clause: ``[Val(i, j, v)]``.

        Parameters
        ----------
        N : int
            Grid size (unused, accepted for API consistency).
        puzzle : Puzzle
            Puzzle instance carrying the grid with clue values.

        Returns
        -------
        list of Clause
            One unit clause per pre-filled cell.
        """
        clauses: list[Clause] = []
        for i, j, v in puzzle.get_given_cells():
            clauses.append([Val(i, j, v)])
        return clauses

    @staticmethod
    def a10_domain_bound() -> list[Clause]:
        """
        A10 — Cell values must be in {1..N}.

        This axiom is satisfied implicitly by only grounding
        values in ``range(1, N + 1)``.  No clauses are emitted.

        Returns
        -------
        list of Clause
            Always an empty list.
        """
        return []

    # ==============================================================
    # Less Relation Definition
    # ==============================================================

    @staticmethod
    def a11_less_ground_truth(N: int) -> list[Clause]:
        """
        A11 — Define which number pairs satisfy "less than".

        For each pair ``(a, b)`` where ``1 ≤ a < b ≤ N``, emits
        a unit fact: ``[Less(a, b)]``.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            C(N,2) unit clauses.
        """
        clauses: list[Clause] = []
        for a, b in combinations(range(1, N + 1), 2):
            clauses.append([Less(a, b)])
        return clauses

    @staticmethod
    def a14_less_irreflexivity(N: int) -> list[Clause]:
        """
        A14 — No number is less than itself.

        For each value ``v`` in ``1..N``, emits: ``[¬Less(v, v)]``.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            N unit clauses.
        """
        clauses: list[Clause] = []
        for v in range(1, N + 1):
            clauses.append([~Less(v, v)])
        return clauses

    @staticmethod
    def a15_less_asymmetry(N: int) -> list[Clause]:
        """
        A15 — If a < b then b cannot be < a.

        For each distinct pair ``v1 < v2``, emits:
        ``¬Less(v1, v2) ∨ ¬Less(v2, v1)``.

        The clause is symmetric, so only pairs with ``v1 < v2``
        are generated to avoid duplicates.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        list of Clause
            C(N,2) binary clauses.
        """
        clauses: list[Clause] = []
        for v1, v2 in combinations(range(1, N + 1), 2):
            clauses.append([~Less(v1, v2), ~Less(v2, v1)])
        return clauses

    # ==============================================================
    # Inequality Contrapositive
    # ==============================================================

    @staticmethod
    def a16_inequality_contrapositive(
        N: int, puzzle: Puzzle
    ) -> list[Clause]:
        """
        A16 — Directly forbid value pairs that violate inequalities.

        For each inequality constraint, emits binary clauses that
        ban all value pairs which would violate the constraint:

        * ``LessH(i,j)``  (left < right):
          ``¬Val(i,j,v1) ∨ ¬Val(i,j+1,v2)`` for v1 ≥ v2.
        * ``GreaterH(i,j)`` (left > right):
          ``¬Val(i,j,v1) ∨ ¬Val(i,j+1,v2)`` for v1 ≤ v2.
        * ``LessV(i,j)``  (top < bottom):
          ``¬Val(i,j,v1) ∨ ¬Val(i+1,j,v2)`` for v1 ≥ v2.
        * ``GreaterV(i,j)`` (top > bottom):
          ``¬Val(i,j,v1) ∨ ¬Val(i+1,j,v2)`` for v1 ≤ v2.

        This is **key for propagation**: unit propagation can prune
        impossible values immediately without multi-step inference.

        Parameters
        ----------
        N : int
            Grid size.
        puzzle : Puzzle
            Puzzle instance carrying constraint arrays.

        Returns
        -------
        list of Clause
            Binary clauses for every forbidden value pair at every
            constrained cell pair.
        """
        clauses: list[Clause] = []
        values = range(1, N + 1)

        # Horizontal constraints
        for c in puzzle.h_constraints:
            (i, j), (_, j2) = c.cell1, c.cell2
            for v1 in values:
                for v2 in values:
                    # LessH: need v1 < v2, ban v1 >= v2
                    if c.direction == "<" and v1 >= v2:
                        clauses.append([~Val(i, j, v1), ~Val(i, j2, v2)])
                    # GreaterH: need v1 > v2, ban v1 <= v2
                    elif c.direction == ">" and v1 <= v2:
                        clauses.append([~Val(i, j, v1), ~Val(i, j2, v2)])

        # Vertical constraints
        for c in puzzle.v_constraints:
            (i, j), (i2, _) = c.cell1, c.cell2
            for v1 in values:
                for v2 in values:
                    # LessV: need v1 < v2, ban v1 >= v2
                    if c.direction == "<" and v1 >= v2:
                        clauses.append([~Val(i, j, v1), ~Val(i2, j, v2)])
                    # GreaterV: need v1 > v2, ban v1 <= v2
                    elif c.direction == ">" and v1 <= v2:
                        clauses.append([~Val(i, j, v1), ~Val(i2, j, v2)])

        return clauses
