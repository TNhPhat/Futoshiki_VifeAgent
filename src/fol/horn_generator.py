"""
Horn Clause Generator for Futoshiki puzzles (Generate-and-Test paradigm).

Default mode (base backward chaining):
    - Global Domain(v) facts for v in 1..N
    - Solution rule body uses Domain(var)

Optional AC3-pruned mode:
    - Per-cell Domain_r_c(v) facts
    - Solution rule body uses Domain_r_c(var)
"""
from typing import Dict, List, Tuple, Deque
from futoshiki_vifeagent.core import Puzzle

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
    def exclusion_domains(
        puzzle: Puzzle,
        empty_cells: list[tuple[int, int]] | None = None,
    ) -> dict[tuple[int, int], set[int]] | None:
        n = puzzle.N
        if empty_cells is None:
            empty_cells = list(puzzle.get_empty_cells())
        if not empty_cells:
            return {}

        full_domain = set(range(1, n + 1))
        row_used = [set() for _ in range(n)]
        col_used = [set() for _ in range(n)]
        for r, c, value in puzzle.get_given_cells():
            row_used[r].add(value)
            col_used[c].add(value)

        domains: dict[tuple[int, int], set[int]] = {}
        for r, c in empty_cells:
            domain = full_domain - row_used[r] - col_used[c]
            if not domain:
                return None
            domains[(r, c)] = domain

        for constraint in puzzle.h_constraints + puzzle.v_constraints:
            a = constraint.cell1
            b = constraint.cell2
            a_is_empty = a in domains
            b_is_empty = b in domains

            if a_is_empty and not b_is_empty:
                other_value = int(puzzle.grid[b[0], b[1]])
                if constraint.direction == "<":
                    domains[a] = {v for v in domains[a] if v < other_value}
                else:
                    domains[a] = {v for v in domains[a] if v > other_value}
                if not domains[a]:
                    return None
            elif b_is_empty and not a_is_empty:
                other_value = int(puzzle.grid[a[0], a[1]])
                if constraint.direction == "<":
                    domains[b] = {v for v in domains[b] if v > other_value}
                else:
                    domains[b] = {v for v in domains[b] if v < other_value}
                if not domains[b]:
                    return None
            elif not a_is_empty and not b_is_empty:
                a_val = int(puzzle.grid[a[0], a[1]])
                b_val = int(puzzle.grid[b[0], b[1]])
                if constraint.direction == "<" and not (a_val < b_val):
                    return None
                if constraint.direction == ">" and not (a_val > b_val):
                    return None

        return domains

    @staticmethod
    def relative_size_domains(
        puzzle: Puzzle,
        empty_cells: list[tuple[int, int]] | None = None,
    ) -> dict[tuple[int, int], set[int]] | None:
        if empty_cells is None:
            empty_cells = list(puzzle.get_empty_cells())
        if not empty_cells:
            return {}

        domains = HornClauseGenerator.exclusion_domains(puzzle, empty_cells=empty_cells)
        if domains is None:
            return None

        return HornClauseGenerator._propagate_relative_size(puzzle, domains)

    @staticmethod
    def hidden_single_domains(
        puzzle: Puzzle,
        empty_cells: list[tuple[int, int]] | None = None,
    ) -> dict[tuple[int, int], set[int]] | None:
        n = puzzle.N
        if empty_cells is None:
            empty_cells = list(puzzle.get_empty_cells())
        if not empty_cells:
            return {}

        domains = HornClauseGenerator.relative_size_domains(puzzle, empty_cells=empty_cells)
        if domains is None:
            return None

        changed = True
        while changed:
            changed = False

            for row in range(n):
                row_cells = [(r, c) for r, c in empty_cells if r == row and (r, c) in domains]
                for value in range(1, n + 1):
                    carriers = [cell for cell in row_cells if value in domains[cell]]
                    if len(carriers) == 1 and domains[carriers[0]] != {value}:
                        domains[carriers[0]] = {value}
                        changed = True

            for col in range(n):
                col_cells = [(r, c) for r, c in empty_cells if c == col and (r, c) in domains]
                for value in range(1, n + 1):
                    carriers = [cell for cell in col_cells if value in domains[cell]]
                    if len(carriers) == 1 and domains[carriers[0]] != {value}:
                        domains[carriers[0]] = {value}
                        changed = True

            propagated = HornClauseGenerator._propagate_relative_size(puzzle, domains)
            if propagated is None:
                return None
            if propagated != domains:
                domains = propagated
                changed = True

        return domains

    @staticmethod
    def _propagate_relative_size(
        puzzle: Puzzle,
        domains: dict[tuple[int, int], set[int]],
    ) -> dict[tuple[int, int], set[int]] | None:
        domains = {cell: set(values) for cell, values in domains.items()}
        changed = True
        while changed:
            changed = False
            if HornClauseGenerator._propagate_singleton_exclusions(puzzle, domains):
                changed = True
                if any(not values for values in domains.values()):
                    return None

            for constraint in puzzle.h_constraints + puzzle.v_constraints:
                a = constraint.cell1
                b = constraint.cell2
                a_is_empty = a in domains
                b_is_empty = b in domains

                if not (a_is_empty and b_is_empty):
                    continue

                if constraint.direction == "<":
                    smaller_cell = a
                    larger_cell = b
                else:
                    smaller_cell = b
                    larger_cell = a

                smaller_domain = domains[smaller_cell]
                larger_domain = domains[larger_cell]

                if not smaller_domain or not larger_domain:
                    return None

                max_larger = max(larger_domain)
                min_smaller = min(smaller_domain)

                pruned_smaller = {value for value in smaller_domain if value < max_larger}
                pruned_larger = {value for value in larger_domain if value > min_smaller}

                if not pruned_smaller or not pruned_larger:
                    return None

                if pruned_smaller != smaller_domain:
                    domains[smaller_cell] = pruned_smaller
                    changed = True
                if pruned_larger != larger_domain:
                    domains[larger_cell] = pruned_larger
                    changed = True

        return domains

    @staticmethod
    def _propagate_singleton_exclusions(
        puzzle: Puzzle,
        domains: dict[tuple[int, int], set[int]],
    ) -> bool:
        changed = False
        singleton_values = {
            cell: next(iter(values))
            for cell, values in domains.items()
            if len(values) == 1
        }

        for (r, c), value in singleton_values.items():
            for other_cell, other_domain in domains.items():
                if other_cell == (r, c):
                    continue
                if value not in other_domain:
                    continue
                if other_cell[0] == r or other_cell[1] == c:
                    other_domain.remove(value)
                    changed = True

        return changed

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

        ordered_empty_cells = list(empty_cells)
        # ac3_domains = HornClauseGenerator._ac3_domains(puzzle, ordered_empty_cells)
        # if use_cell_domains:
        #     ordered_empty_cells.sort(
        #         key=lambda cell: (
        #             len(ac3_domains[(cell[0], cell[1])]),
        #             -HornClauseGenerator.get_cell_score(puzzle, n, cell[0], cell[1]),
        #         )
        #     )
        # else:
        #     ordered_empty_cells.sort(
        #         key=lambda cell: -HornClauseGenerator.get_cell_score(
        #             puzzle, n, cell[0], cell[1]
        #         )
        #     )

        body: List[Literal] = []
        generated_cells: set[Tuple[int, int]] = set()

        for idx, (r, c) in enumerate(ordered_empty_cells):
            var = cell_to_var[(r, c)]

            # Generate first: this variable must be bound before any test
            # literal that references it is added.
            if use_cell_domains:
                body.append(Literal(HornClauseGenerator._domain_predicate_name(r, c), (var,)))
            else:
                body.append(Domain(var))
            generated_cells.add((r, c))

            # Tests against fixed values (no second variable involved).
            for c_other in range(n):
                if c_other != c and puzzle.grid[r, c_other] != 0:
                    body.append(Diff(var, int(puzzle.grid[r, c_other])))

            for r_other in range(n):
                if r_other != r and puzzle.grid[r_other, c] != 0:
                    body.append(Diff(var, int(puzzle.grid[r_other, c])))

            # Add variable-variable tests only when both variables were generated.
            for pr, pc in ordered_empty_cells[:idx]:
                if r == pr or c == pc:
                    prev_var = cell_to_var[(pr, pc)]
                    body.append(Diff(var, prev_var))

            for (other_cell, is_less) in ineq_constraints[(r, c)]:
                or_r, or_c = other_cell
                if puzzle.grid[or_r, or_c] != 0:
                    other_val = int(puzzle.grid[or_r, or_c])
                    body.append(Less(var, other_val) if is_less else Less(other_val, var))
                elif other_cell in generated_cells:
                    other_var = cell_to_var[other_cell]
                    body.append(Less(var, other_var) if is_less else Less(other_var, var))

        return HornClause(Solution(*var_names), body)

    @staticmethod
    def get_cell_score(puzzle,n,r, c):
        score = 0
        for i in range(n):
            if puzzle.grid[r, i] != 0: score += 1
            if puzzle.grid[i, c] != 0: score += 1
        for constraint in puzzle.h_constraints + puzzle.v_constraints:
            if (r, c) == constraint.cell1 or (r, c) == constraint.cell2:
                score += 2
        return score
    
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

    @staticmethod
    def _ac3_domains(
        puzzle: Puzzle,
        empty_cells: list[tuple[int, int]] | None = None,
    ) -> dict[tuple[int, int], set[int]] | None:
        """
        Compute arc-consistent domains for empty cells.

        Delegates to :class:`constraints.ac3.AC3Propagator` for the
        actual AC-3 propagation.

        Parameters
        ----------
        puzzle : Puzzle
            The puzzle definition.
        empty_cells : list or None
            Specific empty cells to consider.  Defaults to all empty
            cells in the puzzle.

        Returns
        -------
        dict or None
            Per-cell domains after AC-3 pruning, or ``None`` on
            contradiction.
        """
        from constraints.ac3 import AC3Propagator

        n = puzzle.N
        if empty_cells is None:
            empty_cells = list(puzzle.get_empty_cells())
        if not empty_cells:
            return {}

        # Build initial domains from row/col elimination
        full_domain = set(range(1, n + 1))
        row_used: list[set[int]] = [set() for _ in range(n)]
        col_used: list[set[int]] = [set() for _ in range(n)]
        for r, c, value in puzzle.get_given_cells():
            row_used[r].add(value)
            col_used[c].add(value)

        domains: dict[tuple[int, int], set[int]] | None = {}
        for r, c in empty_cells:
            domain = full_domain - row_used[r] - col_used[c]
            if not domain:
                return None
            domains[(r, c)] = domain

        domains = HornClauseGenerator.hidden_single_domains(puzzle, empty_cells=empty_cells)
        return AC3Propagator.propagate(domains, puzzle)
