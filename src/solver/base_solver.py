from core import Puzzle
from abc import ABC, abstractmethod

class BaseSolver(ABC):
    def __init__(self) -> None:
        pass
    
    @abstractmethod
    def solve (self,puzzle: Puzzle) -> Puzzle:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass



    