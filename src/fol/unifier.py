from fol.predicates import Literal
from typing import Dict, Optional, List, Any


# A Substitution maps variable names (lowercase strings) to values
Substitution = Dict[str, Any]


class Unifier:
    """Unifies two Literal objects by matching their arguments.

    Variable convention (Prolog-style):
      - Variables are lowercase strings: "v", "i", "j", "x"
      - Constants are integers or uppercase strings: 1, 2, "Val"

    This class provides:
      1. unify(l1, l2, subst) - main unification with existing substitution
      2. match(l1, l2) - convenience for SLD resolution (same sign)
      3. resolve(l1, l2) - for propositional resolution (opposite sign)
      4. apply/compose - substitution operations
      
    IMPORTANT: All methods return NEW substitutions (immutable-safe for backtracking)
    """

    def unify(self, l1: Literal, l2: Literal, 
              subst: Optional[Substitution] = None) -> Optional[Substitution]:
        """
        Unify two literals with an existing substitution.
        
        This is the main unification method for SLD resolution.
        Returns a NEW substitution (does not mutate input).
        
        Args:
            l1: First literal (typically the goal)
            l2: Second literal (typically the clause head)
            subst: Existing substitution to extend (default: empty)
            
        Returns:
            New substitution if unifiable, None otherwise
        """
        if subst is None:
            subst = {}
            
        # Must have same name and sign
        if l1.name != l2.name or l1.negated != l2.negated:
            return None
        if len(l1.args) != len(l2.args):
            return None

        # Copy to avoid mutating input
        result = subst.copy()
        
        for a1, a2 in zip(l1.args, l2.args):
            result = self._unify_terms(a1, a2, result)
            if result is None:
                return None

        return result

    def match(self, l1: Literal, l2: Literal) -> Optional[Substitution]:
        """Unify two literals with the SAME sign (for SLD resolution).

        Convenience method - equivalent to unify(l1, l2, {}).
        
        Returns:
            Substitution dict if unifiable, None otherwise.
        """
        return self.unify(l1, l2, {})

    def resolve(self, l1: Literal, l2: Literal) -> Optional[Substitution]:
        """Unify two literals with OPPOSITE sign (for resolution).

        Used in propositional resolution to cancel complementary literals.

        Returns:
            Substitution dict if resolvable, None otherwise.
        """
        if l1.name != l2.name:
            return None
        if l1.negated == l2.negated:
            return None  
        if len(l1.args) != len(l2.args):
            return None

        result = {}
        for a1, a2 in zip(l1.args, l2.args):
            result = self._unify_terms(a1, a2, result)
            if result is None:
                return None

        return result

    def _unify_terms(self, x: Any, y: Any, subst: Substitution) -> Optional[Substitution]:
        """Unify two terms with the given substitution.
        
        Returns a NEW substitution (copy) to maintain immutability.

        Rules:
          1. Apply existing substitutions first (follow binding chains)
          2. If equal after substitution -> return unchanged
          3. If either is a variable -> bind it (with occur check)
          4. Otherwise -> incompatible constants -> fail
        """
        x = self.apply(x, subst)
        y = self.apply(y, subst)

        if x == y:
            return subst

        if self._is_variable(x):
            # Occur check: x cannot appear in y
            if self._occurs_in(x, y, subst):
                return None
            result = subst.copy()
            result[x] = y
            return result

        if self._is_variable(y):
            # Occur check: y cannot appear in x
            if self._occurs_in(y, x, subst):
                return None
            result = subst.copy()
            result[y] = x
            return result

        return None  # two different constants

    def _occurs_in(self, var: str, term: Any, subst: Substitution) -> bool:
        """Occur check: does var occur in term?
        
        Prevents infinite structures like X = f(X).
        """
        term = self.apply(term, subst)
        if var == term:
            return True
        if isinstance(term, (list, tuple)):
            return any(self._occurs_in(var, t, subst) for t in term)
        return False

    def _is_variable(self, x: Any) -> bool:
        """A variable is a lowercase string, e.g. "v", "i", "x".

        Constants are integers or uppercase/mixed strings.
        """
        return isinstance(x, str) and len(x) > 0 and x[0].islower()

    def apply(self, term: Any, subst: Substitution) -> Any:
        """Apply substitution to a term (follow variable chain).

        Example: if subst = {"x": "y", "y": 3}, then apply("x", subst) -> 3
        """
        while isinstance(term, str) and term in subst:
            term = subst[term]
        return term

    def apply_to_literal(self, literal: Literal, subst: Substitution) -> Literal:
        """Apply a substitution to a Literal, replacing variables in args.

        Example:
          literal = Literal("Val", (0, 1, "v"), False)
          subst = {"v": 2}
          result = Literal("Val", (0, 1, 2), False)
        """
        new_args = tuple(self.apply(a, subst) for a in literal.args)
        return Literal(name=literal.name, args=new_args, negated=literal.negated)

    def compose(self, subst1: Substitution, subst2: Substitution) -> Optional[Substitution]:
        """
        Compose two substitutions: subst1 ∘ subst2.
        
        The result, when applied to a term, gives the same result as
        applying subst2 first, then subst1.
        
        Returns None if the substitutions are inconsistent.
        """
        result = subst1.copy()
        
        for var, val in subst2.items():
            # Apply subst1 to the value
            applied_val = self.apply(val, result)
            
            if var in result:
                # Check consistency
                existing = self.apply(result[var], result)
                if existing != applied_val:
                    return None  # Inconsistent
            else:
                result[var] = applied_val
        
        return result

    def rename_variables(self, literal: Literal, suffix: str) -> Literal:
        """Rename all variables in a literal by appending a suffix.

        Prevents variable capture when reusing clauses in SLD resolution.

        Example:
          Literal("Val", (0, "j", "v")) with suffix "_3"
          -> Literal("Val", (0, "j_3", "v_3"))
        """
        new_args = tuple(
            f"{a}_{suffix}" if self._is_variable(a) else a
            for a in literal.args
        )
        return Literal(name=literal.name, args=new_args, negated=literal.negated)