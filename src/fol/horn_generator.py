"""
Horn Clause Generator for Futoshiki Puzzles (Prolog-style).

Generates Horn clauses with first-order variables for SLD resolution.
Implements axioms from futoshiki.md specification.

Variable Convention:
    - Variables: lowercase strings ("i", "j", "v", "v1", "v2")
    - Constants: integers (0, 1, 2, 3)
"""

from typing import List
from .predicates import Literal, Val, Less, Diff
from .horn_kb import HornClauseKnowledgeBase, HornClause
from core import Puzzle


class HornClauseGenerator:
    """
    Generates Prolog-style Horn clause KB from a Futoshiki puzzle.
    
    Facts are ground (no variables).
    Rules use variables that unify during SLD resolution.
    """

    @staticmethod
    def generate(puzzle: Puzzle) -> HornClauseKnowledgeBase:
        """Generate complete Horn clause KB from puzzle."""
        kb = HornClauseKnowledgeBase()
        
        for fact in HornClauseGenerator._get_facts(puzzle):
            kb.add_fact(fact)
        
        for rule in HornClauseGenerator._get_rules(puzzle):
            kb.add_rule(rule)
        
        return kb

    # ==================== Facts ====================

    @staticmethod
    def _get_facts(puzzle: Puzzle) -> List[Literal]:
        """Get all ground facts."""
        n = puzzle.N
        facts: List[Literal] = []
        facts.extend(HornClauseGenerator._given_clue_facts(puzzle))
        facts.extend(HornClauseGenerator._less_facts(n))
        facts.extend(HornClauseGenerator._diff_facts(n))
        return facts

    @staticmethod
    def _given_clue_facts(puzzle: Puzzle) -> List[Literal]:
        """A9: Val(i,j,v) for pre-filled cells."""
        facts = []
        for i in range(puzzle.N):
            for j in range(puzzle.N):
                if puzzle.grid[i, j] != 0:
                    facts.append(Val(i, j, int(puzzle.grid[i, j])))
        return facts

    @staticmethod
    def _less_facts(n: int) -> List[Literal]:
        """A11: Less(a,b) for all a < b."""
        return [Less(a, b) for a in range(1, n + 1) for b in range(a + 1, n + 1)]

    @staticmethod
    def _diff_facts(n: int) -> List[Literal]:
        """Diff(a,b) for a != b (indices 0..N-1 and values 1..N)."""
        facts = []
        # Index differences
        for a in range(n):
            for b in range(n):
                if a != b:
                    facts.append(Diff(a, b))
        # Value differences
        for a in range(1, n + 1):
            for b in range(1, n + 1):
                if a != b:
                    facts.append(Diff(a, b))
        return facts

    # ==================== Rules ====================

    @staticmethod
    def _get_rules(puzzle: Puzzle) -> List[HornClause]:
        """Get all rules with variables."""
        rules: List[HornClause] = []
        rules.extend(HornClauseGenerator._cell_uniqueness_rule())
        rules.extend(HornClauseGenerator._row_uniqueness_rule())
        rules.extend(HornClauseGenerator._column_uniqueness_rule())
        rules.extend(HornClauseGenerator._less_asymmetry_rule())
        rules.extend(HornClauseGenerator._inequality_rules(puzzle))
        return rules

    @staticmethod
    def _cell_uniqueness_rule() -> List[HornClause]:
        """A2: Val(i,j,v2) ∧ Diff(v1,v2) => ~Val(i,j,v1)"""
        return [HornClause(
            ~Val("i", "j", "v1"),
            [Val("i", "j", "v2"), Diff("v1", "v2")]
        )]

    @staticmethod
    def _row_uniqueness_rule() -> List[HornClause]:
        """A3: Val(i,j2,v) ∧ Diff(j1,j2) => ~Val(i,j1,v)"""
        return [HornClause(
            ~Val("i", "j1", "v"),
            [Val("i", "j2", "v"), Diff("j1", "j2")]
        )]

    @staticmethod
    def _column_uniqueness_rule() -> List[HornClause]:
        """A4: Val(i2,j,v) ∧ Diff(i1,i2) => ~Val(i1,j,v)"""
        return [HornClause(
            ~Val("i1", "j", "v"),
            [Val("i2", "j", "v"), Diff("i1", "i2")]
        )]

    @staticmethod
    def _less_asymmetry_rule() -> List[HornClause]:
        """A15: Less(v1,v2) => ~Less(v2,v1)"""
        return [HornClause(
            ~Less("v2", "v1"),
            [Less("v1", "v2")]
        )]

    @staticmethod
    def _inequality_rules(puzzle: Puzzle) -> List[HornClause]:
        """
        A16: Inequality constraints.
        
        For cell1 < cell2: Val(cell2,v2) ∧ ~Less(v1,v2) => ~Val(cell1,v1)
        For cell1 > cell2: Val(cell2,v2) ∧ ~Less(v2,v1) => ~Val(cell1,v1)
        """
        rules = []
        
        for constraint in puzzle.h_constraints + puzzle.v_constraints:
            r1, c1 = constraint.cell1
            r2, c2 = constraint.cell2
            
            if constraint.direction == '<':
                rules.append(HornClause(
                    ~Val(r1, c1, "v1"),
                    [Val(r2, c2, "v2"), ~Less("v1", "v2")]
                ))
            else:  # '>'
                rules.append(HornClause(
                    ~Val(r1, c1, "v1"),
                    [Val(r2, c2, "v2"), ~Less("v2", "v1")]
                ))
        
        return rules