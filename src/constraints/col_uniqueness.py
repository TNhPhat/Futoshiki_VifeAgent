from .constraint import BaseConstraint
class ColUniqueness(BaseConstraint):
    def __init__(self, col):
        self.col = col

    def is_satisfied(self, puzzle):
        values = [puzzle.grid[r][self.col] for r in range(puzzle.n)]
        values = [v for v in values if v != 0]
        return len(values) == len(set(values))

    def get_affected_cells(self, puzzle):
        return [(r, self.col) for r in range(puzzle.n)]