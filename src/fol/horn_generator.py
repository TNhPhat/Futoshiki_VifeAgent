"""
Horn Clause Generator for Futoshiki Puzzles (Generate-and-Test Paradigm).

Generates a single global rule using the Generate-and-Test paradigm to prevent
infinite recursion in SLD resolution.

Generate-and-Test Approach:
    1. GENERATE phase: Domain(v_r_c) for each empty cell variable
       - This enumerates all possible value assignments via backtracking
    
    2. TEST phase: Diff and Less constraints
       - Row uniqueness: Diff(v_r_c1, v_r_c2) for cells in same row
       - Column uniqueness: Diff(v_r1_c, v_r2_c) for cells in same column  
       - Inequality: Less(v1, v2) for cells with < constraints

Example for 2x2 with given (0,0)=1 and constraint (0,0)<(0,1):
    
    Facts:
        Val(0,0,1)          # Given
        Domain(1), Domain(2) # Value domain
        Diff(1,2), Diff(2,1) # Difference facts
        Less(1,2)           # Less-than facts
    
    Rule:
        Solution(v_0_1, v_1_0, v_1_1) :-
            Domain(v_0_1), Domain(v_1_0), Domain(v_1_1),  # Generate
            Diff(v_0_1, 1), Diff(v_1_0, 1),               # Row/Col with given
            Diff(v_0_1, v_1_1), Diff(v_1_0, v_1_1),       # Row/Col uniqueness
            Less(1, v_0_1)                                 # Inequality: (0,0) < (0,1)

Variable Convention:
    - Variables: lowercase strings ("v_0_1" for cell (0,1))
    - Constants: integers (0, 1, 2, 3)
"""

from typing import List, Tuple, Dict
from .predicates import Literal, Val, Less, Diff, Domain
from .horn_kb import HornClauseKnowledgeBase, HornClause
from core import Puzzle


def Solution(*args) -> Literal:
    """Create a Solution(...) literal with all cell variables."""
    return Literal("Solution", args)


class HornClauseGenerator:
    """
    Generates Definite Clause KB using Generate-and-Test paradigm.
    
    Creates a single Solution rule that:
    1. Generates all possible assignments via Domain facts
    2. Tests all constraints via Diff and Less facts
    
    SLD resolution with backtracking explores the search space.
    """

    @staticmethod
    def generate(puzzle: Puzzle) -> HornClauseKnowledgeBase:
        """Generate complete KB with Generate-and-Test rule."""
        kb = HornClauseKnowledgeBase()
        
        # Add all facts
        for fact in HornClauseGenerator._get_facts(puzzle):
            kb.add_fact(fact)
        
        # Add the single Solution rule
        solution_rule = HornClauseGenerator._get_solution_rule(puzzle)
        if solution_rule is not None:
            kb.add_rule(solution_rule)
        
        return kb
    
    # ==================== Facts ====================

    @staticmethod
    def _get_facts(puzzle: Puzzle) -> List[Literal]:
        """Get all ground facts."""
        n = puzzle.N
        facts: List[Literal] = []
        
        # Given clue facts: Val(i,j,v) for pre-filled cells
        for i in range(n):
            for j in range(n):
                if puzzle.grid[i, j] != 0:
                    facts.append(Val(i, j, int(puzzle.grid[i, j])))
        
        # Domain facts: Domain(v) for v in 1..N
        for v in range(1, n + 1):
            facts.append(Domain(v))
        
        # Diff facts: Diff(a,b) for a != b
        for a in range(1, n + 1):
            for b in range(1, n + 1):
                if a != b:
                    facts.append(Diff(a, b))
        
        # Less facts: Less(a,b) for a < b
        for a in range(1, n + 1):
            for b in range(a + 1, n + 1):
                facts.append(Less(a, b))
        
        return facts

    # ==================== Solution Rule ====================

    @staticmethod
    def _get_solution_rule(puzzle: Puzzle) -> HornClause:
        """
        Generate the single Solution rule using Interleaved Generate-and-Test.
        
        Key optimization: Interleave Domain with Diff/Less constraints so that
        constraints are checked immediately after each variable is bound.
        This enables early pruning and dramatically reduces search space.
        
        Structure:
            Solution(v_0_1, v_1_0, ...) :-
                Domain(v_0_1), Diff(v_0_1, given1), Less(...),  # var 1
                Domain(v_1_0), Diff(v_1_0, v_0_1), Diff(...),   # var 2
                ...
        
        For each variable, we add:
        1. Domain(var) - generate possible value
        2. Diff(var, prev_var) - must differ from earlier variables in same row/col
        3. Diff(var, given) - must differ from given values in same row/col
        4. Less constraints involving this var (if other var is already bound)
        """
        n = puzzle.N
        
        # Collect empty cells and create variable names
        empty_cells: List[Tuple[int, int]] = []
        var_names: List[str] = []
        cell_to_var: Dict[Tuple[int, int], str] = {}
        
        for r in range(n):
            for c in range(n):
                if puzzle.grid[r, c] == 0:
                    var_name = f"v_{r}_{c}"
                    empty_cells.append((r, c))
                    var_names.append(var_name)
                    cell_to_var[(r, c)] = var_name
        
        if not empty_cells:
            return None  # No empty cells, puzzle already solved
        
        # Pre-compute which cells are in same row/col
        def same_row(c1, c2):
            return c1[0] == c2[0]
        
        def same_col(c1, c2):
            return c1[1] == c2[1]
        
        # Pre-compute inequality constraints for quick lookup
        # Maps (r,c) -> list of (other_cell, is_less) where is_less means this < other
        ineq_constraints: Dict[Tuple[int,int], List[Tuple[Tuple[int,int], bool]]] = {}
        for r in range(n):
            for c in range(n):
                ineq_constraints[(r,c)] = []
        
        for constraint in puzzle.h_constraints + puzzle.v_constraints:
            r1, c1 = constraint.cell1
            r2, c2 = constraint.cell2
            if constraint.direction == '<':
                ineq_constraints[(r1,c1)].append(((r2,c2), True))   # cell1 < cell2
                ineq_constraints[(r2,c2)].append(((r1,c1), False))  # cell2 > cell1
            else:  # '>'
                ineq_constraints[(r1,c1)].append(((r2,c2), False))  # cell1 > cell2
                ineq_constraints[(r2,c2)].append(((r1,c1), True))   # cell2 < cell1
        
        # Build interleaved body
        body: List[Literal] = []
        processed_cells = set()  # Track which cells have been processed
        
        for idx, (r, c) in enumerate(empty_cells):
            var = var_names[idx]
            
            # 1. GENERATE: Domain(var)
            body.append(Domain(var))
            
            # 2. TEST: Diff with given values in same row
            for c_other in range(n):
                if c_other != c and puzzle.grid[r, c_other] != 0:
                    body.append(Diff(var, int(puzzle.grid[r, c_other])))
            
            # 3. TEST: Diff with given values in same col
            for r_other in range(n):
                if r_other != r and puzzle.grid[r_other, c] != 0:
                    body.append(Diff(var, int(puzzle.grid[r_other, c])))
            
            # 4. TEST: Diff with already-processed variables in same row/col
            for prev_idx, (pr, pc) in enumerate(empty_cells[:idx]):
                if same_row((r,c), (pr,pc)) or same_col((r,c), (pr,pc)):
                    prev_var = var_names[prev_idx]
                    body.append(Diff(var, prev_var))
            
            # 5. TEST: Less constraints where both cells are now bound
            for (other_cell, is_less) in ineq_constraints[(r,c)]:
                or_r, or_c = other_cell
                
                # Get value/var for other cell
                if puzzle.grid[or_r, or_c] != 0:
                    other_val = int(puzzle.grid[or_r, or_c])
                    # Other cell is given, add constraint now
                    if is_less:
                        body.append(Less(var, other_val))
                    else:
                        body.append(Less(other_val, var))
                elif other_cell in processed_cells:
                    other_var = cell_to_var[other_cell]
                    # Other cell already processed, add constraint now
                    if is_less:
                        body.append(Less(var, other_var))
                    else:
                        body.append(Less(other_var, var))
                # If other cell not yet processed, constraint will be added when it is
            
            processed_cells.add((r, c))
        
        # Create Solution head with all variables
        head = Solution(*var_names)
        
        return HornClause(head, body)
    
    @staticmethod
    def get_empty_cells(puzzle: Puzzle) -> List[Tuple[int, int]]:
        """Get list of empty cell positions in row-major order."""
        empty = []
        for i in range(puzzle.N):
            for j in range(puzzle.N):
                if puzzle.grid[i, j] == 0:
                    empty.append((i, j))
        return empty
    
    @staticmethod
    def get_solution_goal(puzzle: Puzzle) -> Literal:
        """
        Get the Solution goal to prove.
        
        Returns Solution(v_0_1, v_1_0, ...) with unique variable for each empty cell.
        """
        var_names = []
        for r in range(puzzle.N):
            for c in range(puzzle.N):
                if puzzle.grid[r, c] == 0:
                    var_names.append(f"v_{r}_{c}")
        
        return Solution(*var_names)