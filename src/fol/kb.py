from __future__ import annotations

from dataclasses import dataclass, field

from .predicates import Clause, Literal


@dataclass
class KnowledgeBase:
    """
    A propositional CNF knowledge base.

    Stores a list of CNF clauses (disjunctions of literals) and a
    separate set of *facts* — literals that have been asserted as true,
    either directly or extracted from unit clauses.

    Parameters
    ----------
    clauses : list of Clause
        All CNF clauses in the knowledge base.
    facts : set of Literal
        Unit literals that are known to be true.
    """

    clauses: list[Clause] = field(default_factory=list)
    facts: set[Literal] = field(default_factory=set)

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def add_clause(self, clause: Clause) -> None:
        """
        Add a single CNF clause to the knowledge base.

        If the clause is a unit clause (exactly one literal), the
        literal is also added to the ``facts`` set.

        Parameters
        ----------
        clause : Clause
            A disjunction of literals to add.
        """
        self.clauses.append(clause)
        if len(clause) == 1:
            self.facts.add(clause[0])

    def add_clauses(self, clauses: list[Clause]) -> None:
        """
        Add multiple CNF clauses to the knowledge base.

        Equivalent to calling :meth:`add_clause` for each clause,
        but slightly more efficient.

        Parameters
        ----------
        clauses : list of Clause
            Clauses to add.
        """
        for clause in clauses:
            self.add_clause(clause)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_unit_clauses(self) -> list[Clause]:
        """
        Return all unit clauses (clauses with exactly one literal).

        Returns
        -------
        list of Clause
            Each element is a single-literal clause ``[lit]``.
        """
        return [c for c in self.clauses if len(c) == 1]

    def get_clauses_with(self, literal: Literal) -> list[Clause]:
        """
        Return all clauses that contain the given literal.

        Parameters
        ----------
        literal : Literal
            The literal to search for.

        Returns
        -------
        list of Clause
            Clauses containing ``literal`` (by equality).
        """
        return [c for c in self.clauses if literal in c]

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        """Return the total number of clauses in the knowledge base."""
        return len(self.clauses)

    def __repr__(self) -> str:
        """
        Return a summary string.

        Returns
        -------
        str
            e.g. ``"KnowledgeBase(clauses=352, facts=8)"``.
        """
        return (
            f"KnowledgeBase(clauses={len(self.clauses)}, "
            f"facts={len(self.facts)})"
        )
