"""
Pure Prolog-style SLD Resolution Solver for Futoshiki.

This solver uses the Generate-and-Test paradigm with SLD resolution:
- A single Solution rule generates all possible assignments
- Constraints are tested via Diff and Less facts
- SLD backtracking explores the search space

How it works:
1. Generate KB with Domain, Diff, Less facts and a single Solution rule
2. Create goal: Solution(v_0_1, v_1_0, ...) with variables for empty cells
3. Call engine.prove_all(goals) - returns substitution {v_0_1: 2, v_1_0: 1, ...}
4. Extract solution from substitution

The Solution rule structure:
    Solution(v_0_1, v_1_0, ...) :-
        Domain(v_0_1), Domain(v_1_0), ...  # Generate
        Diff(...), Diff(...), ...           # Test uniqueness
        Less(...), ...                      # Test inequalities
"""

from typing import Optional, List, Tuple
import time
import tracemalloc

from core.puzzle import Puzzle
from utils import Stats
from .base_solver import BaseSolver
from fol import HornClauseGenerator, Literal
from inference import BackwardChainingEngine


class BackwardChaining(BaseSolver):
    """
    Futoshiki solver using Generate-and-Test with SLD resolution.
    
    The solver:
    1. Generates a KB with a single Solution rule
    2. Proves the Solution goal
    3. Extracts variable bindings as the solution
    """
    
    def __init__(self):
        self._t0: float = 0.0
        self._stats: Stats = None

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        """
        Solve puzzle using Generate-and-Test SLD resolution.
        """
        self._start_trace()
        
        # Generate KB with Generate-and-Test Solution rule
        kb = HornClauseGenerator.generate(puzzle)
        
        # Generate the Solution goal with variable names
        goal = self._generate_goal(puzzle)
        empty_cells = HornClauseGenerator.get_empty_cells(puzzle)
        var_names = [f"v_{r}_{c}" for r, c in empty_cells]
        
        # Create engine
        engine = BackwardChainingEngine(kb=kb)
        
        # Solve via SLD resolution
        substitution = engine.prove_all([goal])
        
        self._end_trace()
        self._stats.inference_count = engine.inference_count
        
        if substitution is None:
            return None, self._stats
        
        # Build solution from substitution
        solution = puzzle.copy()
        
        for idx, (r, c) in enumerate(empty_cells):
            var_name = var_names[idx]
            value = self._resolve_value(var_name, substitution)
            if value is not None and isinstance(value, int):
                solution.grid[r, c] = value
        
        return solution, self._stats
    
    def _generate_goal(self, puzzle: Puzzle) -> Literal:
        """
        Generate the Solution goal for SLD resolution.
        
        Returns Solution(v_0_1, v_1_0, ...) with a unique variable
        for each empty cell in row-major order.
        """
        return HornClauseGenerator.get_solution_goal(puzzle)
    
    def _resolve_value(self, var_name: str, substitution: dict) -> Optional[int]:
        """
        Resolve a variable name to its final value through the substitution chain.
        
        Follows the chain: var_name -> renamed_var -> ... -> final_value
        """
        value = var_name
        visited = set()
        
        while isinstance(value, str) and value not in visited:
            visited.add(value)
            if value in substitution:
                value = substitution[value]
            else:
                # Variable not directly in substitution
                # Check if any key is a renamed version of our variable
                found = False
                for key, val in substitution.items():
                    if key == value or (isinstance(key, str) and key.startswith(value + "_")):
                        value = val
                        found = True
                        break
                if not found:
                    break
        
        return value if isinstance(value, int) else None
        
    def _start_trace(self):
        self._stats = Stats(0, 0, 0, 0, 0)
        tracemalloc.start()
        self._t0 = time.perf_counter()

    def _end_trace(self):
        self._stats.time_ms = (time.perf_counter() - self._t0) * 1000
        _, self._stats.memory_kb = tracemalloc.get_traced_memory()
        self._stats.memory_kb /= 1024
        tracemalloc.stop()
    
    def get_name(self) -> str:
        return "Backward Chaining (Generate-and-Test SLD)"