"""
Backward Chaining Solver for Futoshiki using SLD Resolution.

Uses Prolog-style backward chaining to verify cell assignments:
- Generate Horn clause KB with uniqueness/inequality rules
- For each candidate value, use SLD resolution to check if forbidden
- Backtrack when no valid value exists
"""

from typing import List, Tuple
import time
import tracemalloc

from core.puzzle import Puzzle
from utils import Stats
from .base_solver import BaseSolver
from fol import HornClauseKnowledgeBase, HornClauseGenerator, Literal
from fol.predicates import Val
from inference import BackwardChainingEngine


class BackwardChaining(BaseSolver):
    """
    Futoshiki solver using SLD resolution (Prolog-style backward chaining).
    
    Algorithm:
    1. Generate Horn clause KB with rules (cell/row/col uniqueness, inequality)
    2. For each empty cell, try values 1..N
    3. Use SLD resolution to prove ~Val(i,j,v) - if provable, value is forbidden
    4. If not provable, value is allowed - make assignment and recurse
    5. Backtrack if no valid value found
    """
    
    def __init__(self):
        self._t0: float = 0.0
        self._stats: Stats = None
        self._inference_count: int = 0

    def solve(self, puzzle: Puzzle) -> tuple[Puzzle | None, Stats]:
        """Solve puzzle using backward chaining with SLD resolution."""
        self._start_trace()
        self._inference_count = 0
        
        # Generate base KB with rules
        base_kb = HornClauseGenerator.generate(puzzle)
        
        empty_cells = puzzle.get_empty_cells()
        current_facts: List[Literal] = []
        solution = puzzle.copy()
        
        self._solve_recursive(base_kb, empty_cells, 0, current_facts, puzzle.N, solution)
        
        self._end_trace()
        self._stats.inference_count = self._inference_count
        return solution, self._stats
    
    def _solve_recursive(self, 
                         base_kb: HornClauseKnowledgeBase,
                         empty_cells: List[Tuple[int, int]], 
                         idx: int,
                         current_facts: List[Literal],
                         n: int,
                         solution: Puzzle) -> bool:
        """Recursively assign values using SLD resolution for validation."""
        if idx >= len(empty_cells):
            return True
        
        i, j = empty_cells[idx]
        
        for v in range(1, n + 1):
            self._inference_count += 1
            
            if self._is_value_allowed(base_kb, current_facts, i, j, v):
                # Value allowed - make assignment
                current_facts.append(Val(i, j, v))
                solution.grid[i, j] = v
                
                if self._solve_recursive(base_kb, empty_cells, idx + 1, 
                                          current_facts, n, solution):
                    return True
                
                # Backtrack
                current_facts.pop()
                solution.grid[i, j] = 0
        
        return False
    
    def _is_value_allowed(self, 
                          base_kb: HornClauseKnowledgeBase,
                          current_facts: List[Literal],
                          i: int, j: int, v: int) -> bool:
        """
        Check if Val(i,j,v) is allowed using SLD resolution.
        
        Returns True if ~Val(i,j,v) cannot be proven (value allowed).
        Returns False if ~Val(i,j,v) is provable (value forbidden).
        """
        kb = self._build_kb_with_facts(base_kb, current_facts)
        engine = BackwardChainingEngine(kb=kb, depth_limit=100)
        
        # Try to prove value is forbidden
        result = engine.prove(~Val(i, j, v))
        return result is None  # Allowed if we cannot prove it's forbidden
    
    def _build_kb_with_facts(self,
                             base_kb: HornClauseKnowledgeBase,
                             current_facts: List[Literal]) -> HornClauseKnowledgeBase:
        """Build KB combining base rules with current assignment facts."""
        kb = HornClauseKnowledgeBase()
        
        for clause in base_kb._clause:
            kb.add_clause(clause)
        
        for fact in current_facts:
            kb.add_fact(fact)
        
        return kb
        
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
        return "Backward Chaining (SLD Resolution)"