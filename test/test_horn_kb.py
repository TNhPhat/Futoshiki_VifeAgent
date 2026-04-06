"""
Integration test: Parser -> Puzzle -> HornClauseGenerator -> HornClauseKnowledgeBase

Tests the Prolog-style Horn clause generation pipeline on 2x2 and 4x4 puzzles.

Axioms implemented in HornClauseGenerator (Prolog-style with variables):
    Facts (Ground):
        A9  - Given clues: Val(i,j,v) for pre-filled cells
        A11 - Less ground truth: Less(a,b) for all a < b
        Diff - Difference facts: Diff(a,b) for all a != b
    
    Rules (Variable-based):
        A2  - Cell uniqueness: Val(I,J,V2) ∧ Diff(V1,V2) => ~Val(I,J,V1)
        A3  - Row uniqueness: Val(I,J2,V) ∧ Diff(J1,J2) => ~Val(I,J1,V)
        A4  - Column uniqueness: Val(I2,J,V) ∧ Diff(I1,I2) => ~Val(I1,J,V)
        A15 - Less asymmetry: Less(V1,V2) => ~Less(V2,V1)
        A16 - Inequality contrapositive: Val(cell2,V2) ∧ ~Less(V1,V2) => ~Val(cell1,V1)

Rule counts for Prolog-style KB:
    - 1 cell uniqueness rule (with variables)
    - 1 row uniqueness rule (with variables)
    - 1 column uniqueness rule (with variables)
    - 1 less asymmetry rule (with variables)
    - 1 inequality rule per constraint (with ground cells, variable values)
"""

import os
import sys
from math import comb

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.parser import Parser
from fol.horn_generator import HornClauseGenerator
from fol.horn_kb import HornClauseKnowledgeBase, HornClause
from fol.predicates import Val, Less, Diff


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
    """Calculate expected number of ground facts (A9 + A11 + Diff)."""
    a9 = num_given              # Given clue facts
    a11 = comb(n, 2)            # Less(a,b) for a < b
    # Diff facts: for indices 0..N-1 and values 1..N
    diff_indices = n * (n - 1)  # Diff(i,j) for i != j, indices 0..N-1
    diff_values = n * (n - 1)   # Diff(v1,v2) for v1 != v2, values 1..N
    return a9 + a11 + diff_indices + diff_values


def expected_rule_count(num_h_constraints: int, num_v_constraints: int) -> int:
    """Calculate expected number of Prolog-style rules."""
    # Core variable-based rules (constant count regardless of N)
    a2 = 1   # Cell uniqueness (1 rule with variables)
    a3 = 1   # Row uniqueness (1 rule with variables)
    a4 = 1   # Column uniqueness (1 rule with variables)
    a15 = 1  # Less asymmetry (1 rule with variables)
    
    # A16: 1 rule per constraint (ground cells, variable values)
    a16 = num_h_constraints + num_v_constraints
    
    return a2 + a3 + a4 + a15 + a16


# ---------------------------------------------------------------------------
# Expected values for 4x4
# ---------------------------------------------------------------------------

N_4X4 = 4
GIVEN_CELLS_4X4 = [(0, 0, 1)]
H_CONSTRAINTS_4X4 = 1  # LessH at (0,0)
V_CONSTRAINTS_4X4 = 0  # None


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
    expected_rules = expected_rule_count(H_CONSTRAINTS_2X2, V_CONSTRAINTS_2X2)
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
    """Cell uniqueness rule exists with variables: Val(i,j,v2) ∧ Diff(v1,v2) => ~Val(i,j,v1)."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for Prolog-style cell uniqueness rule with variables
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val("i", "j", "v1")
    expected_body = [Val("i", "j", "v2"), Diff("v1", "v2")]
    
    found = any(
        c.head == expected_head and len(c.body) == 2 and
        c.body[0] == expected_body[0] and c.body[1] == expected_body[1]
        for c in val_clauses
    )
    assert found, f"Expected cell uniqueness rule with variables"
    print(f"  [PASS] Cell uniqueness rule exists (Prolog-style)")


def test_2x2_hornkb_row_uniqueness_rules():
    """Row uniqueness rule exists with variables: Val(i,j2,v) ∧ Diff(j1,j2) => ~Val(i,j1,v)."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for Prolog-style row uniqueness rule
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val("i", "j1", "v")
    expected_body = [Val("i", "j2", "v"), Diff("j1", "j2")]
    
    found = any(
        c.head == expected_head and len(c.body) == 2 and
        c.body[0] == expected_body[0] and c.body[1] == expected_body[1]
        for c in val_clauses
    )
    assert found, f"Expected row uniqueness rule with variables"
    print(f"  [PASS] Row uniqueness rule exists (Prolog-style)")


def test_2x2_hornkb_inequality_rules():
    """Inequality contrapositive rules exist for LessH constraint with variable values."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # LessH at (0,0): cell(0,0) < cell(0,1)
    # Rule: Val(0,1,v2) ∧ ~Less(v1,v2) => ~Val(0,0,v1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val(0, 0, "v1")
    expected_body_1 = Val(0, 1, "v2")
    expected_body_2 = ~Less("v1", "v2")
    
    found = any(
        c.head == expected_head and len(c.body) == 2 and
        c.body[0] == expected_body_1 and c.body[1] == expected_body_2
        for c in val_clauses
    )
    assert found, f"Expected inequality rule with variable values"
    print(f"  [PASS] Inequality contrapositive rule exists (Prolog-style)")


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
    expected_rules = expected_rule_count(H_CONSTRAINTS_4X4, V_CONSTRAINTS_4X4)
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
    """Less irreflexivity is handled via NAF: ~Less(v,v) succeeds because Less(v,v) cannot be proven."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # In Prolog-style, we don't store ~Less(v,v) as facts
    # Instead, Less(v,v) fails because no such fact exists
    # NAF (Negation-as-Failure) handles this automatically
    
    # Verify Less(1,1) is NOT a fact
    less_clauses = kb.get_clause_for("Less")
    less_11 = any(
        c.is_fact() and c.head == Less(1, 1)
        for c in less_clauses
    )
    assert not less_11, "Less(1,1) should not be a fact (irreflexivity via NAF)"
    print(f"  [PASS] Less irreflexivity handled via NAF")


def test_4x4_hornkb_less_asymmetry():
    """Less asymmetry rule with variables: Less(v1,v2) => ~Less(v2,v1)."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    less_clauses = kb.get_clause_for("Less")
    
    # Prolog-style rule with variables
    expected_head = ~Less("v2", "v1")
    expected_body = Less("v1", "v2")
    
    found = any(
        c.head == expected_head and len(c.body) == 1 and c.body[0] == expected_body
        for c in less_clauses
    )
    assert found, f"Expected less asymmetry rule with variables"
    print(f"  [PASS] Less asymmetry rule exists (Prolog-style)")


def test_4x4_hornkb_column_uniqueness():
    """Column uniqueness rule with variables: Val(i2,j,v) ∧ Diff(i1,i2) => ~Val(i1,j,v)."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val("i1", "j", "v")
    expected_body = [Val("i2", "j", "v"), Diff("i1", "i2")]
    
    found = any(
        c.head == expected_head and len(c.body) == 2 and
        c.body[0] == expected_body[0] and c.body[1] == expected_body[1]
        for c in val_clauses
    )
    assert found, f"Expected column uniqueness rule with variables"
    print(f"  [PASS] Column uniqueness rule exists (Prolog-style)")


def test_4x4_hornkb_diff_facts():
    """Diff facts exist for indices and values to enable Prolog-style inequality."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    diff_clauses = kb.get_clause_for("Diff")
    diff_facts = [c for c in diff_clauses if c.is_fact()]
    
    # For 4x4: indices 0..3 and values 1..4
    # Diff for indices: 4 * 3 = 12 facts
    # Diff for values: 4 * 3 = 12 facts
    expected_count = N_4X4 * (N_4X4 - 1) * 2  # 24
    assert len(diff_facts) == expected_count, \
        f"Expected {expected_count} Diff facts, got {len(diff_facts)}"
    
    # Verify Diff(0,1) and Diff(1,2) are present
    assert any(c.head == Diff(0, 1) for c in diff_facts), "Expected Diff(0,1)"
    assert any(c.head == Diff(1, 2) for c in diff_facts), "Expected Diff(1,2)"
    
    print(f"  [PASS] Diff facts present ({len(diff_facts)} facts)")


def test_4x4_hornkb_row_uniqueness():
    """Row uniqueness rule with variables exists."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val("i", "j1", "v")
    expected_body = [Val("i", "j2", "v"), Diff("j1", "j2")]
    
    found = any(
        c.head == expected_head and len(c.body) == 2 and
        c.body[0] == expected_body[0] and c.body[1] == expected_body[1]
        for c in val_clauses
    )
    assert found, f"Expected row uniqueness rule with variables"
    print(f"  [PASS] Row uniqueness rule exists (Prolog-style)")


def test_4x4_hornkb_inequality_lessh():
    """Inequality contrapositive rules exist for LessH constraint with variable values."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # LessH at (0,0): cell(0,0) < cell(0,1)
    # Prolog-style rule: Val(0,1,v2) ∧ ~Less(v1,v2) => ~Val(0,0,v1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val(0, 0, "v1")
    expected_body_1 = Val(0, 1, "v2")
    expected_body_2 = ~Less("v1", "v2")
    
    found = any(
        c.head == expected_head and len(c.body) == 2 and
        c.body[0] == expected_body_1 and c.body[1] == expected_body_2
        for c in val_clauses
    )
    assert found, f"Expected LessH inequality rule with variables"
    print(f"  [PASS] LessH contrapositive rule exists (Prolog-style)")


def test_4x4_hornkb_inequality_greaterh():
    """Inequality contrapositive rules exist for GreaterH constraint with variable values."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # GreaterH at (1,2): cell(1,2) > cell(1,3)
    # Prolog-style rule: Val(1,3,v2) ∧ ~Less(v2,v1) => ~Val(1,2,v1)
    val_clauses = kb.get_clause_for("Val")
    expected_head = ~Val(1, 2, "v1")
    expected_body_1 = Val(1, 3, "v2")
    expected_body_2 = ~Less("v2", "v1")
    
    found = any(
        c.head == expected_head and len(c.body) == 2 and
        c.body[0] == expected_body_1 and c.body[1] == expected_body_2
        for c in val_clauses
    )
    assert found, f"Expected GreaterH inequality rule with variables"
    print(f"  [PASS] GreaterH contrapositive rule exists (Prolog-style)")


# ===========================================================================
# Runner
# ===========================================================================


if __name__ == "__main__":
    print("=== Integration: Parser -> Puzzle -> HornClauseKnowledgeBase (Prolog-style) ===\n")
    
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
    test_4x4_hornkb_column_uniqueness()
    test_4x4_hornkb_diff_facts()
    test_4x4_hornkb_row_uniqueness()
    test_4x4_hornkb_inequality_lessh()
    
    print("\n=== All Horn KB integration tests passed! ===")
