"""
Forward Chaining Engine for Horn Clauses (First-Order Logic).
"""

from typing import List, Set, Generator
from fol import Unifier, Literal, Substitution
from fol.horn_kb import HornClause

class ForwardChainingEngine:
    def __init__(self, rules: List[HornClause], initial_facts: List[Literal], max_iterations: int = 1000) -> None:
        self.rules = rules
        self.known_facts: Set[Literal] = set(initial_facts)
        self.fact_list: List[Literal] = list(initial_facts)
        self.inference_count = 0
        
        self._unifier = Unifier()
        self._max_iterations = max_iterations
        self._clause_counter = 0

    def run(self) -> Set[Literal]:
        """
        Executes the forward chaining fix-point iteration.
        Returns the completely saturated set of facts.
        """
        changed = True
        iterations = 0

        while changed and iterations < self._max_iterations:
            changed = False
            iterations += 1
            new_facts_this_round = []

            for rule in self.rules:
                self._clause_counter += 1
                renamed_rule = self._rename_clause_vars(rule, f"fw_{self._clause_counter}")

                for subst in self._match_body(list(renamed_rule.body), {}):
                    derived_fact = self._unifier.apply_to_literal(renamed_rule.head, subst)

                    if derived_fact not in self.known_facts:
                        self.known_facts.add(derived_fact)
                        new_facts_this_round.append(derived_fact)
                        changed = True

            self.fact_list.extend(new_facts_this_round)

        return self.known_facts

    def _match_body(self, body: List[Literal], subst: Substitution) -> Generator[Substitution, None, None]:
        """
        Recursively matches rule body literals to known facts.
        """
        self.inference_count += 1

        if not body:
            yield subst.copy()
            return

        first_lit = self._unifier.apply_to_literal(body[0], subst)
        remaining_body = body[1:]

        for fact in self.fact_list:
            new_subst = self._unifier.unify(first_lit, fact, subst)
            if new_subst is not None:
                yield from self._match_body(remaining_body, new_subst)

    def _rename_clause_vars(self, clause: HornClause, suffix: str) -> HornClause:
        """
        Renames variables in a clause to avoid capture (standardization apart).
        """
        renamed_head = self._unifier.rename_variables(clause.head, suffix)
        renamed_body = [
            self._unifier.rename_variables(lit, suffix)
            for lit in clause.body
        ]
        return HornClause(head=renamed_head, body=renamed_body)