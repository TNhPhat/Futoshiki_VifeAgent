from .constraint import BaseConstraint
class RowUniqueness(BaseConstraint):
    def __init__(self, row):
        self.row = row

    def is_satisfied(self, puzzle):
        values = [puzzle.grid[self.row][c] for c in range(puzzle.n)]
        values = [v for v in values if v != 0]
        return len(values) == len(set(values))

    def get_affected_cells(self, puzzle):
        return [(self.row,c) for c in range(puzzle.n)]