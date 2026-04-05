"""
Integration test: Parser -> Puzzle -> HornClauseGenerator -> HornClauseKnowledgeBase

Tests the Horn clause generation pipeline on 2x2 and 4x4 puzzles.

Axioms implemented in HornClauseGenerator:
    Facts:
        A9  - Given clues: Val(i,j,v) for pre-filled cells
        A11 - Less ground truth: Less(a,b) for all a < b
    
    Rules:
        A1  - Cell existence: if all other values eliminated, this value holds
        A2  - Cell uniqueness: Val(i,j,v2) => ~Val(i,j,v1) for v1 != v2
        A3  - Row uniqueness: Val(i,j2,v) => ~Val(i,j1,v) for j1 != j2
        A4  - Column uniqueness: Val(i2,j,v) => ~Val(i1,j,v) for i1 != i2
        A12 - Row surjection: if value eliminated from other cols, it's here
        A13 - Column surjection: if value eliminated from other rows, it's here
        A14 - Less irreflexivity: ~Less(v,v) for each v
        A15 - Less asymmetry: Less(v1,v2) => ~Less(v2,v1)
        A16 - Inequality contrapositive: forbid value pairs violating constraints

Rule counts for N×N grid:
    A1:  N² × N rules (each cell, each value)
    A2:  N² × N × (N-1) rules
    A3:  N × N × (N-1) × N rules
    A4:  N × N × (N-1) × N rules
    A12: N × N × N rules
    A13: N × N × N rules
    A14: N rules
    A15: N × (N-1) rules
    A16: 2 × (forbidden pairs per constraint) × (number of constraints)
"""

import os
import sys
from math import comb

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.parser import Parser
from fol.horn_generator import HornClauseGenerator
from fol.horn_kb import HornClauseKnowledgeBase, HornClause
from fol.predicates import Val, Less


# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURE_2X2 = os.path.join(os.path.dirname(__file__), "fixtures", "input_2x2.txt")
FIXTURE_4X4 = os.path.join(os.path.dirname(__file__), "fixtures", "input_4x4.txt")


# ---------------------------------------------------------------------------
# Expected values for 2x2
# ---------------------------------------------------------------------------

N_2X2 = 2
GIVEN_CELLS_2X2 = [(0, 0, 1)]
H_CONSTRAINTS_2X2 = 1  # LessH at (0,0)
V_CONSTRAINTS_2X2 = 1  # GreaterV at (0,1)


def expected_fact_count(n: int, num_given: int) -> int:
    """Calculate expected number of facts (A9 + A11)."""
    a9 = num_given              # Given clue facts
    a11 = comb(n, 2)            # Less(a,b) for a < b
    return a9 + a11


def expected_rule_count(n: int, num_h_constraints: int, num_v_constraints: int) -> int:
    """Calculate expected number of rules for Horn clause KB."""
    a1 = n * n * n                          # Cell existence
    a2 = n * n * n * (n - 1)                # Cell uniqueness
    a3 = n * n * (n - 1) * n                # Row uniqueness
    a4 = n * n * (n - 1) * n                # Column uniqueness
    a12 = n * n * n                         # Row surjection
    a13 = n * n * n                         # Column surjection
    a14 = n                                  # Less irreflexivity
    a15 = n * (n - 1)                       # Less asymmetry
    
    # A16: for each constraint, forbidden pairs × 2 (both directions)
    # For '<': v1 >= v2 means n*(n+1)/2 pairs
    # For '>': v1 <= v2 means n*(n+1)/2 pairs
    forbidden_pairs = n * (n + 1) // 2
    a16 = (num_h_constraints + num_v_constraints) * forbidden_pairs * 2
    
    return a1 + a2 + a3 + a4 + a12 + a13 + a14 + a15 + a16


# ---------------------------------------------------------------------------
# Expected values for 4x4
# ---------------------------------------------------------------------------

N_4X4 = 4
GIVEN_CELLS_4X4 = [(0, 0, 1), (1, 1, 2), (2, 2, 3)]
H_CONSTRAINTS_4X4 = 2  # LessH at (0,0), GreaterH at (1,2)
V_CONSTRAINTS_4X4 = 2  # LessV at (0,1), GreaterV at (2,0)


# ===========================================================================
# 2x2 Tests
# ===========================================================================


def test_2x2_parser_returns_puzzle():
    """Parser.parse() succeeds for 2x2 fixture."""
    puzzle = Parser().parse(FIXTURE_2X2)
    assert puzzle is not None
    assert puzzle.N == N_2X2
    print(f"  [PASS] Parser returns 2x2 puzzle (N={puzzle.N})")


def test_2x2_puzzle_given_cells():
    """Puzzle has correct given cells."""
    puzzle = Parser().parse(FIXTURE_2X2)
    assert sorted(puzzle.get_given_cells()) == sorted(GIVEN_CELLS_2X2)
    print(f"  [PASS] Given cells: {GIVEN_CELLS_2X2}")


def test_2x2_puzzle_constraints():
    """Puzzle has correct constraint counts."""
    puzzle = Parser().parse(FIXTURE_2X2)
    assert len(puzzle.h_constraints) == H_CONSTRAINTS_2X2
    assert len(puzzle.v_constraints) == V_CONSTRAINTS_2X2
    print(f"  [PASS] Constraints: {H_CONSTRAINTS_2X2}H, {V_CONSTRAINTS_2X2}V")


def test_2x2_hornkb_generation():
    """HornClauseGenerator.generate() returns a HornClauseKnowledgeBase."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    assert isinstance(kb, HornClauseKnowledgeBase)
    print(f"  [PASS] HornClauseGenerator returns KB")


def test_2x2_hornkb_clause_count():
    """HornKB has expected number of total clauses."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    expected_facts = expected_fact_count(N_2X2, len(GIVEN_CELLS_2X2))
    expected_rules = expected_rule_count(N_2X2, H_CONSTRAINTS_2X2, V_CONSTRAINTS_2X2)
    expected_total = expected_facts + expected_rules
    
    assert kb.clause_count == expected_total, \
        f"Clause count: {kb.clause_count} != {expected_total}"
    print(f"  [PASS] Total clauses: {kb.clause_count} == {expected_total}")


def test_2x2_hornkb_facts():
    """HornKB facts include given clues and Less ground truth."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check given clue fact
    given_clauses = kb.get_clause_for("Val")
    given_facts = [c for c in given_clauses if c.is_fact() and not c.head.negated]
    assert len(given_facts) == len(GIVEN_CELLS_2X2), \
        f"Expected {len(GIVEN_CELLS_2X2)} Val facts, got {len(given_facts)}"
    
    # Check Less ground truth facts
    less_clauses = kb.get_clause_for("Less")
    less_facts = [c for c in less_clauses if c.is_fact() and not c.head.negated]
    assert len(less_facts) == comb(N_2X2, 2), \
        f"Expected {comb(N_2X2, 2)} Less facts, got {len(less_facts)}"
    
    print(f"  [PASS] Facts: {len(given_facts)} Val, {len(less_facts)} Less")


def test_2x2_hornkb_given_val_content():
    """Given clue Val(0,0,1) is in the KB."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    val_clauses = kb.get_clause_for("Val")
    expected_lit = Val(0, 0, 1)
    found = any(
        c.is_fact() and c.head == expected_lit 
        for c in val_clauses
    )
    assert found, f"Expected {expected_lit} as a fact"
    print(f"  [PASS] Val(0,0,1) is a fact")


def test_2x2_hornkb_less_content():
    """Less(1,2) is in the KB as a fact."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    less_clauses = kb.get_clause_for("Less")
    expected_lit = Less(1, 2)
    found = any(
        c.is_fact() and c.head == expected_lit 
        for c in less_clauses
    )
    assert found, f"Expected {expected_lit} as a fact"
    print(f"  [PASS] Less(1,2) is a fact")


def test_2x2_hornkb_cell_uniqueness_rules():
    """Cell uniqueness rules exist: Val(i,j,v2) => ~Val(i,j,v1)."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for a specific cell uniqueness rule: Val(0,0,2) => ~Val(0,0,1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val(0, 0, 1)
    expected_body = Val(0, 0, 2)
    
    found = any(
        c.head == expected_head and len(c.body) == 1 and c.body[0] == expected_body
        for c in val_clauses
    )
    assert found, f"Expected rule: {expected_body} => {expected_head}"
    print(f"  [PASS] Cell uniqueness rule exists")


def test_2x2_hornkb_row_uniqueness_rules():
    """Row uniqueness rules exist: Val(i,j2,v) => ~Val(i,j1,v)."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for: Val(0,1,1) => ~Val(0,0,1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val(0, 0, 1)
    expected_body = Val(0, 1, 1)
    
    found = any(
        c.head == expected_head and len(c.body) == 1 and c.body[0] == expected_body
        for c in val_clauses
    )
    assert found, f"Expected rule: {expected_body} => {expected_head}"
    print(f"  [PASS] Row uniqueness rule exists")


def test_2x2_hornkb_inequality_rules():
    """Inequality contrapositive rules exist for LessH constraint."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # LessH at (0,0): cell(0,0) < cell(0,1)
    # Should ban v1=2, v2=1: Val(0,1,1) => ~Val(0,0,2)
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val(0, 0, 2)
    expected_body = Val(0, 1, 1)
    
    found = any(
        c.head == expected_head and len(c.body) == 1 and c.body[0] == expected_body
        for c in val_clauses
    )
    assert found, f"Expected inequality rule: {expected_body} => {expected_head}"
    print(f"  [PASS] Inequality contrapositive rule exists")


# ===========================================================================
# 4x4 Tests
# ===========================================================================


def test_4x4_parser_returns_puzzle():
    """Parser.parse() succeeds for 4x4 fixture."""
    puzzle = Parser().parse(FIXTURE_4X4)
    assert puzzle is not None
    assert puzzle.N == N_4X4
    print(f"  [PASS] Parser returns 4x4 puzzle (N={puzzle.N})")


def test_4x4_puzzle_given_cells():
    """Puzzle has correct given cells."""
    puzzle = Parser().parse(FIXTURE_4X4)
    assert sorted(puzzle.get_given_cells()) == sorted(GIVEN_CELLS_4X4)
    print(f"  [PASS] Given cells: {GIVEN_CELLS_4X4}")


def test_4x4_puzzle_constraints():
    """Puzzle has correct constraint counts."""
    puzzle = Parser().parse(FIXTURE_4X4)
    assert len(puzzle.h_constraints) == H_CONSTRAINTS_4X4
    assert len(puzzle.v_constraints) == V_CONSTRAINTS_4X4
    print(f"  [PASS] Constraints: {H_CONSTRAINTS_4X4}H, {V_CONSTRAINTS_4X4}V")


def test_4x4_hornkb_generation():
    """HornClauseGenerator.generate() returns a HornClauseKnowledgeBase."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    assert isinstance(kb, HornClauseKnowledgeBase)
    print(f"  [PASS] HornClauseGenerator returns KB")


def test_4x4_hornkb_clause_count():
    """HornKB has expected number of total clauses."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    expected_facts = expected_fact_count(N_4X4, len(GIVEN_CELLS_4X4))
    expected_rules = expected_rule_count(N_4X4, H_CONSTRAINTS_4X4, V_CONSTRAINTS_4X4)
    expected_total = expected_facts + expected_rules
    
    assert kb.clause_count == expected_total, \
        f"Clause count: {kb.clause_count} != {expected_total}"
    print(f"  [PASS] Total clauses: {kb.clause_count} == {expected_total}")


def test_4x4_hornkb_facts():
    """HornKB facts include given clues and Less ground truth."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check given clue facts
    given_clauses = kb.get_clause_for("Val")
    given_facts = [c for c in given_clauses if c.is_fact() and not c.head.negated]
    assert len(given_facts) == len(GIVEN_CELLS_4X4), \
        f"Expected {len(GIVEN_CELLS_4X4)} Val facts, got {len(given_facts)}"
    
    # Check Less ground truth facts
    less_clauses = kb.get_clause_for("Less")
    less_facts = [c for c in less_clauses if c.is_fact() and not c.head.negated]
    assert len(less_facts) == comb(N_4X4, 2), \
        f"Expected {comb(N_4X4, 2)} Less facts, got {len(less_facts)}"
    
    print(f"  [PASS] Facts: {len(given_facts)} Val, {len(less_facts)} Less")


def test_4x4_hornkb_given_val_content():
    """Given clue literals are in the KB."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    val_clauses = kb.get_clause_for("Val")
    
    for i, j, v in GIVEN_CELLS_4X4:
        expected_lit = Val(i, j, v)
        found = any(
            c.is_fact() and c.head == expected_lit 
            for c in val_clauses
        )
        assert found, f"Expected {expected_lit} as a fact"
    
    print(f"  [PASS] All given Val literals are facts")


def test_4x4_hornkb_less_content():
    """All Less(a,b) for a<b are in the KB."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    less_clauses = kb.get_clause_for("Less")
    
    for a in range(1, N_4X4 + 1):
        for b in range(a + 1, N_4X4 + 1):
            expected_lit = Less(a, b)
            found = any(
                c.is_fact() and c.head == expected_lit 
                for c in less_clauses
            )
            assert found, f"Expected {expected_lit} as a fact"
    
    print(f"  [PASS] All Less(a,b) facts present ({comb(N_4X4, 2)} pairs)")


def test_4x4_hornkb_less_irreflexivity():
    """~Less(v,v) rules exist for each v."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    less_clauses = kb.get_clause_for("Less")
    
    for v in range(1, N_4X4 + 1):
        expected_lit = ~Less(v, v)
        found = any(
            c.is_fact() and c.head == expected_lit 
            for c in less_clauses
        )
        assert found, f"Expected {expected_lit} as a fact"
    
    print(f"  [PASS] All ~Less(v,v) facts present ({N_4X4} literals)")


def test_4x4_hornkb_less_asymmetry():
    """Less asymmetry rules: Less(v1,v2) => ~Less(v2,v1)."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    less_clauses = kb.get_clause_for("Less")
    
    # Check Less(1,2) => ~Less(2,1)
    expected_head = ~Less(2, 1)
    expected_body = Less(1, 2)
    
    found = any(
        c.head == expected_head and len(c.body) == 1 and c.body[0] == expected_body
        for c in less_clauses
    )
    assert found, f"Expected rule: {expected_body} => {expected_head}"
    print(f"  [PASS] Less asymmetry rule exists")


def test_4x4_hornkb_row_surjection():
    """Row surjection rules exist: value must appear in each row."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for row surjection rule for row 0, value 1, column 0
    # Body: ~Val(0,1,1) ∧ ~Val(0,2,1) ∧ ~Val(0,3,1)
    # Head: Val(0,0,1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = Val(0, 0, 1)
    expected_body_lits = {~Val(0, 1, 1), ~Val(0, 2, 1), ~Val(0, 3, 1)}
    
    found = any(
        c.head == expected_head and set(c.body) == expected_body_lits
        for c in val_clauses
    )
    assert found, f"Expected row surjection rule for Val(0,0,1)"
    print(f"  [PASS] Row surjection rule exists")


def test_4x4_hornkb_col_surjection():
    """Column surjection rules exist: value must appear in each column."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for column surjection rule for col 0, value 1, row 0
    # Body: ~Val(1,0,1) ∧ ~Val(2,0,1) ∧ ~Val(3,0,1)
    # Head: Val(0,0,1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = Val(0, 0, 1)
    expected_body_lits = {~Val(1, 0, 1), ~Val(2, 0, 1), ~Val(3, 0, 1)}
    
    found = any(
        c.head == expected_head and set(c.body) == expected_body_lits
        for c in val_clauses
    )
    assert found, f"Expected column surjection rule for Val(0,0,1)"
    print(f"  [PASS] Column surjection rule exists")


def test_4x4_hornkb_cell_existence():
    """Cell existence rules exist: if all other values eliminated, this holds."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for cell existence rule for cell (0,0), value 1
    # Body: ~Val(0,0,2) ∧ ~Val(0,0,3) ∧ ~Val(0,0,4)
    # Head: Val(0,0,1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = Val(0, 0, 1)
    expected_body_lits = {~Val(0, 0, 2), ~Val(0, 0, 3), ~Val(0, 0, 4)}
    
    found = any(
        c.head == expected_head and set(c.body) == expected_body_lits
        for c in val_clauses
    )
    assert found, f"Expected cell existence rule for Val(0,0,1)"
    print(f"  [PASS] Cell existence rule exists")


def test_4x4_hornkb_inequality_lessh():
    """Inequality contrapositive rules exist for LessH constraint."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # LessH at (0,0): cell(0,0) < cell(0,1)
    # Should ban v1=4, v2=1: Val(0,1,1) => ~Val(0,0,4)
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val(0, 0, 4)
    expected_body = Val(0, 1, 1)
    
    found = any(
        c.head == expected_head and len(c.body) == 1 and c.body[0] == expected_body
        for c in val_clauses
    )
    assert found, f"Expected inequality rule: {expected_body} => {expected_head}"
    print(f"  [PASS] LessH contrapositive rule exists")


def test_4x4_hornkb_inequality_greaterh():
    """Inequality contrapositive rules exist for GreaterH constraint."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # GreaterH at (1,2): cell(1,2) > cell(1,3)
    # Should ban v1=1, v2=4: Val(1,3,4) => ~Val(1,2,1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val(1, 2, 1)
    expected_body = Val(1, 3, 4)
    
    found = any(
        c.head == expected_head and len(c.body) == 1 and c.body[0] == expected_body
        for c in val_clauses
    )
    assert found, f"Expected inequality rule: {expected_body} => {expected_head}"
    print(f"  [PASS] GreaterH contrapositive rule exists")


# ===========================================================================
# Runner
# ===========================================================================


if __name__ == "__main__":
    print("=== Integration: Parser -> Puzzle -> HornClauseKnowledgeBase ===\n")
    
    print("--- 2x2 Puzzle Tests ---")
    test_2x2_parser_returns_puzzle()
    test_2x2_puzzle_given_cells()
    test_2x2_puzzle_constraints()
    test_2x2_hornkb_generation()
    test_2x2_hornkb_clause_count()
    test_2x2_hornkb_facts()
    test_2x2_hornkb_given_val_content()
    test_2x2_hornkb_less_content()
    test_2x2_hornkb_cell_uniqueness_rules()
    test_2x2_hornkb_row_uniqueness_rules()
    test_2x2_hornkb_inequality_rules()
    
    print("\n--- 4x4 Puzzle Tests ---")
    test_4x4_parser_returns_puzzle()
    test_4x4_puzzle_given_cells()
    test_4x4_puzzle_constraints()
    test_4x4_hornkb_generation()
    test_4x4_hornkb_clause_count()
    test_4x4_hornkb_facts()
    test_4x4_hornkb_given_val_content()
    test_4x4_hornkb_less_content()
    test_4x4_hornkb_less_irreflexivity()
    test_4x4_hornkb_less_asymmetry()
    test_4x4_hornkb_row_surjection()
    test_4x4_hornkb_col_surjection()
    test_4x4_hornkb_cell_existence()
    test_4x4_hornkb_inequality_lessh()
    test_4x4_hornkb_inequality_greaterh()
    
    print("\n=== All Horn KB integration tests passed! ===")
