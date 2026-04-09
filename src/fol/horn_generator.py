"""
Horn Clause Generator for Futoshiki puzzles (Generate-and-Test paradigm).

Default mode (base backward chaining):
    - Global Domain(v) facts for v in 1..N
    - Solution rule body uses Domain(var)

Optional AC3-pruned mode:
    - Per-cell Domain_r_c(v) facts
    - Solution rule body uses Domain_r_c(var)
"""

from typing import Dict, List, Tuple

from core import Puzzle

from .horn_kb import HornClause, HornClauseKnowledgeBase
from .predicates import Diff, Domain, Less, Literal, Val


def Solution(*args) -> Literal:
    return Literal("Solution", args)


class HornClauseGenerator:
    @staticmethod
    def generate(
        puzzle: Puzzle,
        domains: Dict[Tuple[int, int], set[int]] | None = None,
        use_cell_domains: bool = False,
    ) -> HornClauseKnowledgeBase:
        kb = HornClauseKnowledgeBase()

        for fact in HornClauseGenerator._get_facts(
            puzzle,
            domains=domains,
            use_cell_domains=use_cell_domains,
        ):
            kb.add_fact(fact)

        solution_rule = HornClauseGenerator._get_solution_rule(
            puzzle,
            use_cell_domains=use_cell_domains,
        )
        if solution_rule is not None:
            kb.add_rule(solution_rule)

        return kb

    @staticmethod
    def _get_facts(
        puzzle: Puzzle,
        domains: Dict[Tuple[int, int], set[int]] | None = None,
        use_cell_domains: bool = False,
    ) -> List[Literal]:
        n = puzzle.N
        facts: List[Literal] = []

        for i in range(n):
            for j in range(n):
                if puzzle.grid[i, j] != 0:
                    facts.append(Val(i, j, int(puzzle.grid[i, j])))

        if use_cell_domains:
            full_domain = set(range(1, n + 1))
            for r, c in HornClauseGenerator.get_empty_cells(puzzle):
                predicate_name = HornClauseGenerator._domain_predicate_name(r, c)
                allowed_values = (
                    domains.get((r, c), full_domain) if domains is not None else full_domain
                )
                for value in sorted(allowed_values):
                    facts.append(Literal(predicate_name, (value,)))
        else:
            for v in range(1, n + 1):
                facts.append(Domain(v))

        for a in range(1, n + 1):
            for b in range(1, n + 1):
                if a != b:
                    facts.append(Diff(a, b))

        for a in range(1, n + 1):
            for b in range(a + 1, n + 1):
                facts.append(Less(a, b))

        return facts

    @staticmethod
    def _get_solution_rule(
        puzzle: Puzzle,
        use_cell_domains: bool = False,
    ) -> HornClause | None:
        n = puzzle.N

        empty_cells = HornClauseGenerator.get_empty_cells(puzzle)
        if not empty_cells:
            return None

        var_names: List[str] = []
        cell_to_var: Dict[Tuple[int, int], str] = {}
        for r, c in empty_cells:
            var_name = f"v_{r}_{c}"
            var_names.append(var_name)
            cell_to_var[(r, c)] = var_name

        ineq_constraints: Dict[Tuple[int, int], List[Tuple[Tuple[int, int], bool]]] = {
            (r, c): [] for r in range(n) for c in range(n)
        }
        for constraint in puzzle.h_constraints + puzzle.v_constraints:
            r1, c1 = constraint.cell1
            r2, c2 = constraint.cell2
            if constraint.direction == "<":
                ineq_constraints[(r1, c1)].append(((r2, c2), True))
                ineq_constraints[(r2, c2)].append(((r1, c1), False))
            else:
                ineq_constraints[(r1, c1)].append(((r2, c2), False))
                ineq_constraints[(r2, c2)].append(((r1, c1), True))

        body: List[Literal] = []
        processed_cells: set[Tuple[int, int]] = set()

        for idx, (r, c) in enumerate(empty_cells):
            var = var_names[idx]

            if use_cell_domains:
                body.append(Literal(HornClauseGenerator._domain_predicate_name(r, c), (var,)))
            else:
                body.append(Domain(var))

            for c_other in range(n):
                if c_other != c and puzzle.grid[r, c_other] != 0:
                    body.append(Diff(var, int(puzzle.grid[r, c_other])))

            for r_other in range(n):
                if r_other != r and puzzle.grid[r_other, c] != 0:
                    body.append(Diff(var, int(puzzle.grid[r_other, c])))

            for prev_idx, (pr, pc) in enumerate(empty_cells[:idx]):
                if r == pr or c == pc:
                    prev_var = var_names[prev_idx]
                    body.append(Diff(var, prev_var))

            for (other_cell, is_less) in ineq_constraints[(r, c)]:
                or_r, or_c = other_cell
                if puzzle.grid[or_r, or_c] != 0:
                    other_val = int(puzzle.grid[or_r, or_c])
                    body.append(Less(var, other_val) if is_less else Less(other_val, var))
                elif other_cell in processed_cells:
                    other_var = cell_to_var[other_cell]
                    body.append(Less(var, other_var) if is_less else Less(other_var, var))

            processed_cells.add((r, c))

        return HornClause(Solution(*var_names), body)

    @staticmethod
    def get_empty_cells(puzzle: Puzzle) -> List[Tuple[int, int]]:
        return list(puzzle.get_empty_cells())

    @staticmethod
    def get_solution_goal(puzzle: Puzzle) -> Literal:
        var_names = [f"v_{r}_{c}" for r, c in HornClauseGenerator.get_empty_cells(puzzle)]
        return Solution(*var_names)

    @staticmethod
    def _domain_predicate_name(r: int, c: int) -> str:
        return f"Domain_{r}_{c}"
