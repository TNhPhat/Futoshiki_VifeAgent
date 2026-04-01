from .constraint import BaseConstraint
class InequalityConstraint(BaseConstraint):
    def __init__(self, cell1, cell2, direction):
        self.cell1 = cell1  
        self.cell2 = cell2
        self.direction = direction  

    def is_satisfied(self, puzzle):
        r1, c1 = self.cell1
        r2, c2 = self.cell2

        v1 = puzzle.grid[r1][c1]
        v2 = puzzle.grid[r2][c2]

        if v1 == 0 or v2 == 0:
            return True  

        if self.direction == '>':
            return v1 > v2
        else:
            return v1 < v2

    def get_affected_cells(self, puzzle):
        return [self.cell1, self.cell2]