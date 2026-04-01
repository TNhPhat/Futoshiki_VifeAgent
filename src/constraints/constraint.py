from abc import ABC, abstractmethod

class BaseConstraint(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def is_satisfied(self, puzzle) -> bool:
        """
        Check if the current state of the puzzle satisfies the constraint.
        Return:
         True if valid, False if violated.
        """
        pass

    @abstractmethod
    def get_affected_cells(self, puzzle) -> list[tuple[int,...]]:
        """
        Returns a list of cells affected by this constraint
        (helps optimize the Search algorithm).
        """
        pass