"""
Heuristic h4: AC-3 Enhanced Domain Sum.

Runs AC-3 arc-consistency propagation on a **copy** of the current
state's domains, then returns the h2 formula (Sigma (|domain'| - 1)) on
the pruned domains.

If AC-3 detects a contradiction (any domain collapses to empty),
returns a large penalty value indicating the state is unreachable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from constraints.ac3 import AC3Propagator
from .base_heuristic import BaseHeuristic

if TYPE_CHECKING:
    from search.state import SearchState
    from core.puzzle import Puzzle


class AC3Heuristic(BaseHeuristic):
    """
    h4(n) = Sigma (|domain'(i,j)| - 1) for all unassigned cells,
    where domain' = domains after AC-3 propagation.

    If any domain becomes empty after AC-3 -> returns N x N x N
    (large penalty signalling a dead-end state).

    Complexity: O(e x d3) per call, where e = arcs, d = max domain.
    """

    def estimate(self, state: SearchState, puzzle: Puzzle) -> int:
        """
        Run AC-3 on a copy of the state's domains, then compute h2.

        Parameters
        ----------
        state : SearchState
            Current search state with domain map.
        puzzle : Puzzle
            Original puzzle definition.

        Returns
        -------
        int
            h2 on pruned domains, or N3 on contradiction.
        """
        N = puzzle.N

        # Work on a copy so the original state is not mutated
        domains_copy: dict[tuple[int, int], set[int]] = {
            k: set(v) for k, v in state.domains.items()
            if state.grid[k[0], k[1]] == 0
        }

        result = AC3Propagator.propagate(domains_copy, puzzle)
        if result is None:
            return N * N * N  # contradiction -> large penalty

        # h2 formula on pruned domains
        total = 0
        for (i, j), dom in result.items():
            if state.grid[i, j] == 0:
                total += max(0, len(dom) - 1)
        return total

    def get_name(self) -> str:
        return "h4: AC-3 Pruned Domain Sum"
