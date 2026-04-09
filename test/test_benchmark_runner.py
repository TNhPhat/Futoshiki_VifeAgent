from __future__ import annotations

import csv
from pathlib import Path

from benchmark import benchmark as benchmark_runner
from utils import StatsCsvWriter


INPUT_2X2 = """2
1,0
0,0
1
0
0,-1
"""

EXPECTED_2X2 = """2
1,2
2,1
1
0
0,-1
"""

EXPECTED_MISMATCH_2X2 = """2
1,2
1,2
1
0
0,-1
"""


def _write_case(root: Path, expected_text: str) -> None:
    input_dir = root / "input"
    expected_dir = root / "expected"
    input_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)

    case_name = "puzzle_01_2x2.txt"
    (input_dir / case_name).write_text(INPUT_2X2, encoding="utf-8")
    (expected_dir / case_name).write_text(expected_text, encoding="utf-8")


def test_benchmark_main_writes_csv_for_passing_case(tmp_path, monkeypatch):
    benchmark_root = tmp_path / "benchmark"
    _write_case(benchmark_root, EXPECTED_2X2)

    csv_path = tmp_path / "backward.csv"
    monkeypatch.setattr(
        StatsCsvWriter,
        "_solver_csv_path",
        staticmethod(lambda _solver_name: csv_path),
    )

    exit_code = benchmark_runner.main(
        [
            "--solver",
            "backward_chaining",
            "--benchmark-root",
            str(benchmark_root),
        ]
    )

    assert exit_code == 0
    assert csv_path.exists()

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["test_name"] == "puzzle_01_2x2.txt"
    assert rows[0]["ok"] == "True"
    assert rows[0]["message"] == "matches expected solution"


def test_benchmark_main_reports_mismatched_expected_grid(tmp_path, monkeypatch):
    benchmark_root = tmp_path / "benchmark"
    _write_case(benchmark_root, EXPECTED_MISMATCH_2X2)

    csv_path = tmp_path / "backward.csv"
    monkeypatch.setattr(
        StatsCsvWriter,
        "_solver_csv_path",
        staticmethod(lambda _solver_name: csv_path),
    )

    exit_code = benchmark_runner.main(
        [
            "--solver",
            "backward_chaining",
            "--benchmark-root",
            str(benchmark_root),
        ]
    )

    assert exit_code == 1
    assert csv_path.exists()

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["test_name"] == "puzzle_01_2x2.txt"
    assert rows[0]["ok"] == "False"
    assert rows[0]["message"] == "solution grid does not match expected grid"
