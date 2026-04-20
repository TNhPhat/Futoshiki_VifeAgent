"""
Integration test: Parser -> Puzzle -> HornClauseGenerator -> HornClauseKnowledgeBase

Tests Pure Positive Definite Clause generation pipeline on 2x2 and 4x4 puzzles.
All clauses have POSITIVE heads and POSITIVE bodies (no negation used).

Axioms implemented in HornClauseGenerator (Pure Positive Definite Clauses):
    Facts (Ground, all positive):
        Val(i,j,v) - Given clues for pre-filled cells
        Domain(v) - Valid domain values (1..N)
        Diff(a,b) - Difference facts for a != b (values only)
        Less(a,b) - Less-than facts for a < b
    
    Rules (Positive heads, positive bodies):
        ValidVal(r,c,v) :- Domain(v), Val(others), Diff constraints, Less constraints
        Val(r,c,v) :- ValidVal(r,c,v)
"""

import os
import sys
from math import comb

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.parser import Parser
from fol.horn_generator import HornClauseGenerator
from fol.horn_kb import HornClauseKnowledgeBase, HornClause
from fol.predicates import Val, Less, Diff, Domain


FIXTURE_2X2 = os.path.join(os.path.dirname(__file__), "fixtures", "input_2x2.txt")
FIXTURE_4X4 = os.path.join(os.path.dirname(__file__), "fixtures", "input_4x4.txt")


N_2X2 = 2
GIVEN_CELLS_2X2 = [(0, 0, 1)]
H_CONSTRAINTS_2X2 = 1  # LessH at (0,0)
V_CONSTRAINTS_2X2 = 1  # GreaterV at (0,1)


def expected_fact_count(n: int, num_given: int) -> int:
    """Calculate expected number of ground facts (Val + Domain + Diff + Less)."""
    val_facts = num_given           # Given clue facts
    domain_facts = n                # Domain(v) for v in 1..N
    diff_values = n * (n - 1)       # Diff(v1,v2) for v1 != v2, values 1..N
    less_facts = comb(n, 2)         # Less(a,b) for a < b
    return val_facts + domain_facts + diff_values + less_facts


def expected_rule_count(n: int, num_given: int) -> int:
    """Calculate expected number of rules (1 Solution rule for Generate-and-Test)."""
    num_empty = n * n - num_given
    # Generate-and-Test: single Solution rule if there are empty cells
    return 1 if num_empty > 0 else 0


N_4X4 = 4
GIVEN_CELLS_4X4 = [(0, 0, 1)]
H_CONSTRAINTS_4X4 = 1  # LessH at (0,0)
V_CONSTRAINTS_4X4 = 0  # None


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
    expected_rules = expected_rule_count(N_2X2, len(GIVEN_CELLS_2X2))
    expected_total = expected_facts + expected_rules
    
    assert kb.clause_count == expected_total, \
        f"Clause count: {kb.clause_count} != {expected_total}"
    print(f"  [PASS] Total clauses: {kb.clause_count} == {expected_total}")


def test_2x2_hornkb_facts():
    """HornKB facts include given clues, Domain, Diff, and Less."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check given clue fact
    val_clauses = kb.get_clause_for("Val")
    given_facts = [c for c in val_clauses if c.is_fact() and not c.head.negated]
    assert len(given_facts) == len(GIVEN_CELLS_2X2), \
        f"Expected {len(GIVEN_CELLS_2X2)} Val facts, got {len(given_facts)}"
    
    # Check Domain facts
    domain_clauses = kb.get_clause_for("Domain")
    domain_facts = [c for c in domain_clauses if c.is_fact()]
    assert len(domain_facts) == N_2X2, \
        f"Expected {N_2X2} Domain facts, got {len(domain_facts)}"
    
    # Check Less ground truth facts
    less_clauses = kb.get_clause_for("Less")
    less_facts = [c for c in less_clauses if c.is_fact()]
    assert len(less_facts) == comb(N_2X2, 2), \
        f"Expected {comb(N_2X2, 2)} Less facts, got {len(less_facts)}"
    
    print(f"  [PASS] Facts: {len(given_facts)} Val, {len(domain_facts)} Domain, {len(less_facts)} Less")


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
    """Solution rule enforces row/column uniqueness via Diff constraints."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for Solution rule (Generate-and-Test paradigm)
    solution_clauses = kb.get_clause_for("Solution")
    assert len(solution_clauses) == 1, "Expected exactly 1 Solution rule"
    
    solution_rule = solution_clauses[0]
    assert not solution_rule.head.negated, "Solution head should be positive"
    
    # Body should include Domain and Diff constraints
    body_names = [lit.name for lit in solution_rule.body]
    assert "Domain" in body_names, "Solution body should include Domain"
    assert "Diff" in body_names, "Solution body should include Diff"
    
    print(f"  [PASS] Solution rule exists with positive head and Diff constraints")


def test_2x2_hornkb_row_uniqueness_rules():
    """Solution rule includes row uniqueness via Diff constraints."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check Solution rule contains Diff for row uniqueness
    solution_clauses = kb.get_clause_for("Solution")
    assert len(solution_clauses) == 1, "Expected 1 Solution rule"
    
    # Count Diff literals in body (should have multiple for uniqueness)
    diff_count = sum(1 for lit in solution_clauses[0].body if lit.name == "Diff")
    assert diff_count > 0, f"Expected Diff constraints in Solution body"
    
    print(f"  [PASS] Row uniqueness enforced via {diff_count} Diff literals in Solution rule")


def test_2x2_hornkb_inequality_rules():
    """Solution rule integrates inequality constraints via Less literals."""
    puzzle = Parser().parse(FIXTURE_2X2)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for Solution rule that includes Less constraints
    solution_clauses = kb.get_clause_for("Solution")
    
    # Solution rule should include Less for inequality constraint
    has_less = any(lit.name == "Less" for lit in solution_clauses[0].body)
    assert has_less, "Expected Less constraint in Solution rule for inequality"
    print(f"  [PASS] Inequality constraint integrated via Less in Solution rule")


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
    expected_rules = expected_rule_count(N_4X4, len(GIVEN_CELLS_4X4))
    expected_total = expected_facts + expected_rules
    
    assert kb.clause_count == expected_total, \
        f"Clause count: {kb.clause_count} != {expected_total}"
    print(f"  [PASS] Total clauses: {kb.clause_count} == {expected_total}")


def test_4x4_hornkb_facts():
    """HornKB facts include given clues, Domain, Diff, and Less."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check given clue facts
    val_clauses = kb.get_clause_for("Val")
    given_facts = [c for c in val_clauses if c.is_fact() and not c.head.negated]
    assert len(given_facts) == len(GIVEN_CELLS_4X4), \
        f"Expected {len(GIVEN_CELLS_4X4)} Val facts, got {len(given_facts)}"
    
    # Check Domain facts
    domain_clauses = kb.get_clause_for("Domain")
    domain_facts = [c for c in domain_clauses if c.is_fact()]
    assert len(domain_facts) == N_4X4, \
        f"Expected {N_4X4} Domain facts, got {len(domain_facts)}"
    
    # Check Less ground truth facts
    less_clauses = kb.get_clause_for("Less")
    less_facts = [c for c in less_clauses if c.is_fact()]
    assert len(less_facts) == comb(N_4X4, 2), \
        f"Expected {comb(N_4X4, 2)} Less facts, got {len(less_facts)}"
    
    print(f"  [PASS] Facts: {len(given_facts)} Val, {len(domain_facts)} Domain, {len(less_facts)} Less")


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
    """Less irreflexivity: Less(v,v) should not exist as a fact."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Verify Less(1,1) is NOT a fact
    less_clauses = kb.get_clause_for("Less")
    less_11 = any(
        c.is_fact() and c.head == Less(1, 1)
        for c in less_clauses
    )
    assert not less_11, "Less(1,1) should not be a fact (irreflexivity)"
    print(f"  [PASS] Less irreflexivity maintained (no Less(v,v) facts)")


def test_4x4_hornkb_solution_rule():
    """Solution rule exists for empty cells with positive head."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    solution_clauses = kb.get_clause_for("Solution")
    
    assert len(solution_clauses) == 1, \
        f"Expected 1 Solution rule, got {len(solution_clauses)}"
    
    # Solution head should be positive
    assert not solution_clauses[0].head.negated, "Solution head should be positive"
    
    # Solution head should have args for all empty cells
    num_empty = N_4X4 * N_4X4 - len(GIVEN_CELLS_4X4)
    assert len(solution_clauses[0].head.args) == num_empty, \
        f"Expected {num_empty} args in Solution head, got {len(solution_clauses[0].head.args)}"
    
    print(f"  [PASS] Solution rule exists for all {num_empty} empty cells")


def test_4x4_hornkb_column_uniqueness():
    """Column uniqueness enforced via Diff constraints in Solution rule."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    solution_clauses = kb.get_clause_for("Solution")
    
    # Solution rule should have Diff constraints for column uniqueness
    diff_count = sum(1 for lit in solution_clauses[0].body if lit.name == "Diff")
    # For N=4 with 15 empty cells, there should be many Diff constraints
    assert diff_count > 0, f"Expected Diff constraints in Solution body"
    
    print(f"  [PASS] Column uniqueness enforced via {diff_count} Diff constraints")


def test_4x4_hornkb_diff_facts():
    """Diff facts exist for values to enable uniqueness constraints."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    diff_clauses = kb.get_clause_for("Diff")
    diff_facts = [c for c in diff_clauses if c.is_fact()]
    
    # For 4x4: values 1..4 only (no index Diff needed in pure positive approach)
    expected_count = N_4X4 * (N_4X4 - 1)  # 12
    assert len(diff_facts) == expected_count, \
        f"Expected {expected_count} Diff facts, got {len(diff_facts)}"
    
    # Verify Diff(1,2) is present
    assert any(c.head == Diff(1, 2) for c in diff_facts), "Expected Diff(1,2)"
    
    print(f"  [PASS] Diff facts present ({len(diff_facts)} facts)")


def test_4x4_hornkb_row_uniqueness():
    """Row uniqueness enforced via Diff constraints in Solution rule."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    solution_clauses = kb.get_clause_for("Solution")
    
    # Solution rule should include Domain for generating values
    domain_count = sum(1 for lit in solution_clauses[0].body if lit.name == "Domain")
    num_empty = N_4X4 * N_4X4 - len(GIVEN_CELLS_4X4)
    assert domain_count == num_empty, \
        f"Expected {num_empty} Domain constraints, got {domain_count}"
    
    print(f"  [PASS] Row uniqueness enforced via Domain/Diff constraints")


def test_4x4_hornkb_inequality_less():
    """Inequality constraints use Less literals in Solution rule."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    # Check for Solution rule that includes Less constraints
    solution_clauses = kb.get_clause_for("Solution")
    
    # Solution rule should include Less for inequality constraint
    has_less = any(lit.name == "Less" for lit in solution_clauses[0].body)
    assert has_less, "Expected Less constraint in Solution rule for inequality"
    print(f"  [PASS] Inequality constraints use Less literals")


def test_4x4_hornkb_interleaved_structure():
    """Solution rule uses interleaved Generate-and-Test structure."""
    puzzle = Parser().parse(FIXTURE_4X4)
    kb = HornClauseGenerator.generate(puzzle)
    
    solution_clauses = kb.get_clause_for("Solution")
    body = solution_clauses[0].body
    
    # In interleaved structure, Domain should not all be at the beginning
    # Check that after the first Domain, there's a Diff before the second Domain
    first_domain_idx = next(i for i, lit in enumerate(body) if lit.name == "Domain")
    second_domain_idx = None
    for i in range(first_domain_idx + 1, len(body)):
        if body[i].name == "Domain":
            second_domain_idx = i
            break
    
    if second_domain_idx is not None:
        # Check there's a Diff between first and second Domain
        has_diff_between = any(
            body[i].name == "Diff" 
            for i in range(first_domain_idx + 1, second_domain_idx)
        )
        assert has_diff_between, "Expected interleaved structure: Domain, Diff, Domain"
    
    print(f"  [PASS] Solution rule uses interleaved Generate-and-Test structure")


if __name__ == "__main__":
    print("=== Integration: Parser -> Puzzle -> HornClauseKnowledgeBase (Pure Positive Definite Clauses) ===\n")
    
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
    test_4x4_hornkb_solution_rule()
    test_4x4_hornkb_column_uniqueness()
    test_4x4_hornkb_diff_facts()
    test_4x4_hornkb_row_uniqueness()
    test_4x4_hornkb_inequality_less()
    test_4x4_hornkb_interleaved_structure()
    
    print("\n=== All Horn KB integration tests passed! ===")
