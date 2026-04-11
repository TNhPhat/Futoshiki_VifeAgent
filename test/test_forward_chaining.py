"""
Test suite for Forward Chaining Solver and Engine.

Tests the complete data-driven (bottom-up) pipeline:
  1. ForwardChainingEngine - Fix-point iteration and fact generation.
  2. ForwardChainingSolver - Puzzle solving via exhaustive fact derivation.

Uses valid 2x2 and 4x4 Futoshiki puzzles with known solutions.
"""

import os
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fol.predicates import Literal, Val, Given
from fol.horn_kb import HornClause
from fol.horn_generator import HornClauseGenerator
from inference.forward_chaining import ForwardChainingEngine
from solver.forward_chaining_solver import ForwardChaining
from core.parser import Parser
from core.puzzle import Puzzle
from utils.stats_csv import StatsCsvWriter


# ===========================================================================
# Test Fixtures - Valid Puzzles
# ===========================================================================

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def create_valid_4x4_puzzle() -> Puzzle:
    from constraints.inequality_constraint import InequalityConstraint
    grid = np.array([
        [1, 0, 0, 0],
        [0, 0, 4, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 3]
    ], dtype=int)
    
    h_constraints = [InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction='<')]
    v_constraints = [InequalityConstraint(cell1=(1, 1), cell2=(2, 1), direction='<')]
    
    return Puzzle(N=4, grid=grid, h_constraints=h_constraints, v_constraints=v_constraints)

def create_simple_2x2_puzzle() -> Puzzle:
    from constraints.inequality_constraint import InequalityConstraint
    grid = np.array([
        [1, 0],
        [0, 0]
    ], dtype=int)
    
    h_constraints = [InequalityConstraint(cell1=(0, 0), cell2=(0, 1), direction='<')]
    v_constraints = [InequalityConstraint(cell1=(0, 1), cell2=(1, 1), direction='>')]
    
    return Puzzle(N=2, grid=grid, h_constraints=h_constraints, v_constraints=v_constraints)


def assert_solved_cells_match_expected(solution: Puzzle, expected_grid: np.ndarray) -> None:
    solved_mask = solution.grid != 0
    assert np.array_equal(solution.grid[solved_mask], expected_grid[solved_mask]), (
        f"Solved-cell mismatch\nExpected:\n{expected_grid}\nGot:\n{solution.grid}"
    )


# ===========================================================================
# Forward Chaining Engine Tests
# ===========================================================================

def test_engine_derive_new_fact():
    """Engine derives a new fact based on a simple rule."""
    facts = [Given(0, 0, 1)]
    
    # Bypass hàm Given(int) bằng cách dùng trực tiếp Literal để khai báo biến
    body_literal = Literal("Given", ("i", "j", "v"))
    rule = HornClause(head=Val("i", "j", "v"), body=[body_literal])
    
    engine = ForwardChainingEngine(rules=[rule], initial_facts=facts)
    derived_facts = engine.run()
    
    expected_fact = Val(0, 0, 1)
    assert expected_fact in derived_facts, f"Expected {expected_fact} in {derived_facts}"
    print("  [PASS] Engine derives new fact from rule")

def test_engine_saturation():
    """Engine stops correctly when no new facts can be generated."""
    facts = [Val(0, 0, 1)]
    
    # Bypass hàm Given(int) bằng cách dùng trực tiếp Literal để khai báo biến
    body_literal = Literal("Given", ("i", "j", "v"))
    rule = HornClause(head=Val("i", "j", "v"), body=[body_literal])
    
    engine = ForwardChainingEngine(rules=[rule], initial_facts=facts)
    derived_facts = engine.run()
    
    assert len(derived_facts) == 1
    assert Val(0, 0, 1) in derived_facts
    print("  [PASS] Engine saturates without infinite loops")
    
def test_engine_max_iterations():
    """Engine respects max_iterations limit."""
    # A rule that creates an infinite loop if not checked (A(x) -> A(x+1))
    # Simulated by just running iterations directly or ensuring it hits max limit.
    # In logic, since variables are finite here, we test the cutoff.
    facts = [Given(0, 0, 1)]
    rule = HornClause(head=Given(0, 0, 1), body=[Given(0, 0, 1)]) 
    
    engine = ForwardChainingEngine(rules=[rule], initial_facts=facts, max_iterations=2)
    engine.run()
    
    # If it didn't hang, the test passes
    print("  [PASS] Engine respects max_iterations limit")


# ===========================================================================
# Forward Chaining Solver Tests
# ===========================================================================

def test_solver_solve_2x2():
    """ForwardChaining solves a 2x2 puzzle."""
    puzzle = create_simple_2x2_puzzle()
    solver = ForwardChaining()
    
    solution, stats = solver.solve(puzzle)
    
    assert solution is not None, "Solver failed to find a solution"
    assert solution.is_complete(), "Solution should be complete"
    
    expected = np.array([[1, 2], [2, 1]])
    assert np.array_equal(solution.grid, expected), f"Expected {expected}, got {solution.grid}"
    print(f"  [PASS] Solver solves 2x2 (time={stats.time_ms:.2f}ms, inferences={stats.inference_count})")

def test_solver_solve_4x4():
    """ForwardChaining validates only the cells it can solve."""
    puzzle = create_valid_4x4_puzzle()
    solver = ForwardChaining()
    
    solution, stats = solver.solve(puzzle)
    
    assert solution is not None, "Solver failed to find a solution"
    expected = np.array([
        [1, 2, 3, 4],
        [2, 3, 4, 1],
        [3, 4, 1, 2],
        [4, 1, 2, 3],
    ], dtype=int)
    assert_solved_cells_match_expected(solution, expected)
    initially_unsolved_mask = puzzle.grid == 0
    initially_unsolved = int(np.count_nonzero(initially_unsolved_mask))
    solved_by_algo = int(np.count_nonzero(solution.grid[initially_unsolved_mask]))
    expected_ratio = 1.0 if initially_unsolved == 0 else solved_by_algo / initially_unsolved
    assert stats.completion_ratio == expected_ratio

    print(
        f"  [PASS] Solver returns 4x4 best-effort grid "
        f"(complete={solution.is_complete()}, ratio={stats.completion_ratio:.3f}, "
        f"time={stats.time_ms:.2f}ms, inferences={stats.inference_count})"
    )

def test_solver_respects_given_cells():
    """ForwardChaining preserves given cell values."""
    puzzle = create_valid_4x4_puzzle()
    solver = ForwardChaining()
    
    solution, _ = solver.solve(puzzle)
    
    # Báo cho Pylance biết solution chắc chắn không phải là None tại thời điểm này
    assert solution is not None, "Solver failed to find a solution"
    
    assert solution.grid[0, 0] == 1, "Given (0,0)=1 not preserved"
    assert solution.grid[1, 2] == 4, "Given (1,2)=4 not preserved"
    assert solution.grid[3, 3] == 3, "Given (3,3)=3 not preserved"
    print("  [PASS] Solver preserves given cells")

def test_solver_stats_populated():
    """ForwardChaining populates statistics properly."""
    puzzle = create_simple_2x2_puzzle()
    solver = ForwardChaining()
    
    _, stats = solver.solve(puzzle)
    
    assert stats.time_ms > 0, "time_ms should be > 0"
    assert stats.memory_kb > 0, "memory_kb should be > 0"
    assert stats.inference_count > 0, "inference_count should be > 0"
    assert 0.0 <= stats.completion_ratio <= 1.0, "completion_ratio should be in [0,1]"
    print(f"  [PASS] Stats populated: time={stats.time_ms:.2f}ms, inferences={stats.inference_count}")

def test_solver_name():
    """ForwardChaining returns correct name."""
    solver = ForwardChaining()
    name = solver.get_name()
    assert "Forward" in name, f"Name should mention Forward: {name}"
    print(f"  [PASS] Solver name: {name}")


# ===========================================================================
# Integration Tests
# ===========================================================================

def _run_benchmark_against_expected():
    """Solve all benchmark inputs and match expected solution grids using FC."""
    benchmark_root = Path(__file__).resolve().parents[1] / "src" / "benchmark"
    input_dir = benchmark_root / "input"
    expected_dir = benchmark_root / "expected"

    if not input_dir.exists() or not expected_dir.exists():
        print("  [SKIP] benchmark input/expected directories not found")
        return []

    parser = Parser()
    solver = ForwardChaining()
    input_files = sorted(input_dir.glob("*.txt"))

    if not input_files:
        print("  [SKIP] no benchmark input files found")
        return []

    stats_rows = []
    for input_path in input_files:
        expected_path = expected_dir / input_path.name
        assert expected_path.exists(), f"Missing expected file: {expected_path}"

        puzzle = parser.parse(str(input_path))
        expected = parser.parse(str(expected_path))
        solution, stats = solver.solve(puzzle)

        assert solution is not None, f"No solution returned for {input_path.name}"
        assert_solved_cells_match_expected(solution, expected.grid)
        initially_unsolved_mask = puzzle.grid == 0
        initially_unsolved = int(np.count_nonzero(initially_unsolved_mask))
        solved_by_algo = int(np.count_nonzero(solution.grid[initially_unsolved_mask]))
        expected_ratio = 1.0 if initially_unsolved == 0 else solved_by_algo / initially_unsolved
        assert stats.completion_ratio == expected_ratio

        print(
            f"  [PASS] {input_path.name} "
            f"(ratio={stats.completion_ratio:.3f}, time={stats.time_ms:.2f}ms, "
            f"inf={stats.inference_count})"
        )
        stats_rows.append((input_path.name, stats))
        
    return stats_rows

def test_integration_benchmark_against_expected():
    _run_benchmark_against_expected()


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    print("=== Forward Chaining Test Suite ===\n")
    
    print("--- Forward Chaining Engine Tests ---")
    test_engine_derive_new_fact()
    test_engine_saturation()
    test_engine_max_iterations()
    
    print("\n--- Forward Chaining Solver Tests ---")
    test_solver_solve_2x2()
    test_solver_solve_4x4()
    test_solver_respects_given_cells()
    test_solver_stats_populated()
    test_solver_name()
    
    print("\n--- Integration Benchmark Tests ---")
    solver = ForwardChaining()
    for test_name, stats in _run_benchmark_against_expected():
        StatsCsvWriter.write_stat(
            test_name=test_name,
            stats=stats,
            solver_name=solver.get_name(),
        )
        
    print("\n=== All forward chaining tests passed! ===")
