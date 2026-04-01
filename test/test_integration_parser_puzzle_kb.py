"""
Integration test: Parser -> Puzzle -> KnowledgeBase pipeline.

Fixture: test/fixtures/input_3x3.txt
  N = 3
  Given cells : (0,0)=2, (1,2)=3, (2,1)=1
  h_constraints: LessH at (0,0), GreaterH at (2,1)
  v_constraints: LessV at (1,1)

Expected clause count (derived from axiom formulas, N=3):
  A1  cell existence      :  N^2            =  9
  A2  cell uniqueness     :  N^2 * C(N,2)   = 27
  A3  row uniqueness      :  N * C(N,2) * N = 27
  A4  col uniqueness      :  N * C(N,2) * N = 27
  A12 row surjection      :  N^2            =  9
  A13 col surjection      :  N^2            =  9
  A9  given clues         :  3 givens        =  3
  A10 domain bound        :  no-op           =  0
  A11 Less ground truth   :  C(N,2)          =  3
  A14 Less irreflexivity  :  N               =  3
  A15 Less asymmetry      :  C(N,2)          =  3
  A7  LessH   (0,0)       :  N^2             =  9
  A8  GreaterH (2,1)      :  N^2             =  9
  A5  LessV   (1,1)       :  N^2             =  9
  A6  GreaterV            :  0 constraints   =  0
  A16 contrapositives     :
        LessH   ban v1>=v2 : N*(N+1)/2       =  6
        GreaterH ban v1<=v2: N*(N+1)/2       =  6
        LessV   ban v1>=v2 : N*(N+1)/2       =  6
  Total                                      = 165

Expected facts (unit clauses):
  A9  : Val(0,0,2), Val(1,2,3), Val(2,1,1)  -> 3 positive
  A11 : Less(1,2), Less(1,3), Less(2,3)      -> 3 positive
  A14 : ~Less(1,1), ~Less(2,2), ~Less(3,3)  -> 3 negative
  Total = 9 facts
"""

import os
import sys
from math import comb

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.parser import Parser
from fol.cnf_generator import CNFGenerator
from fol.predicates import Val, Less

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "input_3x3.txt")

N = 3
GIVEN_CELLS = [(0, 0, 2), (1, 2, 3), (2, 1, 1)]
EMPTY_CELLS = [
    (0, 1), (0, 2),
    (1, 0), (1, 1),
    (2, 0), (2, 2),
]

# Derived constants — kept here so test assertions are self-documenting
EXPECTED_CLAUSE_COUNT = (
    N * N                    # A1
    + N * N * comb(N, 2)     # A2
    + N * comb(N, 2) * N     # A3
    + N * comb(N, 2) * N     # A4
    + N * N                  # A12
    + N * N                  # A13
    + len(GIVEN_CELLS)       # A9
    + 0                      # A10 (no-op)
    + comb(N, 2)             # A11
    + N                      # A14
    + comb(N, 2)             # A15
    + N * N                  # A7  LessH at (0,0)
    + N * N                  # A8  GreaterH at (2,1)
    + N * N                  # A5  LessV at (1,1)
    + 0                      # A6  (no GreaterV)
    + N * (N + 1) // 2       # A16 LessH contrap
    + N * (N + 1) // 2       # A16 GreaterH contrap
    + N * (N + 1) // 2       # A16 LessV contrap
)  # = 165

EXPECTED_FACT_COUNT = (
    len(GIVEN_CELLS)   # A9:  Val facts
    + comb(N, 2)       # A11: Less(a,b) for a<b
    + N                # A14: ~Less(v,v)
)  # = 9


# ===========================================================================
# Stage 1: Parser -> Puzzle
# ===========================================================================


def test_parser_returns_puzzle():
    """Parser.parse() succeeds and returns a Puzzle without raising."""
    puzzle = Parser().parse(FIXTURE)
    assert puzzle is not None
    print("  [PASS] Parser returns a Puzzle")


def test_puzzle_grid_size():
    """Puzzle.N matches the N declared in the file."""
    puzzle = Parser().parse(FIXTURE)
    assert puzzle.N == N, f"Expected N={N}, got {puzzle.N}"
    print(f"  [PASS] puzzle.N == {N}")


def test_puzzle_array_shapes():
    """grid, h_constraints, v_constraints have the correct numpy shapes."""
    puzzle = Parser().parse(FIXTURE)
    assert puzzle.grid.shape == (N, N), \
        f"grid shape: {puzzle.grid.shape}"
    assert puzzle.h_constraints.shape == (N, N - 1), \
        f"h_constraints shape: {puzzle.h_constraints.shape}"
    assert puzzle.v_constraints.shape == (N - 1, N), \
        f"v_constraints shape: {puzzle.v_constraints.shape}"
    print("  [PASS] Array shapes correct")


def test_puzzle_given_cells():
    """get_given_cells() returns exactly the clues declared in the fixture."""
    puzzle = Parser().parse(FIXTURE)
    assert sorted(puzzle.get_given_cells()) == sorted(GIVEN_CELLS), \
        f"Given cells mismatch: {puzzle.get_given_cells()}"
    print(f"  [PASS] Given cells: {sorted(puzzle.get_given_cells())}")


def test_puzzle_empty_cells():
    """get_empty_cells() returns all cells not declared as clues."""
    puzzle = Parser().parse(FIXTURE)
    assert sorted(puzzle.get_empty_cells()) == sorted(EMPTY_CELLS), \
        f"Empty cells mismatch: {puzzle.get_empty_cells()}"
    print(f"  [PASS] Empty cells: {sorted(puzzle.get_empty_cells())}")


def test_puzzle_is_given():
    """is_given() is True for each clue cell and False for empty cells."""
    puzzle = Parser().parse(FIXTURE)
    for i, j, _ in GIVEN_CELLS:
        assert puzzle.is_given(i, j), f"Expected is_given({i},{j}) = True"
    for i, j in EMPTY_CELLS:
        assert not puzzle.is_given(i, j), f"Expected is_given({i},{j}) = False"
    print("  [PASS] is_given() correct for all cells")


def test_puzzle_is_not_complete():
    """A puzzle with empty cells must not report is_complete()."""
    puzzle = Parser().parse(FIXTURE)
    assert not puzzle.is_complete()
    print("  [PASS] puzzle.is_complete() == False (has empty cells)")


def test_puzzle_h_constraints():
    """get_h_constraint() matches the fixture's horizontal constraints."""
    puzzle = Parser().parse(FIXTURE)
    assert puzzle.get_h_constraint(0, 0) == 1,  "LessH expected at (0,0)"
    assert puzzle.get_h_constraint(0, 1) == 0,  "No constraint at (0,1)"
    assert puzzle.get_h_constraint(2, 1) == -1, "GreaterH expected at (2,1)"
    assert puzzle.get_h_constraint(1, 0) == 0,  "No constraint at (1,0)"
    print("  [PASS] h_constraints match fixture")


def test_puzzle_v_constraints():
    """get_v_constraint() matches the fixture's vertical constraints."""
    puzzle = Parser().parse(FIXTURE)
    assert puzzle.get_v_constraint(1, 1) == 1, "LessV expected at (1,1)"
    assert puzzle.get_v_constraint(0, 0) == 0, "No constraint at (0,0)"
    assert puzzle.get_v_constraint(1, 0) == 0, "No constraint at (1,0)"
    print("  [PASS] v_constraints match fixture")


# ===========================================================================
# Stage 2: Puzzle -> KnowledgeBase
# ===========================================================================


def test_kb_total_clause_count():
    """CNFGenerator produces exactly the expected number of clauses."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    assert len(kb) == EXPECTED_CLAUSE_COUNT, \
        f"Clause count: {len(kb)} != {EXPECTED_CLAUSE_COUNT}"
    print(f"  [PASS] Total clauses: {len(kb)} == {EXPECTED_CLAUSE_COUNT}")


def test_kb_total_fact_count():
    """KB facts set has exactly the expected number of unit literals."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    assert len(kb.get_facts()) == EXPECTED_FACT_COUNT, \
        f"Fact count: {len(kb.get_facts())} != {EXPECTED_FACT_COUNT}"
    print(f"  [PASS] Total facts: {len(kb.get_facts())} == {EXPECTED_FACT_COUNT}")


def test_kb_given_clues_are_known():
    """Every given clue Val(i,j,v) must be a known fact (A9 unit clauses)."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    for i, j, v in GIVEN_CELLS:
        lit = Val(i, j, v)
        assert kb.is_known(lit), f"Expected {lit} in facts"
    print("  [PASS] All given clues are known facts")


def test_kb_empty_cells_not_known():
    """No Val literal for an empty cell should appear as a known fact."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    for i, j in EMPTY_CELLS:
        for v in range(1, N + 1):
            assert not kb.is_known(Val(i, j, v)), \
                f"Val({i},{j},{v}) should not be a fact (cell is empty)"
    print("  [PASS] No Val facts for empty cells")


def test_kb_less_ground_truth_facts():
    """All Less(a,b) for a<b must be known facts (A11 unit clauses)."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            lit = Less(a, b)
            assert kb.is_known(lit), f"Expected {lit} in facts"
    print(f"  [PASS] All Less(a,b) facts present ({comb(N,2)} pairs)")


def test_kb_less_irreflexivity_facts():
    """All ~Less(v,v) must be known facts (A14 unit clauses)."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    for v in range(1, N + 1):
        lit = ~Less(v, v)
        assert kb.is_known(lit), f"Expected {lit} in facts"
    print(f"  [PASS] All ~Less(v,v) facts present ({N} literals)")


def test_kb_get_facts_by_predicate_val():
    """get_facts_by_predicate('Val') returns exactly the given-clue facts."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    val_facts = kb.get_facts_by_predicate("Val")
    expected_lits = {Val(i, j, v) for i, j, v in GIVEN_CELLS}
    assert set(val_facts) == expected_lits, \
        f"Val facts: {val_facts} != {expected_lits}"
    print(f"  [PASS] get_facts_by_predicate('Val') == {sorted(str(l) for l in val_facts)}")


def test_kb_get_facts_by_predicate_less():
    """get_facts_by_predicate('Less') returns all Less ground-truth facts."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    less_facts = kb.get_facts_by_predicate("Less")
    # Only positive Less(a,b) facts; ~Less(v,v) has name 'Less' but is negated
    positive = [f for f in less_facts if not f.negated]
    negative = [f for f in less_facts if f.negated]
    assert len(positive) == comb(N, 2), \
        f"Expected {comb(N,2)} positive Less facts, got {len(positive)}"
    assert len(negative) == N, \
        f"Expected {N} negative Less facts (~Less(v,v)), got {len(negative)}"
    print(f"  [PASS] get_facts_by_predicate('Less'): {len(positive)} positive, {len(negative)} negative")


def test_kb_get_clauses_returns_all():
    """get_clauses() returns the same collection as len(kb)."""
    puzzle = Parser().parse(FIXTURE)
    kb = CNFGenerator.generate(puzzle)
    assert len(kb.get_clauses()) == len(kb)
    print(f"  [PASS] get_clauses() length == len(kb) == {len(kb)}")


# ===========================================================================
# Runner
# ===========================================================================


if __name__ == "__main__":
    print("=== Integration: Parser -> Puzzle -> KnowledgeBase ===\n")

    print("Stage 1 — Parser -> Puzzle:")
    test_parser_returns_puzzle()
    test_puzzle_grid_size()
    test_puzzle_array_shapes()
    test_puzzle_given_cells()
    test_puzzle_empty_cells()
    test_puzzle_is_given()
    test_puzzle_is_not_complete()
    test_puzzle_h_constraints()
    test_puzzle_v_constraints()

    print("\nStage 2 — Puzzle -> KnowledgeBase:")
    test_kb_total_clause_count()
    test_kb_total_fact_count()
    test_kb_given_clues_are_known()
    test_kb_empty_cells_not_known()
    test_kb_less_ground_truth_facts()
    test_kb_less_irreflexivity_facts()
    test_kb_get_facts_by_predicate_val()
    test_kb_get_facts_by_predicate_less()
    test_kb_get_clauses_returns_all()

    print("\n=== All integration tests passed! ===")
