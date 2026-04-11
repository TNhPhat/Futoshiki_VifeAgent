from __future__ import annotations

import argparse
from typing import Sequence

from futoshiki_vifeagent.benchmark import benchmark as benchmark_runner


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="futoshiki-solver",
        description="Solver-side tools for Futoshiki.",
    )
    parser.add_argument(
        "--solver",
        default="backward_chaining",
        help=(
            "Solver key: forward_chaining, forward_then_ac3_backward_chaining, "
            "backtracking_forward_chaining, "
            "backward_chaining, ac3_backward_chaining, brute_force"
        ),
    )
    parser.add_argument(
        "--benchmark-root",
        default=None,
        help="Optional benchmark directory containing input/ and expected/.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    benchmark_argv: list[str] = ["--solver", args.solver]
    if args.benchmark_root:
        benchmark_argv.extend(["--benchmark-root", args.benchmark_root])

    return benchmark_runner.main(benchmark_argv)


if __name__ == "__main__":
    raise SystemExit(main())
