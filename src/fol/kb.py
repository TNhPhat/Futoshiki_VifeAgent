from __future__ import annotations

from dataclasses import dataclass, field

from .predicates import Clause, Literal


@dataclass
class CNFClauseKnowledgeBase:
    """
    A propositional CNF knowledge base.

    Stores a list of CNF clauses (disjunctions of literals) and a
    separate set of *facts* -- literals that have been asserted as true,
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

    def remove_clause(self, clause: Clause) -> None:
        """
        Remove the first occurrence of *clause* from the knowledge base.

        If the clause is a unit clause whose literal no longer appears in
        any remaining unit clause, the literal is also removed from the
        ``facts`` set.

        Parameters
        ----------
        clause : Clause
            The clause to remove.  Must be present; raises ``ValueError``
            otherwise.
        """
        self.clauses.remove(clause)
        if len(clause) == 1:
            lit = clause[0]
            if not any(len(c) == 1 and c[0] == lit for c in self.clauses):
                self.facts.discard(lit)

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

    def get_clauses(self) -> list[Clause]:
        """
        Return all clauses in the knowledge base.

        Returns
        -------
        list of Clause
            All CNF clauses currently stored.
        """
        return self.clauses

    def get_facts(self) -> set[Literal]:
        """
        Return all known facts (literals asserted as true).

        Returns
        -------
        set of Literal
            All literals derived from unit clauses.
        """
        return self.facts

    def is_known(self, literal: Literal) -> bool:
        """
        Check whether a literal is a known fact.

        Parameters
        ----------
        literal : Literal
            The literal to test.

        Returns
        -------
        bool
            ``True`` if *literal* is in the ``facts`` set.
        """
        return literal in self.facts

    def get_facts_by_predicate(self, name: str) -> list[Literal]:
        """
        Return all known facts whose predicate matches *name*.

        Useful for retrieving all ``Val``, ``Less``, or ``LessH`` facts
        without scanning all clauses.

        Parameters
        ----------
        name : str
            Predicate name to filter by (e.g. ``"Val"``, ``"Less"``).

        Returns
        -------
        list of Literal
            All facts ``f`` where ``f.name == name``.
        """
        return [f for f in self.facts if f.name == name]

    def __len__(self) -> int:
        """Return the total number of clauses in the knowledge base."""
        return len(self.clauses)

    def __repr__(self) -> str:
        """
        Return a summary string.

        Returns
        -------
        str
            e.g. ``"CNFClauseKnowledgeBase(clauses=352, facts=8)"``.
        """
        return (
            f"CNFClauseKnowledgeBase(clauses={len(self.clauses)}, "
            f"facts={len(self.facts)})"
        )
