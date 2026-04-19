from __future__ import annotations

import argparse
from typing import Protocol, Sequence

from benchmark import benchmark as benchmark_runner
from benchmark import generator as benchmark_generator
from benchmark import validator as benchmark_validator
from benchmark import visualize as benchmark_visualize


class ToolMain(Protocol):
    def __call__(
        self,
        argv: list[str] | None = None,
        *,
        prog: str | None = None,
    ) -> int: ...


_TOOLS: dict[str, tuple[ToolMain, str]] = {
    "run": (
        benchmark_runner.main,
        "Run solver benchmark against expected benchmark corpus.",
    ),
    "generate": (
        benchmark_generator.main,
        "Generate benchmark input/expected corpus.",
    ),
    "visualize": (
        benchmark_visualize.main,
        "Visualize benchmark CSVs as line charts and a completion-ratio heatmap.",
    ),
    "validate": (
        benchmark_validator.main,
        "Validate benchmark input files and optional expected solutions.",
    ),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="futoshiki benchmark",
        description="Benchmark tools for Futoshiki.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            ["commands:"]
            + [f"  {name:<9} {help_text}" for name, (_, help_text) in _TOOLS.items()]
        ),
    )
    parser.add_argument("command", nargs="?", choices=tuple(_TOOLS))
    parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command is None:
        parser.print_help()
        return 2

    tool_main, _help_text = _TOOLS[args.command]
    tool_args = list(args.args)
    if tool_args and tool_args[0] == "--":
        tool_args = tool_args[1:]
    return tool_main(tool_args, prog=f"{parser.prog} {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
