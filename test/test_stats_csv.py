from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from utils import Stats, StatsCsvWriter


def test_write_one_stats_to_csv(tmp_path, monkeypatch):
    output_path = tmp_path / "stats.csv"
    monkeypatch.setattr(
        StatsCsvWriter,
        "_solver_csv_path",
        staticmethod(lambda _solver_name: output_path),
    )
    stats = Stats(
        time_ms=12.5,
        memory_kb=100.0,
        inference_count=20,
        node_expansions=3,
        backtracks=1,
        completion_ratio=0.5,
    )

    StatsCsvWriter.write_stat("test_case_1", stats, solver_name="Backward Chaining")

    with output_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["test_name"] == "test_case_1"
    assert rows[0]["time_ms"] == "12.5"
    assert rows[0]["memory_kb"] == "100.0"
    assert rows[0]["inference_count"] == "20"
    assert rows[0]["node_expansions"] == "3"
    assert rows[0]["backtracks"] == "1"
    assert rows[0]["completion_ratio"] == "0.5"


def test_write_many_supports_future_added_metrics(tmp_path, monkeypatch):
    @dataclass
    class FutureStats:
        time_ms: float
        memory_kb: float
        inference_count: int
        node_expansions: int
        backtracks: int
        cache_hits: int

    output_path = tmp_path / "future_stats.csv"
    monkeypatch.setattr(
        StatsCsvWriter,
        "_solver_csv_path",
        staticmethod(lambda _solver_name: output_path),
    )
    records = [
        ("case_1", FutureStats(1.0, 2.0, 3, 4, 5, 6)),
        ("case_2", FutureStats(10.0, 20.0, 30, 40, 50, 60)),
    ]

    StatsCsvWriter.write_many(records, solver_name="Backward Chaining")

    with output_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert "cache_hits" in (reader.fieldnames or [])
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["test_name"] == "case_1"
    assert rows[1]["test_name"] == "case_2"
    assert rows[0]["cache_hits"] == "6"
    assert rows[1]["cache_hits"] == "60"


def test_solver_name_maps_to_resource_output_path():
    path = StatsCsvWriter._solver_csv_path("Backward Chaining (Generate-and-Test SLD)")
    expected_suffix = Path("resource") / "output" / "backward_chaining_generate_and_test_sld.csv"
    assert str(path).endswith(str(expected_suffix))
