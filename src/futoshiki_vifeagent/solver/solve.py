from __future__ import annotations

import argparse
from pathlib import Path

from futoshiki_vifeagent.core import Formatter, Parser
from futoshiki_vifeagent.solver import (
    AStarSolver,
    BackwardChaining,
    BacktrackingForwardChaining,
    BaseSolver,
    BruteForceSolver,
    ForwardChaining,
    ForwardThenBackwardChaining,
)
from heuristics import (
    AC3Heuristic,
    DomainSizeHeuristic,
    EmptyCellHeuristic,
    MinConflictsHeuristic,
)


def _solver_registry() -> dict[str, BaseSolver | type[BaseSolver]]:
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


def _solver_keys() -> str:
    return ", ".join(sorted(_solver_registry()))


def _make_solver(solver_key: str) -> BaseSolver:
    registry = _solver_registry()
    if solver_key not in registry:
        raise ValueError(f"unknown solver '{solver_key}'. valid values: {_solver_keys()}")

    entry = registry[solver_key]
    return entry if isinstance(entry, BaseSolver) else entry()


def _iter_input_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".txt":
            raise ValueError(f"input file must be a .txt file: {input_path}")
        return [input_path]

    if input_path.is_dir():
        files = sorted(path for path in input_path.glob("*.txt") if path.is_file())
        if not files:
            raise FileNotFoundError(f"no .txt files found in: {input_path}")
        return files

    raise FileNotFoundError(f"input path not found: {input_path}")


def _solve_file(input_path: Path, solver_key: str) -> tuple[str | None, str]:
    parser = Parser()
    formatter = Formatter()
    puzzle = parser.parse(str(input_path))
    solver = _make_solver(solver_key)
    solution, stats = solver.solve(puzzle.copy())

    if solution is None:
        return None, (
            f"{input_path}: no solution found "
            f"({solver.get_name()}, {stats.time_ms:.2f}ms)"
        )

    output = formatter.format(solution)
    summary = (
        f"{input_path}: solved with {solver.get_name()} "
        f"({stats.time_ms:.2f}ms, {stats.memory_kb:.1f}KB)"
    )
    return output, summary


def solve_path(input_path: Path, solver_key: str, output_dir: Path | None = None) -> int:
    input_files = _iter_input_files(input_path)
    if len(input_files) == 1 and input_path.is_file():
        output, summary = _solve_file(input_files[0], solver_key)
        if output is None:
            print(summary)
            return 1
        print(output)
        return 0

    destination = output_dir or (input_path / "solutions")
    destination.mkdir(parents=True, exist_ok=True)

    failed = 0
    for file_path in input_files:
        output, summary = _solve_file(file_path, solver_key)
        if output is None:
            failed += 1
            print(f"FAIL {summary}")
            continue

        output_path = destination / f"{file_path.stem}_solution.txt"
        output_path.write_text(output + "\n", encoding="utf-8")
        print(f"OK {file_path.name} -> {output_path}")

    print(
        f"Solved {len(input_files) - failed}/{len(input_files)} file(s). "
        f"Output: {destination}"
    )
    return 0 if failed == 0 else 1


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Solve one Futoshiki .txt file or every .txt file in a folder.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Puzzle .txt file or directory containing puzzle .txt files.",
    )
    parser.add_argument(
        "--solver",
        default="backward_chaining",
        help=f"Solver key. Valid values: {_solver_keys()}.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for folder-mode solved outputs. Defaults to <input>/solutions.",
    )
    return parser


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)
    try:
        return solve_path(
            input_path=args.input,
            solver_key=args.solver,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(1, f"{parser.prog}: error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
