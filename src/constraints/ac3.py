"""
AC-3 (Arc Consistency Algorithm 3) propagator for Futoshiki puzzles.

Removes provably impossible values from cell domains by enforcing
arc consistency across row-uniqueness, column-uniqueness, and
inequality constraints.

A domain dict maps ``(row, col) -> {possible values}`` for each
unassigned cell.  Assigned cells are absent from this dict; their
fixed values are read directly from the puzzle grid.

Relation bitmask encoding
-------------------------
Each arc carries a bitmask that encodes one or more relations:

- ``REL_NEQ  = 1``  not-equal  (row / column uniqueness)
- ``REL_LT   = 2``  less-than  (``<`` inequality)
- ``REL_GT   = 4``  greater-than (``>`` inequality)

Bits can be OR-ed when two cells share multiple constraint types.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.puzzle import Puzzle

# Relation-mask bit constants
REL_NEQ: int = 1
REL_LT: int = 2
REL_GT: int = 4


class AC3Propagator:
    """
    Standalone AC-3 arc-consistency propagator.

    Works on a ``dict[tuple[int, int], set[int]]`` domain map that
    uses the same representation as ``AStarEngine`` / ``SearchState``.
    """

    @staticmethod
    def propagate(
        domains: dict[tuple[int, int], set[int]] | None,
        puzzle: Puzzle,
    ) -> dict[tuple[int, int], set[int]] | None:
        """
        Run AC-3 on *domains* (mutated in-place).

        Parameters
        ----------
        domains : dict[tuple[int, int], set[int]]
            Per-cell domain sets for **unassigned** cells.  Modified in
            place.
        puzzle : Puzzle
            The puzzle definition (grid, constraints, N).

        Returns
        -------
        dict[tuple[int, int], set[int]] or None
            The pruned *domains* dict on success, or ``None`` if a
            contradiction is detected (any domain becomes empty).
        """
        if not domains:
            return domains

        N = puzzle.N
        empty_set = set(domains.keys())

        constraints: dict[
            tuple[tuple[int, int], tuple[int, int]], int
        ] = {}
        neighbors: dict[
            tuple[int, int], set[tuple[int, int]]
        ] = {cell: set() for cell in domains}

        def _add(
            a: tuple[int, int],
            b: tuple[int, int],
            mask: int,
        ) -> None:
            key = (a, b)
            constraints[key] = constraints.get(key, 0) | mask
            neighbors[a].add(b)

        # Row uniqueness arcs
        row_groups: dict[int, list[tuple[int, int]]] = {}
        for r, c in domains:
            row_groups.setdefault(r, []).append((r, c))

        for cells in row_groups.values():
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    _add(cells[i], cells[j], REL_NEQ)
                    _add(cells[j], cells[i], REL_NEQ)

        # Column uniqueness arcs
        col_groups: dict[int, list[tuple[int, int]]] = {}
        for r, c in domains:
            col_groups.setdefault(c, []).append((r, c))

        for cells in col_groups.values():
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    _add(cells[i], cells[j], REL_NEQ)
                    _add(cells[j], cells[i], REL_NEQ)

        # Inequality arcs
        for ineq in puzzle.h_constraints + puzzle.v_constraints:
            a, b = ineq.cell1, ineq.cell2
            a_empty = a in empty_set
            b_empty = b in empty_set

            if a_empty and b_empty:
                if ineq.direction == "<":
                    _add(a, b, REL_LT)
                    _add(b, a, REL_GT)
                else:
                    _add(a, b, REL_GT)
                    _add(b, a, REL_LT)
            elif a_empty:
                # b is assigned -- tighten a against the fixed value
                bval = int(puzzle.grid[b[0], b[1]])
                if bval == 0:
                    # b is also unassigned but not in domains -> skip
                    continue
                if ineq.direction == "<":
                    domains[a] = {v for v in domains[a] if v < bval}
                else:
                    domains[a] = {v for v in domains[a] if v > bval}
                if not domains[a]:
                    return None
            elif b_empty:
                aval = int(puzzle.grid[a[0], a[1]])
                if aval == 0:
                    continue
                if ineq.direction == "<":
                    domains[b] = {v for v in domains[b] if v > aval}
                else:
                    domains[b] = {v for v in domains[b] if v < aval}
                if not domains[b]:
                    return None

        queue: deque[tuple[tuple[int, int], tuple[int, int]]] = deque(
            constraints.keys()
        )

        while queue:
            xi, xj = queue.popleft()
            mask = constraints[(xi, xj)]

            if AC3Propagator._revise(domains, xi, xj, mask):
                if not domains[xi]:
                    return None  # contradiction
                for xk in neighbors[xi]:
                    if xk != xj:
                        queue.append((xk, xi))

        return domains

    @staticmethod
    def _revise(
        domains: dict[tuple[int, int], set[int]],
        xi: tuple[int, int],
        xj: tuple[int, int],
        mask: int,
    ) -> bool:
        """
        Remove values from ``domains[xi]`` for which **no** value in
        ``domains[xj]`` satisfies the relation encoded by *mask*.

        Returns True if the domain was modified.
        """
        dom_i = domains[xi]
        dom_j = domains[xj]

        # Fast-path: pure NEQ with singleton neighbour
        if mask == REL_NEQ and len(dom_j) == 1:
            blocked = next(iter(dom_j))
            if blocked in dom_i:
                dom_i.remove(blocked)
                return True
            return False

        revised = False
        for vi in tuple(dom_i):
            if not any(
                AC3Propagator._satisfies(vi, vj, mask) for vj in dom_j
            ):
                dom_i.remove(vi)
                revised = True

        return revised

    @staticmethod
    def _satisfies(a: int, b: int, mask: int) -> bool:
        """
        Return True if the value pair ``(a, b)`` satisfies **all**
        relations encoded in *mask*.
        """
        if mask & REL_NEQ and a == b:
            return False
        if mask & REL_LT and not (a < b):
            return False
        if mask & REL_GT and not (a > b):
            return False
        return True
