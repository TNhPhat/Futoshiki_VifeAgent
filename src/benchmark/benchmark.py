from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

import numpy as np

from futoshiki_vifeagent.core import Parser
from futoshiki_vifeagent.solver import (
    AStarSolver,
    BackwardChaining,
    BacktrackingForwardChaining,
    BruteForceSolver,
    ForwardChaining,
    ForwardThenBackwardChaining,
)
from heuristics import (
    EmptyCellHeuristic,
    DomainSizeHeuristic,
    MinConflictsHeuristic,
    AC3Heuristic,
)
from futoshiki_vifeagent.solver import BaseSolver
from futoshiki_vifeagent.utils import StatsCsvWriter


@dataclass
class BenchmarkRow:
    solver_name: str
    puzzle_size: int
    input_file: str
    ok: bool
    message: str
    time_ms: float
    memory_kb: float
    inference_count: int
    node_expansions: int
    backtracks: int
    completion_ratio: float


def _solver_registry() -> Dict[str, BaseSolver | type[BaseSolver]]:
    return {
        "forward_chaining": ForwardChaining,
        "forward_then_backward_chaining": ForwardThenBackwardChaining,
        "backtracking_forward_chaining": BacktrackingForwardChaining,
        "backward_chaining": BackwardChaining,
        "brute_force": BruteForceSolver,
        "astar_h1": AStarSolver(EmptyCellHeuristic()),
        "astar_h2": AStarSolver(DomainSizeHeuristic()),
        "astar_h3": AStarSolver(MinConflictsHeuristic()),
        "astar_h4": AStarSolver(AC3Heuristic()),
    }


_SIZE_RE = re.compile(r"_(\d+)x\d+")


def _puzzle_n_from_filename(name: str) -> int | None:
    m = _SIZE_RE.search(name)
    return int(m.group(1)) if m else None


def _iter_input_files(input_dir: Path, max_n: int | None = None) -> Iterable[Path]:
    for file_path in sorted(input_dir.glob("*.txt")):
        if not file_path.is_file():
            continue
        if max_n is not None:
            n = _puzzle_n_from_filename(file_path.name)
            if n is not None and n > max_n:
                continue
        yield file_path


def _progress_bar(done: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "[no cases]"
    ratio = done / total
    filled = int(ratio * width)
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _evaluate_case(
    parser: Parser,
    solver_name: str,
    solver: BaseSolver,
    input_path: Path,
    expected_dir: Path,
) -> BenchmarkRow:
    puzzle = parser.parse(str(input_path))
    solution, stats = solver.solve(puzzle.copy())

    expected_path = expected_dir / input_path.name
    if not expected_path.exists():
        return BenchmarkRow(
            solver_name=solver_name,
            puzzle_size=puzzle.N,
            input_file=input_path.name,
            ok=False,
            message=f"missing expected file: {expected_path.name}",
            time_ms=stats.time_ms,
            memory_kb=stats.memory_kb,
            inference_count=stats.inference_count,
            node_expansions=stats.node_expansions,
            backtracks=stats.backtracks,
            completion_ratio=stats.completion_ratio,
        )

    if solution is None:
        return BenchmarkRow(
            solver_name=solver_name,
            puzzle_size=puzzle.N,
            input_file=input_path.name,
            ok=False,
            message="solver returned no solution",
            time_ms=stats.time_ms,
            memory_kb=stats.memory_kb,
            inference_count=stats.inference_count,
            node_expansions=stats.node_expansions,
            backtracks=stats.backtracks,
            completion_ratio=stats.completion_ratio,
        )

    if not solution.is_complete():
        return BenchmarkRow(
            solver_name=solver_name,
            puzzle_size=puzzle.N,
            input_file=input_path.name,
            ok=False,
            message="solution is incomplete",
            time_ms=stats.time_ms,
            memory_kb=stats.memory_kb,
            inference_count=stats.inference_count,
            node_expansions=stats.node_expansions,
            backtracks=stats.backtracks,
            completion_ratio=stats.completion_ratio,
        )

    expected = parser.parse(str(expected_path))
    is_match = bool(np.array_equal(solution.grid, expected.grid))
    message = (
        "matches expected solution"
        if is_match
        else "solution grid does not match expected grid"
    )

    return BenchmarkRow(
        solver_name=solver_name,
        puzzle_size=puzzle.N,
        input_file=input_path.name,
        ok=is_match,
        message=message,
        time_ms=stats.time_ms,
        memory_kb=stats.memory_kb,
        inference_count=stats.inference_count,
        node_expansions=stats.node_expansions,
        backtracks=stats.backtracks,
        completion_ratio=stats.completion_ratio,
    )


def run_benchmark(solver_key: str, benchmark_root: Path, max_n: int | None = None) -> tuple[list[tuple[str, BenchmarkRow]], int]:
    registry = _solver_registry()
    if solver_key not in registry:
        valid = ", ".join(sorted(registry.keys()))
        raise ValueError(f"unknown solver '{solver_key}'. valid values: {valid}")

    input_dir = benchmark_root / "input"
    expected_dir = benchmark_root / "expected"
    if not input_dir.exists():
        raise FileNotFoundError(f"benchmark input directory not found: {input_dir}")
    if not expected_dir.exists():
        raise FileNotFoundError(f"benchmark expected directory not found: {expected_dir}")

    entry = registry[solver_key]
    solver = entry if isinstance(entry, BaseSolver) else entry()
    solver_name = solver.get_name()
    parser = Parser()
    rows: list[tuple[str, BenchmarkRow]] = []
    failed = 0

    input_files = list(_iter_input_files(input_dir, max_n=max_n))
    if not input_files:
        raise FileNotFoundError(f"no benchmark input files found in: {input_dir}")

    total = len(input_files)
    max_n_label = f", max_n={max_n}" if max_n is not None else ""
    print(
        f"Running benchmark: solver={solver_name} ({solver_key}), "
        f"cases={total}{max_n_label}, root={benchmark_root}"
    )

    for idx, input_path in enumerate(input_files, start=1):
        row = _evaluate_case(
            parser=parser,
            solver_name=solver_name,
            solver=solver,
            input_path=input_path,
            expected_dir=expected_dir,
        )
        if not row.ok:
            failed += 1
        rows.append((input_path.name, row))

        status = "OK" if row.ok else "FAIL"
        print(
            f"{_progress_bar(idx, total)} "
            f"{idx}/{total} {input_path.name} -> {status} "
            f"({row.time_ms:.2f}ms, {row.memory_kb:.1f}KB)"
        )

    print(
        f"Benchmark complete: passed={total - failed}, failed={failed}, total={total}"
    )

    return rows, failed


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Run solver benchmarks against expected puzzle solutions."
    )
    parser.add_argument(
        "--solver",
        required=True,
        help=(
            "Solver key: forward_chaining, forward_then_backward_chaining, "
            "backtracking_forward_chaining, "
            "backward_chaining, brute_force, "
            "astar_h1, astar_h2, astar_h3, astar_h4, all"
        ),
    )
    parser.add_argument(
        "--benchmark-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Benchmark directory containing input/ and expected/.",
    )
    parser.add_argument(
        "--max-n",
        type=int,
        default=None,
        metavar="N",
        help="Skip puzzles larger than NxN (e.g. --max-n 6 runs only 4x4..6x6).",
    )
    return parser


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)
    if (args.solver == "all"):
        for solver in _solver_registry():
            rows, failed = run_benchmark(
                solver_key=solver,
                benchmark_root=args.benchmark_root,
                max_n=args.max_n,
            )
            solver_name = rows[0][1].solver_name
            csv_path = StatsCsvWriter.write_many(rows, solver_name=solver_name)
            print(f"Stats written to: {csv_path}")
    else:
        rows, failed = run_benchmark(
            solver_key=args.solver,
            benchmark_root=args.benchmark_root,
            max_n=args.max_n,
        )
        solver_name = rows[0][1].solver_name
        csv_path = StatsCsvWriter.write_many(rows, solver_name=solver_name)
        print(f"Stats written to: {csv_path}")
        return 0 if failed == 0 else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
