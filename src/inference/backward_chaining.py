"""
SLD Resolution Engine for Horn Clauses (Prolog-style Backward Chaining).

Implements standard SLD resolution with:
- Leftmost goal selection (Prolog selection rule)
- Unification with occur check
- Variable renaming (standardization apart)
- Negation-as-Failure (NAF) for closed-world assumption
"""

from typing import List, Optional, Set, FrozenSet
from fol import Unifier, HornClauseKnowledgeBase, Literal, Substitution
from fol.horn_kb import HornClause


class BackwardChainingEngine:
    """
    SLD resolution engine with Negation-as-Failure (NAF) for Horn clauses.
    
    Handles two types of negation:
    1. Rule-derived: ~P proven via rules with negated heads
    2. NAF: ~P succeeds if P cannot be proven (closed-world assumption)
    
    NAF is only applied to predicates in naf_predicates set (default: Less, Diff).
    For Val predicates, only rule-derived negation is used.
    """
    
    def __init__(self, kb: HornClauseKnowledgeBase, depth_limit: int = 50,
                 naf_predicates: Optional[Set[str]] = None) -> None:
        self._kb = kb
        self._unifier = Unifier()
        self._depth_limit = depth_limit
        self._clause_counter = 0
        self._naf_predicates = naf_predicates or {"Less", "Diff"}
    
    def prove(self, goal: Literal) -> Optional[Substitution]:
        """Prove a single goal. Returns substitution if successful, None otherwise."""
        return self.prove_all([goal])
    
    def prove_all(self, goals: List[Literal]) -> Optional[Substitution]:
        """Prove a conjunction of goals. Returns substitution if successful."""
        self._clause_counter = 0
        return self._sld_resolve(
            goals=goals,
            subst={},
            depth=0,
            proven_negative=set(),
            visited=frozenset()
        )
    
    def _sld_resolve(self, 
                     goals: List[Literal], 
                     subst: Substitution, 
                     depth: int,
                     proven_negative: Set[Literal],
                     visited: FrozenSet[Literal]) -> Optional[Substitution]:
        """
        Core SLD resolution algorithm.
        
        Args:
            goals: Goal list (resolvent) - leftmost selected first
            subst: Current substitution (answer substitution)
            depth: Recursion depth for limit checking
            proven_negative: Cache of proven NAF literals
            visited: Loop detection set
            
        Returns:
            Substitution if goals are provable, None otherwise
        """
        if depth > self._depth_limit:
            return None
        
        if not goals:
            return subst  # Success: empty goal list
        
        # Select leftmost goal (Prolog selection rule)
        current_goal = self._unifier.apply_to_literal(goals[0], subst)
        remaining_goals = goals[1:]
        
        # Try matching clauses first (works for both positive and negated goals)
        result = self._try_clause_matching(
            current_goal, remaining_goals, subst, depth, proven_negative, visited
        )
        if result is not None:
            return result
        
        # Fall back to NAF for negated goals (only for allowed predicates)
        if current_goal.negated and current_goal.name in self._naf_predicates:
            return self._try_naf(
                current_goal, remaining_goals, subst, depth, proven_negative, visited
            )
        
        return None
    
    def _try_clause_matching(self,
                              goal: Literal,
                              remaining_goals: List[Literal],
                              subst: Substitution,
                              depth: int,
                              proven_negative: Set[Literal],
                              visited: FrozenSet[Literal]) -> Optional[Substitution]:
        """
        Try to prove goal by unifying with clause heads.
        
        Standard SLD resolution step:
        1. Find clause with head unifying with goal
        2. Apply MGU to body literals
        3. Add body to goal list
        4. Recurse
        """
        if goal in visited:
            return None  # Loop detection
        
        new_visited = visited | {goal}
        
        for clause in self._kb.get_clause_for(goal.name):
            # Rename variables (standardization apart)
            self._clause_counter += 1
            renamed = self._rename_clause_vars(clause, str(self._clause_counter))
            
            # Unify goal with clause head
            mgu = self._unifier.match(goal, renamed.head)
            if mgu is None:
                continue
            
            # Compose substitutions
            composed = {**subst, **mgu}
            
            # Build new goal list: body + remaining
            new_goals = [
                self._unifier.apply_to_literal(lit, composed)
                for lit in renamed.body
            ] + remaining_goals
            
            # Recurse
            result = self._sld_resolve(
                new_goals, composed, depth + 1, proven_negative, new_visited
            )
            if result is not None:
                return result
        
        return None
    
    def _try_naf(self,
                 goal: Literal,
                 remaining_goals: List[Literal],
                 subst: Substitution,
                 depth: int,
                 proven_negative: Set[Literal],
                 visited: FrozenSet[Literal]) -> Optional[Substitution]:
        """
        Negation-as-Failure: ~P succeeds if P cannot be proven.
        
        Implements closed-world assumption for specified predicates.
        """
        if self._has_unbound_variables(goal, subst):
            return None  # NAF requires ground literals
        
        if goal in proven_negative:
            return self._sld_resolve(
                remaining_goals, subst, depth, proven_negative, visited
            )
        
        # Try to prove positive version
        positive_goal = ~goal
        proof = self._sld_resolve(
            [positive_goal], subst, depth + 1, proven_negative, visited
        )
        
        if proof is None:
            # P unprovable → ~P succeeds
            new_proven = proven_negative | {goal}
            return self._sld_resolve(
                remaining_goals, subst, depth, new_proven, visited
            )
        
        return None  # P proven → ~P fails
    
    def _has_unbound_variables(self, literal: Literal, subst: Substitution) -> bool:
        """Check if literal contains unbound variables."""
        applied = self._unifier.apply_to_literal(literal, subst)
        return any(self._unifier._is_variable(arg) for arg in applied.args)
    
    def _rename_clause_vars(self, clause: HornClause, suffix: str) -> HornClause:
        """Rename variables in clause to avoid capture (standardization apart)."""
        renamed_head = self._unifier.rename_variables(clause.head, suffix)
        renamed_body = [
            self._unifier.rename_variables(lit, suffix) 
            for lit in clause.body
        ]
        return HornClause(head=renamed_head, body=renamed_body)