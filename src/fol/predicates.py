from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Literal:
    """
    A ground literal in propositional logic.

    Literals are immutable and hashable, making them safe to use
    inside ``set``, ``frozenset``, and ``dict``.  Negation is
    performed with the ``~`` operator.

    Parameters
    ----------
    name : str
        Predicate name (e.g. ``"Val"``, ``"Less"``).
    args : tuple[int, ...]
        Ground arguments (e.g. ``(0, 1, 3)`` for Val(0,1,3)).
    negated : bool
        ``True`` if this literal is negated (¬).
    """

    name: str
    args: tuple
    negated: bool = False

    def __invert__(self) -> Literal:
        """
        Return the negation of this literal.

        Uses the ``~`` operator so that ``~Val(0, 0, 1)`` produces
        ``¬Val(0,0,1)`` and ``~~lit`` restores the original.

        Returns
        -------
        Literal
            A new ``Literal`` with the ``negated`` flag flipped.
        """
        return Literal(
            name=self.name,
            args=self.args,
            negated=not self.negated,
        )

    def __repr__(self) -> str:
        """
        Return a human-readable string representation.

        Returns
        -------
        str
            e.g. ``"Val(0,0,1)"`` or ``"¬Val(0,0,1)"``.
        """
        prefix = "¬" if self.negated else ""
        args_str = ",".join(str(a) for a in self.args)
        return f"{prefix}{self.name}({args_str})"


# Type alias: a CNF clause is a disjunction of literals.
Clause = list[Literal]


# ------------------------------------------------------------------
# Factory functions — thin wrappers for readability
# ------------------------------------------------------------------


def Val(i, j, v) -> Literal:
    """
    Create a ``Val(i, j, v)`` literal — cell (i,j) holds value v.

    Parameters
    ----------
    i : int or str
        Row index (0-based integer or variable string).
    j : int or str
        Column index (0-based integer or variable string).
    v : int or str
        Cell value (1-based integer or variable string).

    Returns
    -------
    Literal
        ``Literal("Val", (i, j, v))``.
    """
    return Literal("Val", (i, j, v))


def Given(i: int, j: int, v: int) -> Literal:
    """
    Create a ``Given(i, j, v)`` literal — cell (i,j) is a clue.

    Parameters
    ----------
    i : int
        Row index (0-based).
    j : int
        Column index (0-based).
    v : int
        Pre-filled clue value (1-based).

    Returns
    -------
    Literal
        ``Literal("Given", (i, j, v))``.
    """
    return Literal("Given", (i, j, v))


def LessH(i: int, j: int) -> Literal:
    """
    Create a ``LessH(i, j)`` literal — horizontal ``<`` constraint.

    Indicates that cell(i,j) < cell(i,j+1).

    Parameters
    ----------
    i : int
        Row index (0-based).
    j : int
        Column index of the left cell (0-based).

    Returns
    -------
    Literal
        ``Literal("LessH", (i, j))``.
    """
    return Literal("LessH", (i, j))


def GreaterH(i: int, j: int) -> Literal:
    """
    Create a ``GreaterH(i, j)`` literal — horizontal ``>`` constraint.

    Indicates that cell(i,j) > cell(i,j+1).

    Parameters
    ----------
    i : int
        Row index (0-based).
    j : int
        Column index of the left cell (0-based).

    Returns
    -------
    Literal
        ``Literal("GreaterH", (i, j))``.
    """
    return Literal("GreaterH", (i, j))


def LessV(i: int, j: int) -> Literal:
    """
    Create a ``LessV(i, j)`` literal — vertical ``<`` constraint.

    Indicates that cell(i,j) < cell(i+1,j).

    Parameters
    ----------
    i : int
        Row index of the top cell (0-based).
    j : int
        Column index (0-based).

    Returns
    -------
    Literal
        ``Literal("LessV", (i, j))``.
    """
    return Literal("LessV", (i, j))


def GreaterV(i: int, j: int) -> Literal:
    """
    Create a ``GreaterV(i, j)`` literal — vertical ``>`` constraint.

    Indicates that cell(i,j) > cell(i+1,j).

    Parameters
    ----------
    i : int
        Row index of the top cell (0-based).
    j : int
        Column index (0-based).

    Returns
    -------
    Literal
        ``Literal("GreaterV", (i, j))``.
    """
    return Literal("GreaterV", (i, j))


def Less(v1, v2) -> Literal:
    """
    Create a ``Less(v1, v2)`` literal — numerical relation v1 < v2.

    Parameters
    ----------
    v1 : int or str
        First value (1-based integer or variable string).
    v2 : int or str
        Second value (1-based integer or variable string).

    Returns
    -------
    Literal
        ``Literal("Less", (v1, v2))``.
    """
    return Literal("Less", (v1, v2))


def Diff(a, b) -> Literal:
    """
    Create a ``Diff(a, b)`` literal — inequality relation a != b.

    Used in Prolog-style rules to express that two values are different.
    
    Parameters
    ----------
    a : int or str
        First value (integer or variable string).
    b : int or str
        Second value (integer or variable string).

    Returns
    -------
    Literal
        ``Literal("Diff", (a, b))``.
    """
    return Literal("Diff", (a, b))


def Domain(v) -> Literal:
    """
    Create a ``Domain(v)`` literal — v is a valid domain value.

    Parameters
    ----------
    v : int or str
        A value in the domain (1..N integer or variable string).

    Returns
    -------
    Literal
        ``Literal("Domain", (v,))``.
    """
    return Literal("Domain", (v,))


def ValidVal(i, j, v) -> Literal:
    """
    Create a ``ValidVal(i, j, v)`` literal — value v is valid for cell (i,j).

    This is a positive predicate used in Definite Clauses to derive
    that a value satisfies all constraints for a given cell.

    Parameters
    ----------
    i : int or str
        Row index (0-based integer or variable string).
    j : int or str
        Column index (0-based integer or variable string).
    v : int or str
        Cell value (1-based integer or variable string).

    Returns
    -------
    Literal
        ``Literal("ValidVal", (i, j, v))``.
    """
    return Literal("ValidVal", (i, j, v))
