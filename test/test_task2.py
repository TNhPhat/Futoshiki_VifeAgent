"""Verification script for kb.py and cnf_generator.py (Task 2)."""

import sys
import os

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import numpy as np
from math import comb
from fol.predicates import Literal, Val, Less
from fol.kb import CNFClauseKnowledgeBase
from fol.cnf_generator import CNFGenerator
from fol.axioms import Axioms
from core.puzzle import Puzzle
from constraints.inequality_constraint import InequalityConstraint


# ==================================================================
# Helpers
# ==================================================================


def make_empty_puzzle(N: int) -> Puzzle:
    """Create an NxN puzzle with no givens and no constraints."""
    return Puzzle(
        N=N,
        grid=np.zeros((N, N), dtype=int),
        h_constraints=[],
        v_constraints=[],
    )


def make_test_puzzle(N: int) -> Puzzle:
    """
    Create a 4x4 test puzzle with known constraints.

    - Cell (0,0) = 1, Cell (1,1) = 2 (givens)
    - h_constraint (0,0) → LessH:    cell(0,0) < cell(0,1)
    - h_constraint (1,2) → GreaterH: cell(1,2) > cell(1,3)
    - v_constraint (0,1) → LessV:    cell(0,1) < cell(1,1)
    - v_constraint (2,0) → GreaterV: cell(2,0) > cell(3,0)
    """
    grid = np.zeros((N, N), dtype=int)
    grid[0, 0] = 1
    grid[1, 1] = 2

    return Puzzle(
        N=N,
        grid=grid,
        h_constraints=[
            InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction="<"),
            InequalityConstraint(cell1=(1, 2), cell2=(1, 3), direction=">"),
        ],
        v_constraints=[
            InequalityConstraint(cell1=(0, 1), cell2=(1, 1), direction="<"),
            InequalityConstraint(cell1=(2, 0), cell2=(3, 0), direction=">"),
        ],
    )


# ==================================================================
# Tests
# ==================================================================


def test_kb_basics():
    """Test CNFClauseKnowledgeBase add, len, repr, unit-fact extraction."""
    kb = CNFClauseKnowledgeBase()
    assert len(kb) == 0
    assert len(kb.facts) == 0

    # Add a multi-literal clause — should NOT add to facts
    kb.add_clause([Val(0, 0, 1), Val(0, 0, 2)])
    assert len(kb) == 1
    assert len(kb.facts) == 0

    # Add a unit clause — should auto-add to facts
    kb.add_clause([Val(0, 0, 1)])
    assert len(kb) == 2
    assert Val(0, 0, 1) in kb.facts

    # Double-add same unit → facts is a set, no duplication
    kb.add_clause([Val(0, 0, 1)])
    assert len(kb) == 3  # clause list grows
    assert len(kb.facts) == 1  # facts stays deduplicated

    print("  [PASS] KB basics")


def test_kb_queries():
    """Test get_unit_clauses and get_clauses_with."""
    kb = CNFClauseKnowledgeBase()
    kb.add_clause([Val(0, 0, 1)])
    kb.add_clause([Val(0, 0, 1), Val(0, 0, 2)])
    kb.add_clause([~Val(0, 0, 1), ~Val(0, 0, 2)])
    kb.add_clause([Less(1, 2)])

    units = kb.get_unit_clauses()
    assert len(units) == 2  # Val(0,0,1) and Less(1,2)

    # Clauses containing Val(0,0,1) — appears in first two clauses
    matching = kb.get_clauses_with(Val(0, 0, 1))
    assert len(matching) == 2

    # Clauses containing ~Val(0,0,1) — appears in third clause
    matching_neg = kb.get_clauses_with(~Val(0, 0, 1))
    assert len(matching_neg) == 1

    print("  [PASS] KB queries")


def test_kb_repr():
    """Test repr output."""
    kb = CNFClauseKnowledgeBase()
    kb.add_clause([Val(0, 0, 1)])
    kb.add_clause([Less(1, 2)])
    r = repr(kb)
    assert "clauses=2" in r
    assert "facts=2" in r
    print("  [PASS] KB repr")


def test_kb_add_clauses_bulk():
    """Test add_clauses bulk method."""
    kb = CNFClauseKnowledgeBase()
    clauses = [[Val(0, 0, v)] for v in range(1, 5)]
    kb.add_clauses(clauses)
    assert len(kb) == 4
    assert len(kb.facts) == 4
    print("  [PASS] KB add_clauses bulk")


def test_generate_empty_puzzle():
    """
    Test CNFGenerator.generate on an empty 4x4 puzzle.

    Expected clause count with no givens/constraints:
        A1=16, A2=96, A3=96, A4=96,
        A5-A8=0, A9=0, A10=0,
        A11=6, A12=16, A13=16, A14=4, A15=6, A16=0
        Total = 352
    """
    N = 4
    puzzle = make_empty_puzzle(N)
    kb = CNFGenerator.generate(puzzle)

    expected = (
        N * N              # A1:  16
        + N * N * comb(N, 2)  # A2:  96
        + N * comb(N, 2) * N  # A3:  96
        + N * comb(N, 2) * N  # A4:  96
        + 0                # A5-A8: no constraints
        + 0                # A9:  no givens
        + 0                # A10: no-op
        + comb(N, 2)       # A11: 6
        + N * N            # A12: 16
        + N * N            # A13: 16
        + N                # A14: 4
        + comb(N, 2)       # A15: 6
        + 0                # A16: no constraints
    )
    assert expected == 352, f"Expected formula = {expected}"
    assert len(kb) == expected, (
        f"Empty 4x4: {len(kb)} clauses != {expected}"
    )

    # Facts should include Less ground truth (6) + irreflexivity (4)
    # = 10 unit-clause facts
    expected_facts = comb(N, 2) + N  # 6 + 4 = 10
    assert len(kb.facts) == expected_facts, (
        f"Facts: {len(kb.facts)} != {expected_facts}"
    )

    print(f"  [PASS] Empty puzzle: {len(kb)} clauses, {len(kb.facts)} facts")


def test_generate_ground_kb_from_size():
    """CNFGenerator.generate_ground_kb(N) matches empty-puzzle generation."""
    N = 4
    kb_from_size = CNFGenerator.generate_ground_kb(N)
    kb_from_empty = CNFGenerator.generate(make_empty_puzzle(N))

    assert len(kb_from_size) == len(kb_from_empty), (
        f"Ground KB: {len(kb_from_size)} clauses != {len(kb_from_empty)}"
    )
    assert kb_from_size.facts == kb_from_empty.facts, (
        "Ground KB facts differ from empty-puzzle generation"
    )
    assert kb_from_size.get_clauses() == kb_from_empty.get_clauses(), (
        "Ground KB clauses differ from empty-puzzle generation"
    )

    print(
        "  [PASS] generate_ground_kb(N) matches generate(empty puzzle)"
    )


def test_generate_test_puzzle():
    """
    Test CNFGenerator.generate on the test puzzle with givens + constraints.
    """
    N = 4
    puzzle = make_test_puzzle(N)
    kb = CNFGenerator.generate(puzzle)

    # Base clauses (same as empty)
    base = 352

    # Added by constraints:
    #   A5: 1 LessV  constraint → N² = 16 clauses
    #   A6: 1 GreaterV constraint → N² = 16 clauses
    #   A7: 1 LessH  constraint → N² = 16 clauses
    #   A8: 1 GreaterH constraint → N² = 16 clauses
    #   A9: 2 givens → 2 unit clauses
    #   A16: 4 constraints x N(N+1)/2 = 4 x 10 = 40 clauses
    extra = 16 + 16 + 16 + 16 + 2 + 40
    expected = base + extra  # 352 + 106 = 458
    assert len(kb) == expected, (
        f"Test puzzle: {len(kb)} clauses != {expected}"
    )

    # Facts: 10 base (Less + irrefl) + 2 given clue unit clauses = 12
    assert Val(0, 0, 1) in kb.facts, "Given Val(0,0,1) not in facts"
    assert Val(1, 1, 2) in kb.facts, "Given Val(1,1,2) not in facts"
    assert Less(1, 2) in kb.facts, "Less(1,2) not in facts"
    assert Less(3, 4) in kb.facts, "Less(3,4) not in facts"
    assert ~Less(1, 1) in kb.facts, "~Less(1,1) not in facts"

    expected_facts = comb(N, 2) + N + 2  # 6 + 4 + 2 = 12
    assert len(kb.facts) == expected_facts, (
        f"Facts: {len(kb.facts)} != {expected_facts}"
    )

    print(f"  [PASS] Test puzzle: {len(kb)} clauses, {len(kb.facts)} facts")


def test_generate_preserves_axiom_breakdown():
    """Verify each axiom's contribution independently matches the KB total."""
    N = 4
    puzzle = make_test_puzzle(N)

    # Compute expected counts per axiom
    counts = {
        "A1": len(Axioms.a1_cell_existence(N)),
        "A2": len(Axioms.a2_cell_uniqueness(N)),
        "A3": len(Axioms.a3_row_uniqueness(N)),
        "A4": len(Axioms.a4_col_uniqueness(N)),
        "A5": len(Axioms.a5_vertical_less(N, puzzle)),
        "A6": len(Axioms.a6_vertical_greater(N, puzzle)),
        "A7": len(Axioms.a7_horizontal_less(N, puzzle)),
        "A8": len(Axioms.a8_horizontal_greater(N, puzzle)),
        "A9": len(Axioms.a9_given_clues(N, puzzle)),
        "A10": len(Axioms.a10_domain_bound()),
        "A11": len(Axioms.a11_less_ground_truth(N)),
        "A12": len(Axioms.a12_row_surjection(N)),
        "A13": len(Axioms.a13_col_surjection(N)),
        "A14": len(Axioms.a14_less_irreflexivity(N)),
        "A15": len(Axioms.a15_less_asymmetry(N)),
        "A16": len(Axioms.a16_inequality_contrapositive(N, puzzle)),
    }

    total_from_axioms = sum(counts.values())
    kb = CNFGenerator.generate(puzzle)

    assert len(kb) == total_from_axioms, (
        f"KB has {len(kb)} clauses but axiom sum = {total_from_axioms}"
    )

    print(f"  [PASS] Axiom breakdown matches KB total ({total_from_axioms})")
    for name, count in counts.items():
        print(f"         {name}: {count}")


# ==================================================================
# Main
# ==================================================================

if __name__ == "__main__":
    print("=== Task 2 Tests ===\n")

    print("CNFClauseKnowledgeBase:")
    test_kb_basics()
    test_kb_queries()
    test_kb_repr()
    test_kb_add_clauses_bulk()

    print("\nCNFGenerator — empty 4x4:")
    test_generate_empty_puzzle()
    test_generate_ground_kb_from_size()

    print("\nCNFGenerator — test puzzle 4x4:")
    test_generate_test_puzzle()

    print("\nAxiom breakdown verification:")
    test_generate_preserves_axiom_breakdown()

    print("\n=== All Task 2 tests passed! ===")
