"""
Horn Clause Generator for Futoshiki Puzzles.

Implements all axioms A1-A16 from futoshiki.md specification as Horn clauses
for use with backward chaining / SLD resolution.
"""

from typing import List
from .predicates import Literal, Val, Less
from .horn_kb import HornClauseKnowledgeBase, HornClause
from core import Puzzle


class HornClauseGenerator:
    """
    Generates a Horn clause knowledge base from a Futoshiki puzzle.

    """

    @staticmethod
    def generate(puzzle: Puzzle) -> HornClauseKnowledgeBase:
        """Generate complete Horn clause KB from puzzle."""
        n = puzzle.N
        kb = HornClauseKnowledgeBase()
        
        # Add facts
        for fact in HornClauseGenerator.get_facts(n, puzzle):
            kb.add_fact(fact)
        
        # Add rules
        for rule in HornClauseGenerator.get_rules(n, puzzle):
            kb.add_rule(rule)
        
        return kb

    @staticmethod
    def get_facts(n: int, puzzle: Puzzle) -> List[Literal]:
        """Get all facts (A9, A11)."""
        facts: List[Literal] = []
        facts += HornClauseGenerator.a9_given_clue_facts(n, puzzle)
        facts += HornClauseGenerator.a11_less_ground_truth_facts(n)
        return facts

    @staticmethod
    def get_rules(n: int, puzzle: Puzzle) -> List[HornClause]:
        """Get all rules (A1-A4, A12-A16)."""
        rules: List[HornClause] = []
        # Cell constraints
        rules += HornClauseGenerator.a1_cell_existence_rules(n)
        rules += HornClauseGenerator.a2_cell_uniqueness_rules(n)
        # Permutation constraints
        rules += HornClauseGenerator.a3_row_uniqueness_rules(n)
        rules += HornClauseGenerator.a4_column_uniqueness_rules(n)
        rules += HornClauseGenerator.a12_row_surjection_rules(n)
        rules += HornClauseGenerator.a13_column_surjection_rules(n)
        # Less relation
        rules += HornClauseGenerator.a14_less_irreflexivity_rules(n)
        rules += HornClauseGenerator.a15_less_asymmetry_rules(n)
        # Inequality constraints
        rules += HornClauseGenerator.a16_inequality_contrapositive_rules(n, puzzle)
        return rules

    @staticmethod
    def a9_given_clue_facts(n: int, puzzle: Puzzle) -> List[Literal]:
        """
        A9: Given Clues - Pre-filled cells must keep their given value.
        
        For each given cell (i,j,v) in the puzzle, emits: Val(i,j,v)
        """
        facts: List[Literal] = []
        for i in range(n):
            for j in range(n):
                if puzzle.grid[i, j] != 0:
                    v = puzzle.grid[i, j]
                    facts.append(Val(i, j, v))
        return facts

    @staticmethod
    def a11_less_ground_truth_facts(n: int) -> List[Literal]:
        """
        A11: Less Ground Truth - Define which number pairs satisfy "less than".
        
        For each pair (a,b) where 1 <= a < b <= N, emits: Less(a,b)
        """
        facts: List[Literal] = []
        for a in range(1, n + 1):
            for b in range(a + 1, n + 1):
                facts.append(Less(a, b))
        return facts

    @staticmethod
    def a1_cell_existence_rules(n: int) -> List[HornClause]:
        """
        A1: Cell Existence - Every cell must be filled with some value.
        """
        rules: List[HornClause] = []
        for i in range(n):
            for j in range(n):
                for v in range(1, n + 1):
                    others = [v2 for v2 in range(1, n + 1) if v2 != v]
                    body = [~Val(i, j, v2) for v2 in others]
                    rules.append(HornClause(Val(i, j, v), body))
        return rules

    @staticmethod
    def a2_cell_uniqueness_rules(n: int) -> List[HornClause]:
        """
        A2: Cell Uniqueness - A cell cannot hold two different values at once.
        """
        rules: List[HornClause] = []
        for i in range(n):
            for j in range(n):
                for v1 in range(1, n + 1):
                    for v2 in range(1, n + 1):
                        if v1 != v2:
                            rules.append(HornClause(~Val(i, j, v1), [Val(i, j, v2)]))
        return rules

    @staticmethod
    def a3_row_uniqueness_rules(n: int) -> List[HornClause]:
        """
        A3: Row Uniqueness - No value repeats in the same row.
        """
        rules: List[HornClause] = []
        for i in range(n):
            for j1 in range(n):
                for j2 in range(n):
                    if j1 != j2:
                        for v in range(1, n + 1):
                            rules.append(HornClause(~Val(i, j1, v), [Val(i, j2, v)]))
        return rules

    @staticmethod
    def a4_column_uniqueness_rules(n: int) -> List[HornClause]:
        """
        A4: Column Uniqueness - No value repeats in the same column.
        """
        rules: List[HornClause] = []
        for j in range(n):
            for i1 in range(n):
                for i2 in range(n):
                    if i1 != i2:
                        for v in range(1, n + 1):
                            rules.append(HornClause(~Val(i1, j, v), [Val(i2, j, v)]))
        return rules

    @staticmethod
    def a12_row_surjection_rules(n: int) -> List[HornClause]:
        """
        A12: Row Surjection - Every value 1..N must appear in each row.
        """
        rules: List[HornClause] = []
        for i in range(n):
            for v in range(1, n + 1):
                for j in range(n):
                    other_cols = [j2 for j2 in range(n) if j2 != j]
                    body = [~Val(i, j2, v) for j2 in other_cols]
                    rules.append(HornClause(Val(i, j, v), body))
        return rules

    @staticmethod
    def a13_column_surjection_rules(n: int) -> List[HornClause]:
        """
        A13: Column Surjection - Every value 1..N must appear in each column.
        """
        rules: List[HornClause] = []
        for j in range(n):
            for v in range(1, n + 1):
                for i in range(n):
                    other_rows = [i2 for i2 in range(n) if i2 != i]
                    body = [~Val(i2, j, v) for i2 in other_rows]
                    rules.append(HornClause(Val(i, j, v), body))
        return rules

    @staticmethod
    def a14_less_irreflexivity_rules(n: int) -> List[HornClause]:
        """
        A14: Less Irreflexivity - No number is less than itself.
        """
        rules: List[HornClause] = []
        for v in range(1, n + 1):
            # ~Less(v,v) as a fact (rule with empty body)
            rules.append(HornClause(~Less(v, v), []))
        return rules

    @staticmethod
    def a15_less_asymmetry_rules(n: int) -> List[HornClause]:
        """
        A15: Less Asymmetry - If a < b then b cannot be < a.
        
        Horn form: Less(v1,v2) => ~Less(v2,v1)
        """
        rules: List[HornClause] = []
        for v1 in range(1, n + 1):
            for v2 in range(1, n + 1):
                if v1 != v2:
                    rules.append(HornClause(~Less(v2, v1), [Less(v1, v2)]))
        return rules

    @staticmethod
    def a16_inequality_contrapositive_rules(n: int, puzzle: Puzzle) -> List[HornClause]:
        """
        A16: Inequality Contrapositive - Directly forbid value pairs that violate inequalities.
        
        For each constraint, emit rules that ban impossible value pairs:
        - LessH(i,j): left < right, ban v1 >= v2
        - GreaterH(i,j): left > right, ban v1 <= v2
        - LessV(i,j): top < bottom, ban v1 >= v2
        - GreaterV(i,j): top > bottom, ban v1 <= v2
        
        Horn form: Val(r2,c2,v2) => ~Val(r1,c1,v1) for forbidden pairs
        """
        rules: List[HornClause] = []
        
        # Horizontal constraints
        for constraint in puzzle.h_constraints:
            r1, c1 = constraint.cell1
            r2, c2 = constraint.cell2
            op = constraint.direction
            
            for v1 in range(1, n + 1):
                for v2 in range(1, n + 1):
                    if op == '<' and v1 >= v2:
                        # Ban: cell1=v1 and cell2=v2 when v1 >= v2
                        rules.append(HornClause(~Val(r1, c1, v1), [Val(r2, c2, v2)]))
                        rules.append(HornClause(~Val(r2, c2, v2), [Val(r1, c1, v1)]))
                    elif op == '>' and v1 <= v2:
                        # Ban: cell1=v1 and cell2=v2 when v1 <= v2
                        rules.append(HornClause(~Val(r1, c1, v1), [Val(r2, c2, v2)]))
                        rules.append(HornClause(~Val(r2, c2, v2), [Val(r1, c1, v1)]))
        
        # Vertical constraints
        for constraint in puzzle.v_constraints:
            r1, c1 = constraint.cell1
            r2, c2 = constraint.cell2
            op = constraint.direction
            
            for v1 in range(1, n + 1):
                for v2 in range(1, n + 1):
                    if op == '<' and v1 >= v2:
                        # Ban: cell1=v1 and cell2=v2 when v1 >= v2
                        rules.append(HornClause(~Val(r1, c1, v1), [Val(r2, c2, v2)]))
                        rules.append(HornClause(~Val(r2, c2, v2), [Val(r1, c1, v1)]))
                    elif op == '>' and v1 <= v2:
                        # Ban: cell1=v1 and cell2=v2 when v1 <= v2
                        rules.append(HornClause(~Val(r1, c1, v1), [Val(r2, c2, v2)]))
                        rules.append(HornClause(~Val(r2, c2, v2), [Val(r1, c1, v1)]))
        
        return rules