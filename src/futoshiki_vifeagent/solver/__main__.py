from __future__ import annotations

import argparse
from typing import Sequence

from futoshiki_vifeagent.benchmark import benchmark as benchmark_runner
from benchmark import generator as benchmark_generator
from benchmark import validator as benchmark_validator
from benchmark import visualize as benchmark_visualize


def main(argv: Sequence[str] | None = None) -> int:
    argv_list = list(argv) if argv is not None else []

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
            "Solver key: forward_chaining, forward_then_backward_chaining, "
            "backtracking_forward_chaining, "
            "backward_chaining, brute_force, "
            "astar_h1, astar_h2, astar_h3"
        ),
    )
    run_parser.add_argument(
        "--benchmark-root",
        default=None,
        help="Optional benchmark directory containing input/ and expected/.",
    )
    run_parser.add_argument(
        "--max-n",
        type=int,
        default=None,
        metavar="N",
        help="Skip puzzles larger than NxN (e.g. --max-n 6 runs only 4x4..6x6).",
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

    visualize_parser = subparsers.add_parser(
        "visualize",
        help="Visualize benchmark CSVs as line charts and a completion-ratio heatmap.",
    )
    visualize_parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory containing benchmark CSV files (default: resource/output/).",
    )
    visualize_parser.add_argument(
        "--output-dir",
        default=None,
        help="Save PNGs here instead of displaying interactively.",
    )
    visualize_parser.add_argument(
        "--latex-dir",
        default=None,
        help="Generate LaTeX tables and save .tex files to this directory.",
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
        max_n = getattr(args, "max_n", None)
        benchmark_argv: list[str] = ["--solver", solver_key]
        if benchmark_root:
            benchmark_argv.extend(["--benchmark-root", benchmark_root])
        if max_n is not None:
            benchmark_argv.extend(["--max-n", str(max_n)])
        return benchmark_runner.main(benchmark_argv)

    if args.command == "visualize":
        visualize_argv: list[str] = []
        if args.data_dir:
            visualize_argv.extend(["--data-dir", args.data_dir])
        if args.output_dir:
            visualize_argv.extend(["--output-dir", args.output_dir])
        if args.latex_dir:
            visualize_argv.extend(["--latex-dir", args.latex_dir])
        return benchmark_visualize.main(visualize_argv)

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
