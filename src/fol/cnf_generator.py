from __future__ import annotations

from typing import TYPE_CHECKING

from .axioms import Axioms
from .kb import CNFClauseKnowledgeBase

if TYPE_CHECKING:
    from core.puzzle import Puzzle


class CNFGenerator:
    """
    Ground all FOL axioms (A1-A16) into CNF clauses for a Futoshiki puzzle.

    This class acts as a facade over :class:`Axioms`: its single public
    method :meth:`generate` calls every axiom method, aggregates the
    resulting clauses, and returns them inside a :class:`CNFClauseKnowledgeBase`.
    """

    @staticmethod
    def generate_ground_kb(N: int) -> CNFClauseKnowledgeBase:
        """
        Build a ground CNF knowledge base from grid size only.

        This is equivalent to generating CNF for an empty NxN puzzle:
        no given clues and no inequality constraints.

        Parameters
        ----------
        N : int
            Grid size.

        Returns
        -------
        CNFClauseKnowledgeBase
            A populated KB containing all axioms that can be grounded
            using only ``N``.
        """
        import numpy as np
        from core.puzzle import Puzzle

        empty_puzzle = Puzzle(
            N=N,
            grid=np.zeros((N, N), dtype=int),
            h_constraints=[],
            v_constraints=[],
        )
        return CNFGenerator.generate(empty_puzzle)

    @staticmethod
    def generate(puzzle: Puzzle) -> CNFClauseKnowledgeBase:
        """
        Build a complete CNF knowledge base for the given puzzle.

        Calls ``Axioms.a1_*`` through ``Axioms.a16_*`` in order,
        collects all ground clauses, and stores them in a new
        :class:`CNFClauseKnowledgeBase`.

        Parameters
        ----------
        puzzle : Puzzle
            The Futoshiki puzzle instance carrying grid size ``N``,
            constraint arrays, and given clue values.

        Returns
        -------
        CNFClauseKnowledgeBase
            A populated knowledge base containing every ground CNF
            clause required to encode the puzzle.
        """
        N = puzzle.N
        kb = CNFClauseKnowledgeBase()

        # -- Cell constraints --------------------------------------
        kb.add_clauses(Axioms.a1_cell_existence(N))
        kb.add_clauses(Axioms.a2_cell_uniqueness(N))

        # -- Permutation constraints -------------------------------
        kb.add_clauses(Axioms.a3_row_uniqueness(N))
        kb.add_clauses(Axioms.a4_col_uniqueness(N))
        kb.add_clauses(Axioms.a12_row_surjection(N))
        kb.add_clauses(Axioms.a13_col_surjection(N))

        # -- Inequality constraints --------------------------------
        # Assert each puzzle constraint as a unit fact so the KB panel
        # can display and highlight LessH / GreaterH / LessV / GreaterV.
        kb.add_clauses(Axioms.a_constraint_facts(puzzle))
        kb.add_clauses(Axioms.a5_vertical_less(N, puzzle))
        kb.add_clauses(Axioms.a6_vertical_greater(N, puzzle))
        kb.add_clauses(Axioms.a7_horizontal_less(N, puzzle))
        kb.add_clauses(Axioms.a8_horizontal_greater(N, puzzle))
        kb.add_clauses(Axioms.a16_inequality_contrapositive(N, puzzle))

        # -- Clues & domain ----------------------------------------
        kb.add_clauses(Axioms.a9_given_clues(N, puzzle))
        kb.add_clauses(Axioms.a10_domain_bound())  # no-op

        # -- Less relation definition ------------------------------
        kb.add_clauses(Axioms.a11_less_ground_truth(N))
        kb.add_clauses(Axioms.a14_less_irreflexivity(N))
        kb.add_clauses(Axioms.a15_less_asymmetry(N))

        return kb
