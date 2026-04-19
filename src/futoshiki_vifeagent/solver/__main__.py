from __future__ import annotations

from typing import Sequence

from .solve import main as solve_main


def main(argv: Sequence[str] | None = None, *, prog: str = "futoshiki-solver") -> int:
    return solve_main(list(argv) if argv is not None else None, prog=prog)


if __name__ == "__main__":
    raise SystemExit(main())
