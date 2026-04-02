from fol.predicates import Literal
from typing import Dict, Optional, List


# A Substitution maps variable names (lowercase strings) to values
Substitution = Dict[str, object]


class Unifier:
    """Unifies two Literal objects by matching their arguments.

    Variable convention (Prolog-style):
      - Variables are lowercase strings: "v", "i", "j", "x"
      - Constants are integers or uppercase strings: 1, 2, "Val"

    This class provides TWO operations:

      1. match(l1, l2) - for SLD resolution (same predicate, same sign)
         Used to unify a GOAL with a clause HEAD.
         Both must have the same name AND same negation sign.

      2. resolve(l1, l2) - for propositional resolution (opposite sign)
         Used to resolve complementary literals.
         Both must have the same name BUT opposite negation.

    """

    def match(self, l1: Literal, l2: Literal) -> Optional[Substitution]:
        """Unify two literals with the SAME sign (for SLD resolution).

        Used when matching a goal with a clause head:
          Goal:  Val(0, 1, "v")   (negated=False)
          Head:  Val(0, 1, 2)     (negated=False)
          Result: {"v": 2}

        Returns:
            Substitution dict if unifiable, None otherwise.
        """
        # SLD: goal and head must have same name AND same sign
        if l1.name != l2.name:
            return None
        if l1.negated != l2.negated:
            return None  
        if len(l1.args) != len(l2.args):
            return None

        subst = {}
        for a1, a2 in zip(l1.args, l2.args):
            result = self._unify_args(a1, a2, subst)
            if result is None:
                return None
            subst = result

        return subst

    def resolve(self, l1: Literal, l2: Literal) -> Optional[Substitution]:
        """Unify two literals with OPPOSITE sign (for resolution).

        Used in propositional resolution to cancel complementary literals:
          l1: Val(1, 2, 3)    (negated=False)
          l2: not Val(1, 2, 3)   (negated=True)
          Result: {} (resolved)

        Returns:
            Substitution dict if resolvable, None otherwise.
        """
        if l1.name != l2.name:
            return None
        if l1.negated == l2.negated:
            return None  
        if len(l1.args) != len(l2.args):
            return None

        subst = {}
        for a1, a2 in zip(l1.args, l2.args):
            result = self._unify_args(a1, a2, subst)
            if result is None:
                return None
            subst = result

        return subst

    def _unify_args(self, x, y, subst: Substitution) -> Optional[Substitution]:
        """Unify two individual arguments.

        Rules:
          1. Apply existing substitutions first (follow binding chains)
          2. If equal after substitution -> already unified
          3. If either is a variable (lowercase string) -> bind it
          4. Otherwise -> incompatible constants -> fail
        """
        x = self._apply(subst, x)
        y = self._apply(subst, y)

        if x == y:
            return subst

        if self._is_variable(x):
            return self._extend(subst, x, y) 

        if self._is_variable(y):
            return self._extend(subst, y, x)

        return None  # two different constants

    def _is_variable(self, x) -> bool:
        """A variable is a lowercase string, e.g. "v", "i", "x".

        Constants are integers or uppercase/mixed strings.
        """
        return isinstance(x, str) and len(x) > 0 and x[0].islower()

    def _extend(
        self, subst: Substitution, var: str, value
    ) -> Optional[Substitution]:
        """Bind a variable to a value in the substitution.

        If the variable is already bound, unify its current binding
        with the new value (ensures consistency).
        """
        if var in subst:
            return self._unify_args(subst[var], value, subst)
        subst[var] = value
        return subst

    def _apply(self, subst: Substitution, x):
        """Follow substitution chain until we reach a non-variable or unbound var.

        Example: if subst = {"x": "y", "y": 3}, then _apply("x") -> 3
        """
        while isinstance(x, str) and x in subst:
            x = subst[x]
        return x

    def apply_to_literal(self, literal: Literal, subst: Substitution) -> Literal:
        """Apply a substitution to a Literal, replacing variables in args.

        Example:
          literal = Literal("Val", (0, 1, "v"), False)
          subst = {"v": 2}
          result = Literal("Val", (0, 1, 2), False)
        """
        new_args = tuple(self._apply(subst, a) for a in literal.args)
        return Literal(name=literal.name, args=new_args, negated=literal.negated)

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