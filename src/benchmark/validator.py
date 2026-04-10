from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


PROJECT_SRC = Path(__file__).resolve().parents[1]
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from futoshiki_vifeagent.core import ParseError, Parser, Puzzle


@dataclass(slots=True)
class ValidationResult:
    path: Path
    ok: bool
    message: str


def _constraint_signature(puzzle: Puzzle) -> tuple[tuple[tuple[int, int], tuple[int, int], str], ...]:
    return tuple(
        sorted(
            (constraint.cell1, constraint.cell2, constraint.direction)
            for constraint in (*puzzle.h_constraints, *puzzle.v_constraints)
        )
    )


def _row_constraint_map(puzzle: Puzzle) -> list[list[int]]:
    rows = [[0] * (puzzle.N - 1) for _ in range(puzzle.N)]
    for constraint in puzzle.h_constraints:
        row, col = constraint.cell1
        rows[row][col] = 1 if constraint.direction == "<" else -1
    return rows


def _col_constraint_map(puzzle: Puzzle) -> list[list[int]]:
    rows = [[0] * puzzle.N for _ in range(puzzle.N - 1)]
    for constraint in puzzle.v_constraints:
        row, col = constraint.cell1
        rows[row][col] = 1 if constraint.direction == "<" else -1
    return rows


def serialize_puzzle(puzzle: Puzzle) -> str:
    lines = [str(puzzle.N)]
    lines.extend(",".join(str(int(value)) for value in row) for row in puzzle.grid.tolist())
    lines.extend(",".join(str(value) for value in row) for row in _row_constraint_map(puzzle))
    lines.extend(",".join(str(value) for value in row) for row in _col_constraint_map(puzzle))
    return "\n".join(lines) + "\n"


def _adjacent_constraint_allows(puzzle: Puzzle, grid: np.ndarray, row: int, col: int, value: int) -> bool:
    left_constraint = puzzle.get_h_constraint(row, col - 1) if col > 0 else None
    if left_constraint is not None and grid[row, col - 1] != 0:
        left_value = int(grid[row, col - 1])
        if left_constraint.direction == "<" and not (left_value < value):
            return False
        if left_constraint.direction == ">" and not (left_value > value):
            return False

    right_constraint = puzzle.get_h_constraint(row, col) if col < puzzle.N - 1 else None
    if right_constraint is not None and grid[row, col + 1] != 0:
        right_value = int(grid[row, col + 1])
        if right_constraint.direction == "<" and not (value < right_value):
            return False
        if right_constraint.direction == ">" and not (value > right_value):
            return False

    top_constraint = puzzle.get_v_constraint(row - 1, col) if row > 0 else None
    if top_constraint is not None and grid[row - 1, col] != 0:
        top_value = int(grid[row - 1, col])
        if top_constraint.direction == "<" and not (top_value < value):
            return False
        if top_constraint.direction == ">" and not (top_value > value):
            return False

    bottom_constraint = puzzle.get_v_constraint(row, col) if row < puzzle.N - 1 else None
    if bottom_constraint is not None and grid[row + 1, col] != 0:
        bottom_value = int(grid[row + 1, col])
        if bottom_constraint.direction == "<" and not (value < bottom_value):
            return False
        if bottom_constraint.direction == ">" and not (value > bottom_value):
            return False

    return True


def _initial_validation(puzzle: Puzzle) -> None:
    seen_rows: list[set[int]] = [set() for _ in range(puzzle.N)]
    seen_cols: list[set[int]] = [set() for _ in range(puzzle.N)]

    for row in range(puzzle.N):
        for col in range(puzzle.N):
            value = int(puzzle.grid[row, col])
            if value == 0:
                continue
            if value in seen_rows[row]:
                raise ValueError(f"duplicate given value {value} in row {row}")
            if value in seen_cols[col]:
                raise ValueError(f"duplicate given value {value} in column {col}")
            seen_rows[row].add(value)
            seen_cols[col].add(value)

    for constraint in puzzle.h_constraints:
        r1, c1 = constraint.cell1
        r2, c2 = constraint.cell2
        v1 = int(puzzle.grid[r1, c1])
        v2 = int(puzzle.grid[r2, c2])
        if v1 != 0 and v2 != 0:
            if constraint.direction == "<" and not (v1 < v2):
                raise ValueError(f"horizontal constraint violated at {constraint.cell1}")
            if constraint.direction == ">" and not (v1 > v2):
                raise ValueError(f"horizontal constraint violated at {constraint.cell1}")

    for constraint in puzzle.v_constraints:
        r1, c1 = constraint.cell1
        r2, c2 = constraint.cell2
        v1 = int(puzzle.grid[r1, c1])
        v2 = int(puzzle.grid[r2, c2])
        if v1 != 0 and v2 != 0:
            if constraint.direction == "<" and not (v1 < v2):
                raise ValueError(f"vertical constraint violated at {constraint.cell1}")
            if constraint.direction == ">" and not (v1 > v2):
                raise ValueError(f"vertical constraint violated at {constraint.cell1}")


def solve_puzzle(puzzle: Puzzle, limit: int = 2) -> list[np.ndarray]:
    _initial_validation(puzzle)

    grid = puzzle.grid.copy()
    size = puzzle.N
    row_used = [set(int(value) for value in grid[row, :] if int(value) != 0) for row in range(size)]
    col_used = [set(int(value) for value in grid[:, col] if int(value) != 0) for col in range(size)]

    solutions: list[np.ndarray] = []

    def candidates(row: int, col: int) -> list[int]:
        values: list[int] = []
        for value in range(1, size + 1):
            if value in row_used[row] or value in col_used[col]:
                continue
            if _adjacent_constraint_allows(puzzle, grid, row, col, value):
                values.append(value)
        return values

    def choose_cell() -> tuple[int, int, list[int]] | None:
        best_row = -1
        best_col = -1
        best_candidates: list[int] | None = None

        for row in range(size):
            for col in range(size):
                if int(grid[row, col]) != 0:
                    continue
                current_candidates = candidates(row, col)
                if not current_candidates:
                    return (row, col, [])
                if best_candidates is None or len(current_candidates) < len(best_candidates):
                    best_row = row
                    best_col = col
                    best_candidates = current_candidates
                    if len(best_candidates) == 1:
                        return best_row, best_col, best_candidates

        if best_candidates is None:
            return None
        return best_row, best_col, best_candidates

    def search() -> None:
        if len(solutions) >= limit:
            return

        chosen = choose_cell()
        if chosen is None:
            solutions.append(grid.copy())
            return

        row, col, current_candidates = chosen
        if not current_candidates:
            return

        for value in current_candidates:
            grid[row, col] = value
            row_used[row].add(value)
            col_used[col].add(value)

            search()

            row_used[row].remove(value)
            col_used[col].remove(value)
            grid[row, col] = 0

            if len(solutions) >= limit:
                return

    search()
    return solutions


def validate_file(path: Path, expected_dir: Path | None = None) -> ValidationResult:
    parser = Parser()
    try:
        puzzle = parser.parse(str(path))
        solutions = solve_puzzle(puzzle, limit=2)
        if len(solutions) == 0:
            return ValidationResult(path=path, ok=False, message="unsatisfiable puzzle")
        if len(solutions) > 1:
            return ValidationResult(path=path, ok=False, message="puzzle has multiple solutions")

        if expected_dir is not None:
            expected_path = expected_dir / path.name
            if not expected_path.exists():
                return ValidationResult(path=path, ok=False, message=f"missing expected file: {expected_path.name}")

            expected_puzzle = parser.parse(str(expected_path))
            if not np.array_equal(expected_puzzle.grid, solutions[0]):
                return ValidationResult(path=path, ok=False, message=f"expected grid mismatch: {expected_path.name}")
            if _constraint_signature(expected_puzzle) != _constraint_signature(puzzle):
                return ValidationResult(path=path, ok=False, message=f"constraint mismatch: {expected_path.name}")

        return ValidationResult(path=path, ok=True, message="unique solution")

    except (ParseError, ValueError) as exc:
        return ValidationResult(path=path, ok=False, message=str(exc))


def iter_txt_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return

    for file_path in sorted(path.rglob("*.txt")):
        if file_path.is_file():
            yield file_path


def validate_path(path: Path, expected_dir: Path | None = None) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for file_path in iter_txt_files(path):
        results.append(validate_file(file_path, expected_dir=expected_dir))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Futoshiki benchmark files.")
    parser.add_argument("path", type=Path, help="File or directory to validate.")
    parser.add_argument(
        "--expected-dir",
        type=Path,
        default=None,
        help="Optional directory containing expected solution files to compare by filename.",
    )
    args = parser.parse_args(argv)

    results = validate_path(args.path, expected_dir=args.expected_dir)
    if not results:
        print(f"No .txt files found under {args.path}")
        return 1

    failures = 0
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.path} - {result.message}")
        if not result.ok:
            failures += 1

    print(f"Validated {len(results)} file(s); {failures} failure(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
