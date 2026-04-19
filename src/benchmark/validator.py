from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from z3 import Distinct, Int, Or, Solver, sat

from futoshiki_vifeagent.core import ParseError, Parser, Puzzle


@dataclass(slots=True)
class ValidationResult:
    path: Path
    ok: bool
    message: str


def _progress_bar(done: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "[no files]"
    filled = int((done / total) * width)
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


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


def _build_z3_model(puzzle: Puzzle) -> tuple[Solver, list[list]]:
    size = puzzle.N
    solver = Solver()
    cells = [[Int(f"cell_{row}_{col}") for col in range(size)] for row in range(size)]

    for row in range(size):
        for col in range(size):
            solver.add(cells[row][col] >= 1)
            solver.add(cells[row][col] <= size)

    for row in range(size):
        solver.add(Distinct(cells[row]))

    for col in range(size):
        solver.add(Distinct([cells[row][col] for row in range(size)]))

    for row, col, value in puzzle.get_given_cells():
        solver.add(cells[row][col] == int(value))

    for constraint in puzzle.h_constraints:
        r1, c1 = constraint.cell1
        r2, c2 = constraint.cell2
        if constraint.direction == "<":
            solver.add(cells[r1][c1] < cells[r2][c2])
        else:
            solver.add(cells[r1][c1] > cells[r2][c2])

    for constraint in puzzle.v_constraints:
        r1, c1 = constraint.cell1
        r2, c2 = constraint.cell2
        if constraint.direction == "<":
            solver.add(cells[r1][c1] < cells[r2][c2])
        else:
            solver.add(cells[r1][c1] > cells[r2][c2])

    return solver, cells


def _extract_solution_grid(cells: list[list], model, size: int) -> np.ndarray:
    grid = np.zeros((size, size), dtype=int)
    for row in range(size):
        for col in range(size):
            grid[row, col] = model.evaluate(cells[row][col], model_completion=True).as_long()
    return grid


def solve_puzzle(puzzle: Puzzle, limit: int = 2) -> list[np.ndarray]:
    if limit <= 0:
        return []

    _initial_validation(puzzle)

    solver, cells = _build_z3_model(puzzle)
    size = puzzle.N
    solutions: list[np.ndarray] = []

    while len(solutions) < limit and solver.check() == sat:
        model = solver.model()
        solution = _extract_solution_grid(cells, model, size)
        solutions.append(solution)

        solver.add(
            Or(
                [
                    cells[row][col] != int(solution[row, col])
                    for row in range(size)
                    for col in range(size)
                ]
            )
        )

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
    files = list(iter_txt_files(path))
    if not files:
        return []

    started_at = time.perf_counter()
    print(
        f"Validating {len(files)} benchmark file(s) under {path}"
        + (f" against expected solutions in {expected_dir}" if expected_dir is not None else "")
    )

    results: list[ValidationResult] = []
    for index, file_path in enumerate(files, start=1):
        file_started_at = time.perf_counter()
        result = validate_file(file_path, expected_dir=expected_dir)
        results.append(result)

        status = "OK" if result.ok else "FAIL"
        print(
            f"{_progress_bar(index, len(files))} "
            f"{index}/{len(files)} {file_path.name} -> {status} "
            f"({result.message}, {(time.perf_counter() - file_started_at) * 1000:.2f}ms)"
        )

    total_elapsed_ms = (time.perf_counter() - started_at) * 1000
    print(f"Validation runtime: {total_elapsed_ms:.2f}ms")
    return results


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Validate Futoshiki benchmark files.",
    )
    parser.add_argument("path", type=Path, help="File or directory to validate.")
    parser.add_argument(
        "--expected-dir",
        type=Path,
        default=None,
        help="Optional directory containing expected solution files to compare by filename.",
    )
    return parser


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)

    results = validate_path(args.path, expected_dir=args.expected_dir)
    if not results:
        print(f"No .txt files found under {args.path}")
        return 1

    failures = sum(1 for result in results if not result.ok)
    successes = len(results) - failures
    print(
        f"Validation complete: passed={successes}, failed={failures}, total={len(results)}"
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
