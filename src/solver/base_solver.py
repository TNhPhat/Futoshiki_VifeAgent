from __future__ import annotations

from abc import ABC, abstractmethod

from futoshiki_vifeagent.core import Puzzle
from futoshiki_vifeagent.utils import Stats


class BaseSolver(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        """Solve the puzzle and return (solution, stats), or (None, stats) if unsolvable."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return a short human-readable name for this solver."""
        pass



    
