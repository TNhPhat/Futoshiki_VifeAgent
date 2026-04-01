from predicates import Literal
class Unifier:

    def unify(self, l1: Literal, l2: Literal):
        if l1.name != l2.name or l1.negated == l2.negated:
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

    def _unify_args(self, x, y, subst):
        x = self._apply(subst, x)
        y = self._apply(subst, y)

        if x == y:
            return subst

        if self._is_variable(x):
            return self._extend(subst, x, y)

        if self._is_variable(y):
            return self._extend(subst, y, x)

        return None

    def _is_variable(self, x):
        return isinstance(x, str) and x[0].islower()

    def _extend(self, subst, var, value):
        if var in subst:
            return self._unify_args(subst[var], value, subst)

        subst[var] = value
        return subst

    def _apply(self, subst, x):
        while isinstance(x, str) and x in subst:
            x = subst[x]
        return x