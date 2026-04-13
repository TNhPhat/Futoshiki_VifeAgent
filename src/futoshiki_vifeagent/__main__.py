from __future__ import annotations

import argparse
from typing import Sequence

from .solver.__main__ import main as solver_main
from .ui.__main__ import main as ui_main


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="futoshiki",
        description="Futoshiki application entrypoint.",
    )
    subparsers = parser.add_subparsers(dest="component")

    solver_parser = subparsers.add_parser(
        "solver",
        add_help=False,
        help="Run solver tools (benchmarking).",
    )
    solver_parser.add_argument("-h", "--help", action="store_true")
    solver_parser.add_argument("args", nargs=argparse.REMAINDER)

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        add_help=False,
        help="Run benchmark tools (run, generate, validate).",
    )
    benchmark_parser.add_argument("-h", "--help", action="store_true")
    benchmark_parser.add_argument("args", nargs=argparse.REMAINDER)

    ui_parser = subparsers.add_parser(
        "ui",
        help="Run the UI application.",
    )
    ui_parser.add_argument("args", nargs=argparse.REMAINDER)

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.component == "solver":
        solver_args = args.args
        if args.help or not solver_args or solver_args[0] in {"-h", "--help"}:
            return solver_main(["--help"])
        if solver_args and solver_args[0] == "--":
            solver_args = solver_args[1:]
        return solver_main(solver_args)

    if args.component == "benchmark":
        benchmark_args = args.args
        if args.help or not benchmark_args or benchmark_args[0] in {"-h", "--help"}:
            return solver_main(["--help"])
        if benchmark_args and benchmark_args[0] == "--":
            benchmark_args = benchmark_args[1:]
        return solver_main(benchmark_args)

    if args.component == "ui":
        ui_args = args.args
        if ui_args and ui_args[0] == "--":
            ui_args = ui_args[1:]
        return ui_main(ui_args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
