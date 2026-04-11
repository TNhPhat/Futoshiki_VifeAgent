"""
Horn clause generator for Forward Chaining constraint propagation.

This generator is deduction-only:
1. seed the KB with ground facts (Given, inequalities, Diff, Geq)
2. add Horn rules that propagate to NotVal / Val
3. avoid any generate-and-test "Solution(...)" rule
"""

from __future__ import annotations

from typing import List

from core.puzzle import Puzzle

from .horn_kb import HornClause, HornClauseKnowledgeBase
from .predicates import (
    Diff,
    Geq,
    Given,
    GreaterH,
    GreaterV,
    LessH,
    LessV,
    Literal,
    NotVal,
    Val,
)


class HornClauseGenerator2:
    @staticmethod
    def generate(puzzle: Puzzle) -> HornClauseKnowledgeBase:
        kb = HornClauseKnowledgeBase()
        for fact in HornClauseGenerator2._get_facts(puzzle):
            kb.add_fact(fact)
        for rule in HornClauseGenerator2._get_rules(puzzle):
            kb.add_rule(rule)
        return kb

    @staticmethod
    def _get_facts(puzzle: Puzzle) -> List[Literal]:
        n = puzzle.N
        facts: List[Literal] = []

        # Given clues
        for row, col, value in puzzle.get_given_cells():
            facts.append(Given(row, col, value))

        # Ground inequality facts from puzzle structure
        for constraint in puzzle.h_constraints:
            row, col = constraint.cell1
            if constraint.direction == "<":
                facts.append(LessH(row, col))
            else:
                facts.append(GreaterH(row, col))

        for constraint in puzzle.v_constraints:
            row, col = constraint.cell1
            if constraint.direction == "<":
                facts.append(LessV(row, col))
            else:
                facts.append(GreaterV(row, col))

        # Diff facts over board indices for A3/A4 propagation
        for left in range(n):
            for right in range(n):
                if left != right:
                    facts.append(Diff(left, right))

        # Geq(a, b) uses the axiom-compatible convention b >= a
        for left in range(1, n + 1):
            for right in range(1, n + 1):
                if right >= left:
                    facts.append(Geq(left, right))

        return facts

    @staticmethod
    def _get_rules(puzzle: Puzzle) -> List[HornClause]:
        rules: List[HornClause] = []

        # (1) A9 Given clues
        # Given(i,j,v) => Val(i,j,v)
        rules.append(
            HornClause(
                head=Val("i", "j", "v"),
                body=[Given("i", "j", "v")],
            )
        )

        # (2) A3 Row uniqueness
        # Val(i,j1,v) /\ Diff(j1,j2) => NotVal(i,j2,v)
        rules.append(
            HornClause(
                head=NotVal("i", "j2", "v"),
                body=[Val("i", "j1", "v"), Diff("j1", "j2")],
            )
        )

        # (3) A4 Column uniqueness
        # Val(i1,j,v) /\ Diff(i1,i2) => NotVal(i2,j,v)
        rules.append(
            HornClause(
                head=NotVal("i2", "j", "v"),
                body=[Val("i1", "j", "v"), Diff("i1", "i2")],
            )
        )

        # (4) A16 Inequality propagation
        # Grounded per concrete adjacent pair because the engine has no arithmetic terms.
        for constraint in puzzle.h_constraints:
            row, col = constraint.cell1
            right_col = col + 1

            if constraint.direction == "<":
                # Boundary pruning: left cell in "<" cannot be max; right cannot be min.
                rules.append(HornClause(head=NotVal(row, col, puzzle.N), body=[LessH(row, col)]))
                rules.append(HornClause(head=NotVal(row, right_col, 1), body=[LessH(row, col)]))

                # LessH(i,j) /\ Val(i,j,v1) /\ Geq(v2,v1) => NotVal(i,j+1,v2)
                rules.append(
                    HornClause(
                        head=NotVal(row, right_col, "v2"),
                        body=[LessH(row, col), Val(row, col, "v1"), Geq("v2", "v1")],
                    )
                )
                # Reverse propagation:
                # LessH(i,j) /\ Val(i,j+1,v2) /\ Geq(v2,v1) => NotVal(i,j,v1)
                rules.append(
                    HornClause(
                        head=NotVal(row, col, "v1"),
                        body=[LessH(row, col), Val(row, right_col, "v2"), Geq("v2", "v1")],
                    )
                )
            else:
                # Boundary pruning: left cell in ">" cannot be min; right cannot be max.
                rules.append(HornClause(head=NotVal(row, col, 1), body=[GreaterH(row, col)]))
                rules.append(HornClause(head=NotVal(row, right_col, puzzle.N), body=[GreaterH(row, col)]))

                # GreaterH(i,j) /\ Val(i,j,v1) /\ Geq(v1,v2) => NotVal(i,j+1,v2)
                rules.append(
                    HornClause(
                        head=NotVal(row, right_col, "v2"),
                        body=[GreaterH(row, col), Val(row, col, "v1"), Geq("v1", "v2")],
                    )
                )
                # Reverse propagation:
                # GreaterH(i,j) /\ Val(i,j+1,v2) /\ Geq(v1,v2) => NotVal(i,j,v1)
                rules.append(
                    HornClause(
                        head=NotVal(row, col, "v1"),
                        body=[GreaterH(row, col), Val(row, right_col, "v2"), Geq("v1", "v2")],
                    )
                )

        for constraint in puzzle.v_constraints:
            row, col = constraint.cell1
            bottom_row = row + 1

            if constraint.direction == "<":
                # Boundary pruning: top cell in "<" cannot be max; bottom cannot be min.
                rules.append(HornClause(head=NotVal(row, col, puzzle.N), body=[LessV(row, col)]))
                rules.append(HornClause(head=NotVal(bottom_row, col, 1), body=[LessV(row, col)]))

                # LessV(i,j) /\ Val(i,j,v1) /\ Geq(v2,v1) => NotVal(i+1,j,v2)
                rules.append(
                    HornClause(
                        head=NotVal(bottom_row, col, "v2"),
                        body=[LessV(row, col), Val(row, col, "v1"), Geq("v2", "v1")],
                    )
                )
                # Reverse propagation:
                # LessV(i,j) /\ Val(i+1,j,v2) /\ Geq(v2,v1) => NotVal(i,j,v1)
                rules.append(
                    HornClause(
                        head=NotVal(row, col, "v1"),
                        body=[LessV(row, col), Val(bottom_row, col, "v2"), Geq("v2", "v1")],
                    )
                )
            else:
                # Boundary pruning: top cell in ">" cannot be min; bottom cannot be max.
                rules.append(HornClause(head=NotVal(row, col, 1), body=[GreaterV(row, col)]))
                rules.append(HornClause(head=NotVal(bottom_row, col, puzzle.N), body=[GreaterV(row, col)]))

                # GreaterV(i,j) /\ Val(i,j,v1) /\ Geq(v1,v2) => NotVal(i+1,j,v2)
                rules.append(
                    HornClause(
                        head=NotVal(bottom_row, col, "v2"),
                        body=[GreaterV(row, col), Val(row, col, "v1"), Geq("v1", "v2")],
                    )
                )
                # Reverse propagation:
                # GreaterV(i,j) /\ Val(i+1,j,v2) /\ Geq(v1,v2) => NotVal(i,j,v1)
                rules.append(
                    HornClause(
                        head=NotVal(row, col, "v1"),
                        body=[GreaterV(row, col), Val(bottom_row, col, "v2"), Geq("v1", "v2")],
                    )
                )

        return rules
