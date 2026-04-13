from __future__ import annotations

from abc import ABC, abstractmethod

from futoshiki_vifeagent.core import Puzzle
from futoshiki_vifeagent.utils import Stats


class BaseSolver(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def solve(self, puzzle: Puzzle, on_step=None) -> tuple[Puzzle | None, Stats]:
        """Solve the puzzle and return (solution, stats), or (None, stats) if unsolvable.

        Parameters
        ----------
        on_step : callable(grid: np.ndarray, is_backtrack: bool) | None
            Optional callback invoked after each meaningful state change.
            Solvers that support step-by-step visualisation call this;
            others may ignore it.
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return a short human-readable name for this solver."""
        pass



    
