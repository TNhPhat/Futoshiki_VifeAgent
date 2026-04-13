from __future__ import annotations

import argparse
from typing import Sequence

from futoshiki_vifeagent.benchmark import benchmark as benchmark_runner
from benchmark import generator as benchmark_generator
from benchmark import validator as benchmark_validator


def main(argv: Sequence[str] | None = None) -> int:
    argv_list = list(argv) if argv is not None else []
    if argv_list and argv_list[0].startswith("-"):
        argv_list = ["run", *argv_list]

    parser = argparse.ArgumentParser(
        prog="futoshiki-solver",
        description="Solver-side and benchmark tools for Futoshiki.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="Run solver benchmark against expected benchmark corpus.",
    )
    run_parser.add_argument(
        "--solver",
        default="backward_chaining",
        help=(
            "Solver key: forward_chaining, forward_then_ac3_backward_chaining, "
            "backtracking_forward_chaining, "
            "backward_chaining, ac3_backward_chaining, brute_force, "
            "astar_h1, astar_h2, astar_h3"
        ),
    )
    run_parser.add_argument(
        "--benchmark-root",
        default=None,
        help="Optional benchmark directory containing input/ and expected/.",
    )

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate benchmark input/expected corpus.",
    )
    generate_parser.add_argument(
        "--benchmark-root",
        default=None,
        help="Optional benchmark directory that will contain input/ and expected/.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate benchmark input files and optional expected solutions.",
    )
    validate_parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="File or directory to validate. Defaults to <benchmark-root>/input.",
    )
    validate_parser.add_argument(
        "--expected-dir",
        default=None,
        help="Optional directory containing expected solution files.",
    )
    validate_parser.add_argument(
        "--benchmark-root",
        default=None,
        help="Optional benchmark directory containing input/ and expected/.",
    )

    args = parser.parse_args(argv_list or None)

    if args.command is None:
        return benchmark_runner.main(["--solver", "backward_chaining"])

    if args.command == "run":
        solver_key = getattr(args, "solver", "backward_chaining")
        benchmark_root = getattr(args, "benchmark_root", None)
        benchmark_argv: list[str] = ["--solver", solver_key]
        if benchmark_root:
            benchmark_argv.extend(["--benchmark-root", benchmark_root])
        return benchmark_runner.main(benchmark_argv)

    if args.command == "generate":
        generator_argv: list[str] = []
        if args.benchmark_root:
            generator_argv.extend(["--benchmark-root", args.benchmark_root])
        return benchmark_generator.main(generator_argv)

    if args.command == "validate":
        path = args.path
        expected_dir = args.expected_dir

        validate_argv: list[str] = []
        if path is None:
            root = args.benchmark_root or "src/benchmark"
            validate_argv.append(f"{root}/input")
            if expected_dir is None:
                expected_dir = f"{root}/expected"
        else:
            validate_argv.append(path)

        if expected_dir:
            validate_argv.extend(["--expected-dir", expected_dir])
        return benchmark_validator.main(validate_argv)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
