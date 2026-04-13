"""
Puzzle repository: loads puzzles from the benchmark corpus and generates
new random puzzles on demand.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from benchmark.generator import FutoshikiGenerator
from constraints.inequality_constraint import InequalityConstraint
from core.parser import Parser
from core.puzzle import Puzzle

# Default benchmark input directory (relative to this file's package root)
_DEFAULT_BENCHMARK_DIR = (
    Path(__file__).resolve().parent.parent / "benchmark" / "input"
)


@dataclass(frozen=True)
class PuzzleEntry:
    path: Path
    name: str       # e.g. "puzzle_01_4x4_easy"
    size: int       # e.g. 4
    difficulty: str # e.g. "easy"


class InMemoryPuzzleRepository:
    """
    Lightweight repository that lists benchmark puzzles from disk
    and can generate new ones via FutoshikiGenerator.
    """

    def __init__(self, benchmark_dir: Path | None = None) -> None:
        self._dir = benchmark_dir or _DEFAULT_BENCHMARK_DIR
        self._parser = Parser()
        self._entries: list[PuzzleEntry] | None = None

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_entries(self) -> list[PuzzleEntry]:
        """Return all benchmark puzzle entries, sorted by size then difficulty."""
        if self._entries is None:
            self._entries = self._scan()
        return self._entries

    def _scan(self) -> list[PuzzleEntry]:
        if not self._dir.exists():
            return []

        # Filename pattern: puzzle_NN_NxN_difficulty.txt
        pattern = re.compile(r"puzzle_(\d+)_(\d+)x\d+_(\w+)\.txt$")
        entries: list[PuzzleEntry] = []

        for path in sorted(self._dir.glob("*.txt")):
            m = pattern.match(path.name)
            if m:
                size = int(m.group(2))
                difficulty = m.group(3)
                entries.append(PuzzleEntry(
                    path=path,
                    name=path.stem,
                    size=size,
                    difficulty=difficulty,
                ))

        # Sort: size asc, then difficulty order, then name
        _diff_order = {"easy": 0, "medium": 1, "hard": 2}
        entries.sort(key=lambda e: (e.size, _diff_order.get(e.difficulty, 9), e.name))
        return entries

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, path: Path) -> Puzzle:
        """Parse a puzzle file and return a Puzzle."""
        return self._parser.parse(str(path))

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, n: int, seed: int | None = None) -> Puzzle:
        """
        Generate a random Futoshiki puzzle of size n.

        Parameters
        ----------
        n : int
            Grid size (4–9 recommended).
        seed : int or None
            Random seed for reproducibility.  If None, a random seed is used.
        """
        if seed is None:
            seed = random.randint(0, 999_999)

        gen = FutoshikiGenerator(n, seed=seed)
        gen.generate_full_grid()
        gen.add_constraints(density=0.4)
        gen.create_puzzle(target_fill_ratio=0.35)

        return _generator_to_puzzle(gen)


# ---------------------------------------------------------------------------
# Helper: convert FutoshikiGenerator state → Puzzle
# ---------------------------------------------------------------------------

def _generator_to_puzzle(gen: FutoshikiGenerator) -> Puzzle:
    n = gen.n
    grid = np.array(gen.grid, dtype=int)

    h_constraints: list[InequalityConstraint] = [
        InequalityConstraint(
            cell1=(r, c),
            cell2=(r, c + 1),
            direction="<" if gen.h_const[r][c] == 1 else ">",
        )
        for r in range(n)
        for c in range(n - 1)
        if gen.h_const[r][c] != 0
    ]

    v_constraints: list[InequalityConstraint] = [
        InequalityConstraint(
            cell1=(r, c),
            cell2=(r + 1, c),
            direction="<" if gen.v_const[r][c] == 1 else ">",
        )
        for r in range(n - 1)
        for c in range(n)
        if gen.v_const[r][c] != 0
    ]

    return Puzzle(
        N=n,
        grid=grid,
        h_constraints=h_constraints,
        v_constraints=v_constraints,
    )
