"""Quick verification script for predicates.py and axioms.py."""

import sys
import os

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import numpy as np
from fol.predicates import Literal, Val, Given, Less, LessH
from fol.axioms import Axioms
from core.puzzle import Puzzle
from constraints.inequality_constraint import InequalityConstraint


def test_literal_basics():
    """Test Literal creation, negation, hashability, repr."""
    lit = Val(0, 0, 1)
    assert lit.name == "Val"
    assert lit.args == (0, 0, 1)
    assert lit.negated is False
    assert repr(lit) == "Val(0,0,1)"

    neg = ~lit
    assert neg.negated is True
    assert repr(neg) == "~Val(0,0,1)"

    # Double negation restores original
    assert ~~lit == lit

    # Hashability — can be added to sets
    s = {lit, neg, lit}
    assert len(s) == 2  # lit appears once, neg once

    print("  [PASS] Literal basics")


def test_factory_functions():
    """Test all 7 factory functions produce correct literals."""
    assert Val(1, 2, 3).name == "Val"
    assert Val(1, 2, 3).args == (1, 2, 3)

    assert Given(0, 1, 4).name == "Given"
    assert Given(0, 1, 4).args == (0, 1, 4)

    assert LessH(0, 0).name == "LessH"
    assert LessH(0, 0).args == (0, 0)

    assert Less(1, 2).name == "Less"
    assert Less(1, 2).args == (1, 2)

    print("  [PASS] Factory functions")


def make_test_puzzle(N: int) -> Puzzle:
    """
    Create a small test puzzle with known constraints.

    4x4 grid with:
      - Cell (0,0) = 1 (given)
      - Cell (1,1) = 2 (given)
      - h_constraint (0,0) = 1  → cell(0,0) < cell(0,1)
      - h_constraint (1,2) = -1 → cell(1,2) > cell(1,3)
      - v_constraint (0,1) = 1  → cell(0,1) < cell(1,1)
      - v_constraint (2,0) = -1 → cell(2,0) > cell(3,0)
    """
    grid = np.zeros((N, N), dtype=int)
    grid[0, 0] = 1
    grid[1, 1] = 2

    return Puzzle(
        N=N,
        grid=grid,
        h_constraints=[
            InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction="<"),  # LessH
            InequalityConstraint(cell1=(1, 2), cell2=(1, 3), direction=">"),  # GreaterH
        ],
        v_constraints=[
            InequalityConstraint(cell1=(0, 1), cell2=(1, 1), direction="<"),  # LessV
            InequalityConstraint(cell1=(2, 0), cell2=(3, 0), direction=">"),  # GreaterV
        ],
    )


def test_pure_axiom_counts():
    """Test clause counts for axioms that only depend on N."""
    from math import comb
    N = 4

    # A1: N^2 clauses, each with N literals
    a1 = Axioms.a1_cell_existence(N)
    assert len(a1) == N * N, f"A1: {len(a1)} != {N*N}"
    assert all(len(c) == N for c in a1)
    print(f"  [PASS] A1: {len(a1)} clauses")

    # A2: N^2 * C(N,2) clauses
    a2 = Axioms.a2_cell_uniqueness(N)
    expected = N * N * comb(N, 2)
    assert len(a2) == expected, f"A2: {len(a2)} != {expected}"
    assert all(len(c) == 2 for c in a2)
    assert all(c[0].negated and c[1].negated for c in a2)
    print(f"  [PASS] A2: {len(a2)} clauses")

    # A3: N * C(N,2) * N clauses
    a3 = Axioms.a3_row_uniqueness(N)
    expected = N * comb(N, 2) * N
    assert len(a3) == expected, f"A3: {len(a3)} != {expected}"
    print(f"  [PASS] A3: {len(a3)} clauses")

    # A4: N * C(N,2) * N clauses
    a4 = Axioms.a4_col_uniqueness(N)
    expected = N * comb(N, 2) * N
    assert len(a4) == expected, f"A4: {len(a4)} != {expected}"
    print(f"  [PASS] A4: {len(a4)} clauses")

    # A11: C(N,2) unit clauses
    a11 = Axioms.a11_less_ground_truth(N)
    expected = comb(N, 2)
    assert len(a11) == expected, f"A11: {len(a11)} != {expected}"
    assert all(len(c) == 1 for c in a11)
    print(f"  [PASS] A11: {len(a11)} clauses")

    # A12: N^2 clauses
    a12 = Axioms.a12_row_surjection(N)
    assert len(a12) == N * N, f"A12: {len(a12)} != {N*N}"
    print(f"  [PASS] A12: {len(a12)} clauses")

    # A13: N^2 clauses
    a13 = Axioms.a13_col_surjection(N)
    assert len(a13) == N * N, f"A13: {len(a13)} != {N*N}"
    print(f"  [PASS] A13: {len(a13)} clauses")

    # A14: N unit clauses
    a14 = Axioms.a14_less_irreflexivity(N)
    assert len(a14) == N, f"A14: {len(a14)} != {N}"
    print(f"  [PASS] A14: {len(a14)} clauses")

    # A15: C(N,2) clauses
    a15 = Axioms.a15_less_asymmetry(N)
    expected = comb(N, 2)
    assert len(a15) == expected, f"A15: {len(a15)} != {expected}"
    print(f"  [PASS] A15: {len(a15)} clauses")

    # A10: always empty
    a10 = Axioms.a10_domain_bound()
    assert len(a10) == 0
    print(f"  [PASS] A10: 0 clauses (no-op)")


def test_puzzle_axioms():
    """Test axioms that depend on puzzle data."""
    N = 4
    puzzle = make_test_puzzle(N)
    # A9: given clues — our test puzzle has 2 givens
    a9 = Axioms.a9_given_clues(N, puzzle)
    assert len(a9) == 2, f"A9: {len(a9)} != 2"
    # Check that the unit clauses are Val(0,0,1) and Val(1,1,2)
    unit_lits = {c[0] for c in a9}
    assert Val(0, 0, 1) in unit_lits
    assert Val(1, 1, 2) in unit_lits
    print(f"  [PASS] A9: {len(a9)} clauses")

    # A5: LessV — 1 constraint, N^2 clauses
    a5 = Axioms.a5_vertical_less(N, puzzle)
    assert len(a5) == N * N, f"A5: {len(a5)} != {N*N}"
    print(f"  [PASS] A5: {len(a5)} clauses")

    # A6: GreaterV — 1 constraint, N^2 clauses
    a6 = Axioms.a6_vertical_greater(N, puzzle)
    assert len(a6) == N * N, f"A6: {len(a6)} != {N*N}"
    print(f"  [PASS] A6: {len(a6)} clauses")

    # A7: LessH — 1 constraint, N^2 clauses
    a7 = Axioms.a7_horizontal_less(N, puzzle)
    assert len(a7) == N * N, f"A7: {len(a7)} != {N*N}"
    print(f"  [PASS] A7: {len(a7)} clauses")

    # A8: GreaterH — 1 constraint, N^2 clauses
    a8 = Axioms.a8_horizontal_greater(N, puzzle)
    assert len(a8) == N * N, f"A8: {len(a8)} != {N*N}"
    print(f"  [PASS] A8: {len(a8)} clauses")

    # A16: contrapositive for all 4 constraints
    a16 = Axioms.a16_inequality_contrapositive(N, puzzle)
    # LessH at (0,0): v1>=v2 pairs = N*(N+1)/2 = 10
    # GreaterH at (1,2): v1<=v2 pairs = N*(N+1)/2 = 10
    # LessV at (0,1): v1>=v2 pairs = 10
    # GreaterV at (2,0): v1<=v2 pairs = 10
    expected = 4 * (N * (N + 1) // 2)
    assert len(a16) == expected, f"A16: {len(a16)} != {expected}"
    print(f"  [PASS] A16: {len(a16)} clauses")


def test_a16_correctness():
    """Spot-check A16 clause content for LessH at (0,0)."""
    N = 4
    puzzle = make_test_puzzle(N)
    a16 = Axioms.a16_inequality_contrapositive(N, puzzle)

    # LessH at (0,0): should ban v1 >= v2
    # e.g. (v1=2, v2=1) should produce ~Val(0,0,2) ∨ ~Val(0,1,1)
    target = [~Val(0, 0, 2), ~Val(0, 1, 1)]
    found = any(c == target for c in a16)
    assert found, "A16: missing clause for LessH ban (2,1)"

    # (v1=1, v2=1) should also be banned (v1 >= v2)
    target2 = [~Val(0, 0, 1), ~Val(0, 1, 1)]
    found2 = any(c == target2 for c in a16)
    assert found2, "A16: missing clause for LessH ban (1,1)"

    # (v1=1, v2=2) should NOT be banned (v1 < v2)
    not_target = [~Val(0, 0, 1), ~Val(0, 1, 2)]
    not_found = any(c == not_target for c in a16)
    assert not not_found, "A16: incorrectly bans valid pair"

    print("  [PASS] A16 correctness spot-check")


if __name__ == "__main__":
    N = 4
    print(f"=== Testing with N={N} ===\n")

    print("Literal basics:")
    test_literal_basics()

    print("\nFactory functions:")
    test_factory_functions()

    print(f"\nPure axiom clause counts (N={N}):")
    test_pure_axiom_counts(N)

    puzzle = make_test_puzzle(N)
    print(f"\nPuzzle-dependent axioms (N={N}):")
    test_puzzle_axioms(N, puzzle)

    print(f"\nA16 correctness:")
    test_a16_correctness(N, puzzle)

    print(f"\n=== All tests passed! ===")
