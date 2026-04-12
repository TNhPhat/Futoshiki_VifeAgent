"""
A* search engine for Futoshiki puzzles.

Implements best-first graph search with:
- Priority queue (open set) ordered by f(n) = g(n) + h(n)
- Closed set via grid-hash for cycle detection
- MRV (Minimum Remaining Values) cell selection
- Basic domain propagation (eliminate + auto-fill singletons loop)
- Pluggable heuristic via BaseHeuristic interface
"""

from __future__ import annotations

import heapq
from typing import Optional

import numpy as np

from core.puzzle import Puzzle
from heuristics.base_heuristic import BaseHeuristic
from search.state import SearchState


class AStarEngine:
    """
    Core A* search algorithm for Futoshiki.

    Parameters
    ----------
    heuristic : BaseHeuristic
        The heuristic function to estimate remaining cost.
    """

    def __init__(self, heuristic: BaseHeuristic) -> None:
        self._heuristic = heuristic
        self.node_expansions: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def solve(self, puzzle: Puzzle) -> Optional[SearchState]:
        """
        Run A* search on the given puzzle.

        Parameters
        ----------
        puzzle : Puzzle
            The Futoshiki puzzle to solve.

        Returns
        -------
        SearchState or None
            The goal state if a solution is found; ``None`` otherwise.
        """
        self.node_expansions = 0

        initial = self._build_initial_state(puzzle)
        if initial is None:
            return None  # contradiction during initialisation

        open_set: list[tuple[int, int, SearchState]] = []
        # Tie-breaking counter to ensure stable ordering in heapq
        counter = 0
        heapq.heappush(open_set, (initial.f, counter, initial))

        closed: set[int] = set()

        while open_set:
            _, _, current = heapq.heappop(open_set)

            # Skip already-explored states
            state_hash = hash(current.grid.tobytes())
            if state_hash in closed:
                continue
            closed.add(state_hash)

            self.node_expansions += 1

            # Goal check: complete grid with zero violations
            if current.is_complete and current.g == 0:
                return current

            # If complete but has violations, skip (dead end)
            if current.is_complete:
                continue

            # Select the MRV cell (smallest domain)
            cell = self._select_mrv_cell(current)
            if cell is None:
                continue  # no unassigned cells but not complete (shouldn't happen)

            i, j = cell
            domain = current.domains.get((i, j), set())

            for value in sorted(domain):
                child = self._create_child(
                    current, i, j, value, puzzle,
                )
                if child is not None:
                    child_hash = hash(child.grid.tobytes())
                    if child_hash not in closed:
                        counter += 1
                        heapq.heappush(
                            open_set, (child.f, counter, child),
                        )

        return None  # exhausted search space — no solution

    # ------------------------------------------------------------------
    # Initial state construction
    # ------------------------------------------------------------------

    def _build_initial_state(self, puzzle: Puzzle) -> Optional[SearchState]:
        """
        Create the initial SearchState from the puzzle.

        Initialises domains for every empty cell by eliminating values
        that appear in the same row, column, or violate inequality
        constraints.  Then runs singleton auto-fill until stable.

        Returns None if a contradiction is detected (empty domain).
        """
        N = puzzle.N
        grid = puzzle.grid.copy()
        domains: dict[tuple[int, int], set[int]] = {}

        # Initialise raw domains for empty cells
        for i in range(N):
            for j in range(N):
                if grid[i, j] == 0:
                    domains[(i, j)] = set(range(1, N + 1))

        # Eliminate values based on assigned cells
        for i in range(N):
            for j in range(N):
                v = int(grid[i, j])
                if v != 0:
                    self._eliminate_from_peers(
                        domains, grid, N, i, j, v, puzzle,
                    )

        # Iterative singleton propagation
        if not self._propagate_singletons(domains, grid, N, puzzle):
            return None  # contradiction

        g = self._compute_violations(grid, N, puzzle)
        state = SearchState(grid=grid, domains=domains, g=g, h=0)
        state.h = self._heuristic.estimate(state, puzzle)
        return state

    # ------------------------------------------------------------------
    # Child state creation
    # ------------------------------------------------------------------

    def _create_child(
        self,
        parent: SearchState,
        i: int,
        j: int,
        value: int,
        puzzle: Puzzle,
    ) -> Optional[SearchState]:
        """
        Create a child state by assigning ``value`` to cell ``(i, j)``.

        Returns None if the assignment causes a contradiction
        (any domain becomes empty).
        """
        child = parent.copy()
        N = puzzle.N

        child.grid[i, j] = value
        # Remove this cell from domains (it's now assigned)
        child.domains.pop((i, j), None)

        # Eliminate value from peers
        self._eliminate_from_peers(
            child.domains, child.grid, N, i, j, value, puzzle,
        )

        # Check for empty domains
        for cell, dom in child.domains.items():
            if len(dom) == 0:
                return None  # contradiction

        # Propagate singletons
        if not self._propagate_singletons(
            child.domains, child.grid, N, puzzle,
        ):
            return None  # contradiction

        child.g = self._compute_violations(child.grid, N, puzzle)
        child.h = self._heuristic.estimate(child, puzzle)
        return child

    # ------------------------------------------------------------------
    # MRV cell selection
    # ------------------------------------------------------------------

    @staticmethod
    def _select_mrv_cell(
        state: SearchState,
    ) -> Optional[tuple[int, int]]:
        """
        Select the unassigned cell with the smallest domain (MRV).

        Returns
        -------
        tuple[int, int] or None
            The (row, col) of the most constrained cell, or None if
            no unassigned cells remain.
        """
        best_cell: Optional[tuple[int, int]] = None
        best_size = float("inf")

        for (i, j), domain in state.domains.items():
            if state.grid[i, j] == 0 and len(domain) < best_size:
                best_size = len(domain)
                best_cell = (i, j)

        return best_cell

    # ------------------------------------------------------------------
    # Domain propagation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _eliminate_from_peers(
        domains: dict[tuple[int, int], set[int]],
        grid: np.ndarray,
        N: int,
        row: int,
        col: int,
        value: int,
        puzzle: Puzzle,
    ) -> None:
        """
        Remove ``value`` from the domains of all cells in the same
        row and column.  Also tighten domains for inequality-linked
        cells.
        """
        # Row peers
        for c in range(N):
            if c != col and (row, c) in domains:
                domains[(row, c)].discard(value)

        # Column peers
        for r in range(N):
            if r != row and (r, col) in domains:
                domains[(r, col)].discard(value)

        # Inequality constraint peers
        for constraint in puzzle.h_constraints + puzzle.v_constraints:
            r1, c1 = constraint.cell1
            r2, c2 = constraint.cell2

            if (r1, c1) == (row, col) and (r2, c2) in domains:
                # cell1 is assigned; tighten cell2's domain
                if constraint.direction == "<":
                    # cell1 < cell2: cell2 must be > value
                    domains[(r2, c2)] = {
                        v for v in domains[(r2, c2)] if v > value
                    }
                elif constraint.direction == ">":
                    # cell1 > cell2: cell2 must be < value
                    domains[(r2, c2)] = {
                        v for v in domains[(r2, c2)] if v < value
                    }

            elif (r2, c2) == (row, col) and (r1, c1) in domains:
                # cell2 is assigned; tighten cell1's domain
                if constraint.direction == "<":
                    # cell1 < cell2: cell1 must be < value
                    domains[(r1, c1)] = {
                        v for v in domains[(r1, c1)] if v < value
                    }
                elif constraint.direction == ">":
                    # cell1 > cell2: cell1 must be > value
                    domains[(r1, c1)] = {
                        v for v in domains[(r1, c1)] if v > value
                    }

    @staticmethod
    def _propagate_singletons(
        domains: dict[tuple[int, int], set[int]],
        grid: np.ndarray,
        N: int,
        puzzle: Puzzle,
    ) -> bool:
        """
        Repeatedly auto-fill cells whose domain has exactly one value.

        Returns True if propagation succeeds, False if a contradiction
        is detected (any domain becomes empty after propagation).
        """
        changed = True
        while changed:
            changed = False
            # Work on a snapshot of keys since we modify the dict
            singleton_cells = [
                (cell, next(iter(dom)))
                for cell, dom in list(domains.items())
                if len(dom) == 1 and grid[cell[0], cell[1]] == 0
            ]
            for (i, j), value in singleton_cells:
                grid[i, j] = value
                domains.pop((i, j), None)
                changed = True

                # Eliminate from peers
                AStarEngine._eliminate_from_peers(
                    domains, grid, N, i, j, value, puzzle,
                )

                # Check for empty domains
                for dom in domains.values():
                    if len(dom) == 0:
                        return False

        return True

    # ------------------------------------------------------------------
    # Violation counting
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_violations(
        grid: np.ndarray, N: int, puzzle: Puzzle,
    ) -> int:
        """
        Count constraint violations in the current (partial) assignment.

        Counts:
        - Row uniqueness duplicates among assigned cells.
        - Column uniqueness duplicates among assigned cells.
        - Inequality constraints violated by assigned cell pairs.
        """
        violations = 0

        # Row uniqueness
        for i in range(N):
            assigned = [
                int(grid[i, j]) for j in range(N) if grid[i, j] != 0
            ]
            violations += len(assigned) - len(set(assigned))

        # Column uniqueness
        for j in range(N):
            assigned = [
                int(grid[i, j]) for i in range(N) if grid[i, j] != 0
            ]
            violations += len(assigned) - len(set(assigned))

        # Inequality constraints
        for c in puzzle.h_constraints + puzzle.v_constraints:
            r1, c1 = c.cell1
            r2, c2 = c.cell2
            v1, v2 = int(grid[r1, c1]), int(grid[r2, c2])
            if v1 != 0 and v2 != 0:
                if c.direction == "<" and not (v1 < v2):
                    violations += 1
                elif c.direction == ">" and not (v1 > v2):
                    violations += 1

        return violations
