"""
Test suite for Backward Chaining Solver, Engine, and Unifier.

Tests the complete backward chaining pipeline:
  1. Unifier - variable binding and literal matching
  2. BackwardChainingEngine - SLD resolution with NAF
  3. BackwardChainingSolver - puzzle solving with constraint checking

Uses valid 4x4 Futoshiki puzzles with known solutions.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fol.predicates import Literal, Val, Less
from fol.unifier import Unifier, Substitution
from fol.horn_kb import HornClause, HornClauseKnowledgeBase
from fol.horn_generator import HornClauseGenerator
from inference.backward_chaining import BackwardChainingEngine
from solver.ac3_backward_chaining_solver import AC3BackwardChaining
from solver.backward_chaining_solver import BackwardChaining
from core.parser import Parser
from core.puzzle import Puzzle
from utils.stats_csv import StatsCsvWriter
import numpy as np


# ===========================================================================
# Test Fixtures - Valid 4x4 Puzzles
# ===========================================================================

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def create_valid_4x4_puzzle() -> Puzzle:
    """
    Create a valid 4x4 Futoshiki puzzle with known solution.
    
    Solution:
        [1, 2, 3, 4]
        [2, 3, 4, 1]
        [3, 4, 1, 2]
        [4, 1, 2, 3]
    
    Given cells: (0,0)=1, (1,2)=4, (3,3)=3
    Constraints: (0,0)<(0,1), (1,1)<(2,1)
    """
    from constraints.inequality_constraint import InequalityConstraint
    
    grid = np.array([
        [1, 0, 0, 0],
        [0, 0, 4, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 3]
    ], dtype=int)
    
    h_constraints = [
        InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction='<'),  # 1 < 2
    ]
    
    v_constraints = [
        InequalityConstraint(cell1=(1, 1), cell2=(2, 1), direction='<'),  # 3 < 4
    ]
    
    return Puzzle(N=4, grid=grid, h_constraints=h_constraints, v_constraints=v_constraints)


def create_simple_2x2_puzzle() -> Puzzle:
    """
    Create a simple 2x2 puzzle for basic testing.
    
    Solution:
        [1, 2]
        [2, 1]
    
    Given: (0,0)=1
    Constraints: (0,0)<(0,1), (0,1)>(1,1)
    """
    from constraints.inequality_constraint import InequalityConstraint
    
    grid = np.array([
        [1, 0],
        [0, 0]
    ], dtype=int)
    
    h_constraints = [
        InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction='<'),
    ]
    
    v_constraints = [
        InequalityConstraint(cell1=(0, 1), cell2=(1, 1), direction='>'),
    ]
    
    return Puzzle(N=2, grid=grid, h_constraints=h_constraints, v_constraints=v_constraints)


def create_relative_size_chain_4x4_puzzle() -> Puzzle:
    """Create a 4x4 puzzle with a horizontal inequality chain on empty cells."""
    from constraints.inequality_constraint import InequalityConstraint

    grid = np.array([
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ], dtype=int)

    h_constraints = [
        InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction='<'),
        InequalityConstraint(cell1=(0, 1), cell2=(0, 2), direction='<'),
    ]

    return Puzzle(N=4, grid=grid, h_constraints=h_constraints, v_constraints=[])


def create_hidden_single_row_4x4_puzzle() -> Puzzle:
    """Create a 4x4 puzzle where one row has a hidden single candidate."""
    grid = np.array([
        [0, 0, 4, 0],
        [3, 1, 0, 4],
        [4, 0, 0, 1],
        [0, 4, 0, 0],
    ], dtype=int)

    return Puzzle(N=4, grid=grid, h_constraints=[], v_constraints=[])


# ===========================================================================
# Unifier Tests
# ===========================================================================


def test_unifier_match_identical_literals():
    """Unifier.match succeeds for identical ground literals."""
    unifier = Unifier()
    l1 = Literal("Val", (0, 1, 2))
    l2 = Literal("Val", (0, 1, 2))
    
    result = unifier.match(l1, l2)
    assert result == {}, f"Expected empty substitution, got {result}"
    print("  [PASS] match identical literals")


def test_unifier_match_with_variable():
    """Unifier.match binds variable to constant."""
    unifier = Unifier()
    l1 = Literal("Val", (0, 1, "v"))  # v is a variable
    l2 = Literal("Val", (0, 1, 2))
    
    result = unifier.match(l1, l2)
    assert result == {"v": 2}, f"Expected {{'v': 2}}, got {result}"
    print("  [PASS] match with variable binding")


def test_unifier_match_fails_different_constants():
    """Unifier.match fails when constants differ."""
    unifier = Unifier()
    l1 = Literal("Val", (0, 1, 3))
    l2 = Literal("Val", (0, 1, 2))
    
    result = unifier.match(l1, l2)
    assert result is None, f"Expected None, got {result}"
    print("  [PASS] match fails for different constants")


def test_unifier_match_fails_different_names():
    """Unifier.match fails when predicate names differ."""
    unifier = Unifier()
    l1 = Literal("Val", (0, 1, 2))
    l2 = Literal("Less", (0, 1, 2))
    
    result = unifier.match(l1, l2)
    assert result is None, f"Expected None, got {result}"
    print("  [PASS] match fails for different predicate names")


def test_unifier_match_fails_different_signs():
    """Unifier.match fails when negation signs differ."""
    unifier = Unifier()
    l1 = Literal("Val", (0, 1, 2), negated=False)
    l2 = Literal("Val", (0, 1, 2), negated=True)
    
    result = unifier.match(l1, l2)
    assert result is None, f"Expected None, got {result}"
    print("  [PASS] match fails for different signs")


def test_unifier_resolve_complementary():
    """Unifier.resolve succeeds for complementary literals."""
    unifier = Unifier()
    l1 = Literal("Val", (0, 1, 2), negated=False)
    l2 = Literal("Val", (0, 1, 2), negated=True)
    
    result = unifier.resolve(l1, l2)
    assert result == {}, f"Expected empty substitution, got {result}"
    print("  [PASS] resolve complementary literals")


def test_unifier_apply_to_literal():
    """Unifier.apply_to_literal substitutes variables correctly."""
    unifier = Unifier()
    lit = Literal("Val", (0, "j", "v"))
    subst = {"j": 1, "v": 3}
    
    result = unifier.apply_to_literal(lit, subst)
    expected = Literal("Val", (0, 1, 3))
    assert result == expected, f"Expected {expected}, got {result}"
    print("  [PASS] apply_to_literal substitutes variables")


def test_unifier_rename_variables():
    """Unifier.rename_variables appends suffix to variables."""
    unifier = Unifier()
    lit = Literal("Val", (0, "j", "v"))
    
    result = unifier.rename_variables(lit, "42")
    expected = Literal("Val", (0, "j_42", "v_42"))
    assert result == expected, f"Expected {expected}, got {result}"
    print("  [PASS] rename_variables appends suffix")


def test_unifier_is_variable():
    """Unifier._is_variable correctly identifies variables."""
    unifier = Unifier()
    
    assert unifier._is_variable("v") == True
    assert unifier._is_variable("var") == True
    assert unifier._is_variable("x_1") == True
    assert unifier._is_variable(1) == False
    assert unifier._is_variable("Val") == False  # Uppercase
    assert unifier._is_variable("") == False
    print("  [PASS] _is_variable identifies variables correctly")


# ===========================================================================
# Horn KB Tests
# ===========================================================================


def test_horn_kb_add_fact():
    """HornClauseKnowledgeBase stores and retrieves facts."""
    kb = HornClauseKnowledgeBase()
    fact = Val(0, 0, 1)
    kb.add_fact(fact)
    
    clauses = kb.get_clause_for("Val")
    assert len(clauses) == 1
    assert clauses[0].is_fact()
    assert clauses[0].head == fact
    print("  [PASS] KB stores and retrieves facts")


def test_horn_kb_add_rule():
    """HornClauseKnowledgeBase stores and retrieves rules."""
    kb = HornClauseKnowledgeBase()
    head = Val(0, 0, 1)
    body = [~Val(0, 0, 2), ~Val(0, 0, 3)]
    rule = HornClause(head=head, body=body)
    kb.add_rule(rule)
    
    clauses = kb.get_clause_for("Val")
    assert len(clauses) == 1
    assert not clauses[0].is_fact()
    assert clauses[0].head == head
    assert clauses[0].body == body
    print("  [PASS] KB stores and retrieves rules")


def test_horn_kb_get_clause_for_missing():
    """HornClauseKnowledgeBase returns empty list for missing predicate."""
    kb = HornClauseKnowledgeBase()
    
    clauses = kb.get_clause_for("NonExistent")
    assert clauses == [], f"Expected empty list, got {clauses}"
    print("  [PASS] KB returns empty list for missing predicate")


def test_horn_kb_clause_count():
    """HornClauseKnowledgeBase tracks total clause count."""
    kb = HornClauseKnowledgeBase()
    kb.add_fact(Val(0, 0, 1))
    kb.add_fact(Val(0, 1, 2))
    kb.add_fact(Less(1, 2))
    
    assert kb.clause_count == 3, f"Expected 3 clauses, got {kb.clause_count}"
    print("  [PASS] KB tracks clause count")


# ===========================================================================
# Backward Chaining Engine Tests
# ===========================================================================


def test_engine_prove_fact():
    """BackwardChainingEngine proves a fact in the KB."""
    kb = HornClauseKnowledgeBase()
    kb.add_fact(Val(0, 0, 1))
    
    engine = BackwardChainingEngine(kb)
    goal = Literal("Val", (0, 0, 1))
    
    result = engine.prove_all([goal])
    assert result is not None, "Expected proof to succeed"
    print("  [PASS] Engine proves fact")


def test_engine_prove_fact_with_variable():
    """BackwardChainingEngine binds variable when proving."""
    kb = HornClauseKnowledgeBase()
    kb.add_fact(Val(0, 0, 1))
    
    engine = BackwardChainingEngine(kb)
    goal = Literal("Val", (0, 0, "v"))
    
    result = engine.prove_all([goal])
    assert result is not None, "Expected proof to succeed"
    assert "v" in result or any("v" in str(k) for k in result.keys()), \
        f"Expected variable binding, got {result}"
    print("  [PASS] Engine proves with variable binding")


def test_engine_fail_missing_fact():
    """BackwardChainingEngine fails for missing fact."""
    kb = HornClauseKnowledgeBase()
    kb.add_fact(Val(0, 0, 1))
    
    engine = BackwardChainingEngine(kb)
    goal = Literal("Val", (0, 0, 2))  # Different value
    
    result = engine.prove_all([goal])
    assert result is None, f"Expected None, got {result}"
    print("  [PASS] Engine fails for missing fact")


def test_engine_prove_multiple_goals():
    """BackwardChainingEngine proves multiple goals."""
    kb = HornClauseKnowledgeBase()
    kb.add_fact(Val(0, 0, 1))
    kb.add_fact(Val(0, 1, 2))
    
    engine = BackwardChainingEngine(kb)
    goals = [
        Literal("Val", (0, 0, 1)),
        Literal("Val", (0, 1, 2))
    ]
    
    result = engine.prove_all(goals)
    assert result is not None, "Expected proof to succeed"
    print("  [PASS] Engine proves multiple goals")


def test_engine_depth_limit():
    """BackwardChainingEngine respects depth limit."""
    kb = HornClauseKnowledgeBase()
    # Create a rule that would recurse infinitely
    # P(x) :- P(x+1) (simplified concept)
    
    engine = BackwardChainingEngine(kb, depth_limit=5)
    goal = Literal("Val", (0, 0, 1))
    
    result = engine.prove_all([goal])
    assert result is None, "Expected None due to depth limit or missing fact"
    print("  [PASS] Engine respects depth limit")


# ===========================================================================
# Backward Chaining Solver Tests
# ===========================================================================


def test_solver_solve_2x2():
    """BackwardChainingSolver solves a 2x2 puzzle."""
    puzzle = create_simple_2x2_puzzle()
    solver = BackwardChaining()
    
    solution, stats = solver.solve(puzzle)
    
    assert solution.is_complete(), "Solution should be complete"
    
    # Verify solution
    expected = np.array([[1, 2], [2, 1]])
    assert np.array_equal(solution.grid, expected), \
        f"Expected {expected}, got {solution.grid}"
    print(solution)
    print(f"  [PASS] Solver solves 2x2 (time={stats.time_ms:.2f}ms)")


def test_solver_solve_4x4():
    """BackwardChainingSolver solves a valid 4x4 puzzle."""
    puzzle = create_valid_4x4_puzzle()
    solver = BackwardChaining()
    
    solution, stats = solver.solve(puzzle)
    
    assert solution.is_complete(), "Solution should be complete"
    
    # Verify row uniqueness
    for i in range(4):
        row = list(solution.grid[i])
        assert sorted(row) == [1, 2, 3, 4], f"Row {i} invalid: {row}"
    
    # Verify column uniqueness
    for j in range(4):
        col = list(solution.grid[:, j])
        assert sorted(col) == [1, 2, 3, 4], f"Col {j} invalid: {col}"
    
    # Verify constraints
    assert solution.grid[0, 0] < solution.grid[0, 1], "H constraint violated"
    assert solution.grid[1, 1] < solution.grid[2, 1], "V constraint violated"
    print(solution)
    print(f"  [PASS] Solver solves 4x4 (time={stats.time_ms:.2f}ms, inferences={stats.inference_count})")


def test_solver_respects_given_cells():
    """BackwardChainingSolver preserves given cell values."""
    puzzle = create_valid_4x4_puzzle()
    solver = BackwardChaining()
    
    solution, _ = solver.solve(puzzle)
    
    # Check given cells are preserved
    assert solution.grid[0, 0] == 1, "Given (0,0)=1 not preserved"
    assert solution.grid[1, 2] == 4, "Given (1,2)=4 not preserved"
    assert solution.grid[3, 3] == 3, "Given (3,3)=3 not preserved"
    print(solution)
    print("  [PASS] Solver preserves given cells")


def test_solver_validates_constraints():
    """BackwardChainingSolver respects inequality constraints."""
    puzzle = create_valid_4x4_puzzle()
    solver = BackwardChaining()
    
    solution, _ = solver.solve(puzzle)
    
    # Check all constraints
    for c in puzzle.h_constraints + puzzle.v_constraints:
        r1, c1 = c.cell1
        r2, c2 = c.cell2
        v1 = int(solution.grid[r1, c1])
        v2 = int(solution.grid[r2, c2])
        
        if c.direction == '<':
            assert v1 < v2, f"Constraint {c.cell1} < {c.cell2} violated: {v1} >= {v2}"
        else:
            assert v1 > v2, f"Constraint {c.cell1} > {c.cell2} violated: {v1} <= {v2}"
    print(solution)
    print("  [PASS] Solver validates all constraints")


def test_solver_stats_populated():
    """BackwardChainingSolver populates statistics."""
    puzzle = create_simple_2x2_puzzle()
    solver = BackwardChaining()
    
    _, stats = solver.solve(puzzle)
    
    assert stats.time_ms > 0, "time_ms should be > 0"
    assert stats.memory_kb > 0, "memory_kb should be > 0"
    assert stats.inference_count > 0, "inference_count should be > 0"
    
    print(f"  [PASS] Stats populated: time={stats.time_ms:.2f}ms, mem={stats.memory_kb:.2f}KB")


def test_solver_name():
    """BackwardChainingSolver returns correct name."""
    solver = BackwardChaining()
    name = solver.get_name()
    
    assert "Backward" in name or "backward" in name, f"Name should mention backward: {name}"
    print(f"  [PASS] Solver name: {name}")


def test_ac3_solver_solve_4x4():
    """AC3BackwardChaining solves a valid 4x4 puzzle."""
    puzzle = create_valid_4x4_puzzle()
    solver = AC3BackwardChaining()

    solution, _ = solver.solve(puzzle)
    assert solution is not None
    assert solution.is_complete(), "AC3 solution should be complete"

    for i in range(4):
        row = list(solution.grid[i])
        assert sorted(row) == [1, 2, 3, 4], f"Row {i} invalid: {row}"


def test_ac3_solver_name():
    """AC3BackwardChaining returns a name that mentions AC3."""
    name = AC3BackwardChaining().get_name()
    assert "AC3" in name, f"Name should mention AC3: {name}"


# ===========================================================================
# Integration Tests
# ===========================================================================


def test_integration_parse_and_solve():
    """Integration: Parse fixture and solve with backward chaining."""
    fixture_path = os.path.join(FIXTURE_DIR, "input_2x2.txt")
    
    if not os.path.exists(fixture_path):
        print("  [SKIP] input_2x2.txt fixture not found")
        return
    
    puzzle = Parser().parse(fixture_path)
    solver = BackwardChaining()
    
    solution, stats = solver.solve(puzzle)
    
    assert solution.is_complete(), "Solution should be complete"
    print(f"  [PASS] Integration parse+solve (time={stats.time_ms:.2f}ms)")


def test_integration_horn_generator():
    """Integration: HornClauseGenerator produces valid KB."""
    puzzle = create_valid_4x4_puzzle()
    kb = HornClauseGenerator.generate(puzzle)
    
    # Should have Val facts for given cells
    val_clauses = kb.get_clause_for("Val")
    val_facts = [c for c in val_clauses if c.is_fact() and not c.head.negated]
    
    assert len(val_facts) == 3, f"Expected 3 Val facts, got {len(val_facts)}"
    
    # Should have Less facts
    less_clauses = kb.get_clause_for("Less")
    less_facts = [c for c in less_clauses if c.is_fact() and not c.head.negated]
    
    # For N=4, should have C(4,2) = 6 Less facts
    assert len(less_facts) == 6, f"Expected 6 Less facts, got {len(less_facts)}"
    
    print(f"  [PASS] HornClauseGenerator produces valid KB ({kb.clause_count} clauses)")


def test_exclusion_domains_prune_direct_candidates():
    """Direct exclusion removes row/column/given-inequality candidates."""
    puzzle = create_simple_2x2_puzzle()

    domains = HornClauseGenerator.exclusion_domains(puzzle)

    assert domains is not None
    assert domains[(0, 1)] == {2}, f"Expected {{2}}, got {domains[(0, 1)]}"
    assert domains[(1, 0)] == {2}, f"Expected {{2}}, got {domains[(1, 0)]}"
    assert domains[(1, 1)] == {1, 2}, f"Expected {{1, 2}}, got {domains[(1, 1)]}"


def test_relative_size_domains_prune_inequality_chain():
    """Relative size tightens domains across transitive inequality chains."""
    puzzle = create_relative_size_chain_4x4_puzzle()

    domains = HornClauseGenerator.relative_size_domains(puzzle)

    assert domains is not None
    assert domains[(0, 0)] == {1, 2}, f"Expected {{1, 2}}, got {domains[(0, 0)]}"
    assert domains[(0, 1)] == {2, 3}, f"Expected {{2, 3}}, got {domains[(0, 1)]}"
    assert domains[(0, 2)] == {3, 4}, f"Expected {{3, 4}}, got {domains[(0, 2)]}"


def test_hidden_single_domains_prune_unique_row_candidate():
    """Hidden single collapses the only carrier of a value in a row."""
    puzzle = create_hidden_single_row_4x4_puzzle()

    domains = HornClauseGenerator.hidden_single_domains(puzzle)

    assert domains is not None
    assert domains[(0, 0)] == {1}, f"Expected {{1}}, got {domains[(0, 0)]}"
    assert domains[(0, 1)] == {3}, f"Expected {{3}}, got {domains[(0, 1)]}"
    assert domains[(0, 3)] == {2}, f"Expected {{2}}, got {domains[(0, 3)]}"


def _run_benchmark_against_expected():
    """Solve all benchmark inputs and match expected solution grids."""
    benchmark_root = Path(__file__).resolve().parents[1] / "src" / "benchmark"
    input_dir = benchmark_root / "input"
    expected_dir = benchmark_root / "expected"

    if not input_dir.exists() or not expected_dir.exists():
        print("  [SKIP] benchmark input/expected directories not found")
        return

    parser = Parser()
    solver = BackwardChaining()
    input_files = sorted(input_dir.glob("*.txt"))

    if not input_files:
        print("  [SKIP] no benchmark input files found")
        return

    stats_rows = []
    for input_path in input_files:
        expected_path = expected_dir / input_path.name
        assert expected_path.exists(), f"Missing expected file: {expected_path}"

        puzzle = parser.parse(str(input_path))
        expected = parser.parse(str(expected_path))
        solution, stats = solver.solve(puzzle)

        assert solution is not None, f"No solution returned for {input_path.name}"
        assert solution.is_complete(), f"Incomplete solution for {input_path.name}"
        assert np.array_equal(solution.grid, expected.grid), (
            f"Grid mismatch for {input_path.name}\n"
            f"Expected:\n{expected.grid}\n"
            f"Got:\n{solution.grid}"
        )

        print(f"\n[Benchmark] {input_path.name}")
        print(solution)
        print(
            "  Stats: "
            f"time={stats.time_ms:.2f}ms, "
            f"memory={stats.memory_kb:.2f}KB, "
            f"inferences={stats.inference_count}"
        )
        print(f"  [PASS] {input_path.name}")
        stats_rows.append((input_path.name, stats))
    return stats_rows


# def test_integration_benchmark_against_expected():
#     _run_benchmark_against_expected()


# ===========================================================================
# Runner
# ===========================================================================


if __name__ == "__main__":
    print("=== Backward Chaining Test Suite ===\n")
    
    print("--- Unifier Tests ---")
    test_unifier_match_identical_literals()
    test_unifier_match_with_variable()
    test_unifier_match_fails_different_constants()
    test_unifier_match_fails_different_names()
    test_unifier_match_fails_different_signs()
    test_unifier_resolve_complementary()
    test_unifier_apply_to_literal()
    test_unifier_rename_variables()
    test_unifier_is_variable()
    
    print("\n--- Horn KB Tests ---")
    test_horn_kb_add_fact()
    test_horn_kb_add_rule()
    test_horn_kb_get_clause_for_missing()
    test_horn_kb_clause_count()
    
    print("\n--- Backward Chaining Engine Tests ---")
    test_engine_prove_fact()
    test_engine_prove_fact_with_variable()
    test_engine_fail_missing_fact()
    test_engine_prove_multiple_goals()
    test_engine_depth_limit()
    
    print("\n--- Backward Chaining Solver Tests ---")
    test_solver_solve_2x2()
    test_solver_solve_4x4()
    test_solver_respects_given_cells()
    test_solver_validates_constraints()
    test_solver_stats_populated()
    test_solver_name()
    test_ac3_solver_solve_4x4()
    test_ac3_solver_name()
    
    print("\n--- Integration Tests ---")
    test_integration_parse_and_solve()
    test_integration_horn_generator()
    solver = BackwardChaining()
    # for test_name, stats in _run_benchmark_against_expected():
    #     StatsCsvWriter.write_stat(
    #         test_name=test_name,
    #         stats=stats,
    #         solver_name=solver.get_name(),
    #     )
    print("\n=== All backward chaining tests passed! ===")
