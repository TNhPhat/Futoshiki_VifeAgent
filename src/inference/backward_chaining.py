"""
SLD Resolution Engine for Horn Clauses (Prolog-style Backward Chaining).

Implements standard SLD resolution with:
- Leftmost goal selection (Prolog selection rule)
- Unification with occur check (via Unifier class)
- Variable renaming (standardization apart)
- Backtracking via Python generators
"""

from typing import List, Optional, Generator
from futoshiki_vifeagent.fol import (
    HornClauseKnowledgeBase,
    HornClause,
    Literal,
    Substitution,
    Unifier,
)


class BackwardChainingEngine:
    """
    SLD resolution engine for pure positive Definite Clauses.
    
    Prolog-style solving:
    - Goals are resolved left-to-right (standard SLD)
    - Unification via Unifier class (immutable substitutions)
    - Backtracking via Python generators explores all choices
    """
    
    def __init__(self, kb: HornClauseKnowledgeBase, depth_limit: int = 500, limit_depth: bool = False) -> None:
        self._kb = kb
        self._unifier = Unifier()
        self._depth_limit = depth_limit
        self._clause_counter = 0
        self._inference_count = 0
        self._limit_depth = limit_depth
    
    @property
    def inference_count(self) -> int:
        """Number of inference steps performed."""
        return self._inference_count
    
    def prove(self, goal: Literal) -> Optional[Substitution]:
        """Prove a single goal. Returns substitution if successful, None otherwise."""
        return self.prove_all([goal])
    
    def prove_all(self, goals: List[Literal], on_step=None) -> Optional[Substitution]:
        """
        Prove a conjunction of goals via SLD resolution.

        Parameters
        ----------
        on_step : callable(subst: dict) | None
            Optional callback invoked after each successful unification step.
            Receives the current (partial) substitution so callers can
            reconstruct the induced partial solution at that point.

        Returns the first substitution that satisfies all goals, or None.
        """
        self._clause_counter = 0
        self._inference_count = 0

        for solution in self._sld_resolve(goals, {}, on_step=on_step):
            return solution  # Return first solution
        return None
    
    def prove_all_solutions(self, goals: List[Literal]) -> Generator[Substitution, None, None]:
        """
        Generate all solutions via backtracking.
        
        Yields each substitution that satisfies all goals.
        """
        self._clause_counter = 0
        self._inference_count = 0
        yield from self._sld_resolve(goals, {})
    
    def _sld_resolve(self,
                     goals: List[Literal],
                     subst: Substitution,
                     on_step=None) -> Generator[Substitution, None, None]:
        """
        Core SLD resolution algorithm (generator-based for backtracking).

        Args:
            goals:   Goal list (resolvent) — leftmost selected first.
            subst:   Current substitution (answer substitution).
            on_step: Optional callable(subst) invoked after each successful
                     unification, with the extended substitution.

        Yields:
            Substitutions that satisfy all goals.
        """
        self._inference_count += 1

        # Check depth limit
        if self._limit_depth and self._inference_count > self._depth_limit * 1000:
            return

        # Success: empty goal list
        if not goals:
            yield subst.copy()
            return

        # Select leftmost goal (Prolog selection rule)
        current_goal = self._unifier.apply_to_literal(goals[0], subst)
        remaining_goals = goals[1:]

        # Find all matching clauses for current goal
        matching_clauses = self._kb.get_clause_for(current_goal.name)

        for clause in matching_clauses:
            # Standardize apart: rename variables in clause
            self._clause_counter += 1
            renamed_clause = self._rename_clause_vars(clause, str(self._clause_counter))

            # Try to unify goal with clause head using Unifier
            new_subst = self._unifier.unify(current_goal, renamed_clause.head, subst)

            if new_subst is not None:
                # Notify caller of the new partial substitution.
                if on_step is not None:
                    on_step(new_subst)

                # New goals = clause body + remaining goals
                new_goals = list(renamed_clause.body) + remaining_goals

                # Recursively solve new goals
                yield from self._sld_resolve(new_goals, new_subst, on_step=on_step)
    
    def _rename_clause_vars(self, clause: HornClause, suffix: str) -> HornClause:
        """Rename variables in clause to avoid capture (standardization apart)."""
        renamed_head = self._unifier.rename_variables(clause.head, suffix)
        renamed_body = [
            self._unifier.rename_variables(lit, suffix) 
            for lit in clause.body
        ]
        return HornClause(head=renamed_head, body=renamed_body)
