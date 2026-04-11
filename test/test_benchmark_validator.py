from __future__ import annotations

from pathlib import Path

from benchmark import validator as benchmark_validator
from futoshiki_vifeagent.core import Parser


UNIQUE_2X2 = """2
1,2
2,1
0
0
0,0
"""


MULTIPLE_2X2 = """2
0,0
0,0
0
0
0,0
"""


UNSAT_2X2 = """2
0,0
0,0
1
-1
1,1
"""


def _write_puzzle(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_validate_file_reports_unique_solution(tmp_path: Path):
    puzzle_path = tmp_path / "unique_2x2.txt"
    _write_puzzle(puzzle_path, UNIQUE_2X2)

    result = benchmark_validator.validate_file(puzzle_path)

    assert result.ok is True
    assert result.message == "unique solution"


def test_validate_file_reports_multiple_solutions(tmp_path: Path):
    puzzle_path = tmp_path / "multiple_2x2.txt"
    _write_puzzle(puzzle_path, MULTIPLE_2X2)

    result = benchmark_validator.validate_file(puzzle_path)

    assert result.ok is False
    assert result.message == "puzzle has multiple solutions"


def test_validate_file_reports_unsat(tmp_path: Path):
    puzzle_path = tmp_path / "unsat_2x2.txt"
    _write_puzzle(puzzle_path, UNSAT_2X2)

    result = benchmark_validator.validate_file(puzzle_path)

    assert result.ok is False
    assert result.message == "unsatisfiable puzzle"


def test_solve_puzzle_enumerates_with_limit(tmp_path: Path):
    puzzle_path = tmp_path / "multiple_limit_2x2.txt"
    _write_puzzle(puzzle_path, MULTIPLE_2X2)

    parser = Parser()
    puzzle = parser.parse(str(puzzle_path))

    solutions = benchmark_validator.solve_puzzle(puzzle, limit=2)

    assert len(solutions) == 2
