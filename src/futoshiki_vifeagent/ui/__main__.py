from __future__ import annotations

import argparse
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="futoshiki-ui",
        description="UI entrypoint for Futoshiki.",
    )
    parser.parse_args(list(argv) if argv is not None else None)

    try:
        from app.game_application import GameApplication
        from models.puzzle_repository import InMemoryPuzzleRepository
    except ImportError:
        print(
            "UI runtime is not available in this checkout. "
            "Expected modules: app.game_application and models.puzzle_repository."
        )
        return 2

    GameApplication(InMemoryPuzzleRepository()).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
