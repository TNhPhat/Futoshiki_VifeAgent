"""
Abstract base class for A* search heuristics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from search.state import SearchState
    from core.puzzle import Puzzle


class BaseHeuristic(ABC):
    """
    Interface that every A* heuristic must implement.

    A heuristic estimates the remaining cost ``h(n)`` from a given
    ``SearchState`` to a goal state (complete grid with zero violations).
    To guarantee A* optimality the estimate must be *admissible*
    (never overestimates the true remaining cost).
    """

    @abstractmethod
    def estimate(self, state: SearchState, puzzle: Puzzle) -> int:
        """
        Return h(n) — an admissible heuristic estimate.

        Parameters
        ----------
        state : SearchState
            The current partial assignment with its domain map.
        puzzle : Puzzle
            The original puzzle definition (constraints, N, etc.).

        Returns
        -------
        int
            A non-negative admissible estimate of remaining cost.
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """
        Return a short human-readable name for this heuristic.

        Returns
        -------
        str
            e.g. ``"h1: Empty Cells"``, ``"h2: Domain Sum"``.
        """
        ...
