from __future__ import annotations

from collections import deque

from core.puzzle import Puzzle
from fol import HornClauseGenerator
from inference import BackwardChainingEngine
from utils import Stats

from .backward_chaining_solver import BackwardChaining


class AC3BackwardChaining(BackwardChaining):
    """
    Backward chaining solver variant with AC-3 domain pruning.
    """

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        self._start_trace()

        empty_cells = list(puzzle.get_empty_cells())
        if not empty_cells:
            self._end_trace()
            return puzzle.copy(), self._stats

        domains = self._ac3_domains(puzzle, empty_cells=empty_cells)
        if domains is None:
            self._end_trace()
            return None, self._stats

        kb = HornClauseGenerator.generate(
            puzzle,
            domains=domains,
            use_cell_domains=True,
        )
        goal = self._generate_goal(puzzle)
        var_names = [f"v_{r}_{c}" for r, c in empty_cells]

        engine = BackwardChainingEngine(kb=kb)
        substitution = engine.prove_all([goal])

        self._end_trace()
        self._stats.inference_count = engine.inference_count

        if substitution is None:
            return None, self._stats

        solution = puzzle.copy()
        for idx, (r, c) in enumerate(empty_cells):
            value = self._resolve_value(var_names[idx], substitution)
            if value is not None and isinstance(value, int):
                solution.grid[r, c] = value
        return solution, self._stats

    def _ac3_domains(
        self,
        puzzle: Puzzle,
        empty_cells: list[tuple[int, int]] | None = None,
    ) -> dict[tuple[int, int], set[int]] | None:
        n = puzzle.N
        if empty_cells is None:
            empty_cells = list(puzzle.get_empty_cells())
        if not empty_cells:
            return {}

        empty_set = set(empty_cells)

        domains: dict[tuple[int, int], set[int]] = {}
        full_domain = set(range(1, n + 1))
        row_used = [set() for _ in range(n)]
        col_used = [set() for _ in range(n)]
        for r, c, value in puzzle.get_given_cells():
            row_used[r].add(value)
            col_used[c].add(value)

        for r, c in empty_cells:
            domain = full_domain - row_used[r] - col_used[c]
            if not domain:
                return None
            domains[(r, c)] = domain

        REL_NEQ = 1
        REL_LT = 2
        REL_GT = 4

        constraints: dict[tuple[tuple[int, int], tuple[int, int]], int] = {}
        neighbors: dict[tuple[int, int], set[tuple[int, int]]] = {cell: set() for cell in empty_cells}

        def add_constraint(a: tuple[int, int], b: tuple[int, int], relation_mask: int) -> None:
            key = (a, b)
            constraints[key] = constraints.get(key, 0) | relation_mask
            neighbors[a].add(b)

        row_to_empty: dict[int, list[tuple[int, int]]] = {}
        col_to_empty: dict[int, list[tuple[int, int]]] = {}
        for r, c in empty_cells:
            row_to_empty.setdefault(r, []).append((r, c))
            col_to_empty.setdefault(c, []).append((r, c))

        for row_cells in row_to_empty.values():
            for i in range(len(row_cells)):
                for j in range(i + 1, len(row_cells)):
                    a = row_cells[i]
                    b = row_cells[j]
                    add_constraint(a, b, REL_NEQ)
                    add_constraint(b, a, REL_NEQ)

        for col_cells in col_to_empty.values():
            for i in range(len(col_cells)):
                for j in range(i + 1, len(col_cells)):
                    a = col_cells[i]
                    b = col_cells[j]
                    add_constraint(a, b, REL_NEQ)
                    add_constraint(b, a, REL_NEQ)

        for inequality in puzzle.h_constraints + puzzle.v_constraints:
            a = inequality.cell1
            b = inequality.cell2
            a_is_empty = a in empty_set
            b_is_empty = b in empty_set

            if a_is_empty and b_is_empty:
                if inequality.direction == "<":
                    add_constraint(a, b, REL_LT)
                    add_constraint(b, a, REL_GT)
                else:
                    add_constraint(a, b, REL_GT)
                    add_constraint(b, a, REL_LT)
            elif a_is_empty:
                other_value = int(puzzle.grid[b[0], b[1]])
                if inequality.direction == "<":
                    domains[a] = {v for v in domains[a] if v < other_value}
                else:
                    domains[a] = {v for v in domains[a] if v > other_value}
                if not domains[a]:
                    return None
            elif b_is_empty:
                other_value = int(puzzle.grid[a[0], a[1]])
                if inequality.direction == "<":
                    domains[b] = {v for v in domains[b] if v > other_value}
                else:
                    domains[b] = {v for v in domains[b] if v < other_value}
                if not domains[b]:
                    return None
            else:
                a_val = int(puzzle.grid[a[0], a[1]])
                b_val = int(puzzle.grid[b[0], b[1]])
                if inequality.direction == "<" and not (a_val < b_val):
                    return None
                if inequality.direction == ">" and not (a_val > b_val):
                    return None

        queue: deque[tuple[tuple[int, int], tuple[int, int]]] = deque(constraints.keys())
        while queue:
            xi, xj = queue.popleft()
            relation_mask = constraints[(xi, xj)]
            if self._revise(domains, xi, xj, relation_mask):
                if not domains[xi]:
                    return None
                for xk in neighbors[xi]:
                    if xk != xj:
                        queue.append((xk, xi))

        return domains

    @staticmethod
    def _satisfies_relations(a: int, b: int, relation_mask: int) -> bool:
        if relation_mask & 1 and a == b:
            return False
        if relation_mask & 2 and not (a < b):
            return False
        if relation_mask & 4 and not (a > b):
            return False
        return True

    def _revise(
        self,
        domains: dict[tuple[int, int], set[int]],
        xi: tuple[int, int],
        xj: tuple[int, int],
        relation_mask: int,
    ) -> bool:
        domain_i = domains[xi]
        domain_j = domains[xj]
        revised = False

        if relation_mask == 1 and len(domain_j) == 1:
            blocked_value = next(iter(domain_j))
            if blocked_value in domain_i:
                domain_i.remove(blocked_value)
                return True
            return False

        for value_i in tuple(domain_i):
            if not any(self._satisfies_relations(value_i, value_j, relation_mask) for value_j in domain_j):
                domain_i.remove(value_i)
                revised = True

        return revised

    def get_name(self) -> str:
        return "Backward Chaining + AC3 Pruning"
