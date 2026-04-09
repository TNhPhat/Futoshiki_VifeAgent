from __future__ import annotations

import csv
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


class StatsCsvWriter:
    """
    Persist solver statistics to CSV using dynamic field discovery.

    The writer does not hard-code metric names. It infers columns from each
    record, so if new metrics are added to Stats in the future they will be
    exported automatically.
    """

    @staticmethod
    def write_stat(test_name: str, stats: Any, solver_name: str) -> Path:
        output_path = StatsCsvWriter._solver_csv_path(solver_name)
        row = {"test_name": test_name, **StatsCsvWriter._to_row(stats)}
        StatsCsvWriter._append_row(output_path=output_path, row=row)
        return output_path

    @staticmethod
    def write_many(
        records: Iterable[tuple[str, Any]],
        solver_name: str,
    ) -> Path:
        rows = []
        for test_name, stats in records:
            rows.append({"test_name": test_name, **StatsCsvWriter._to_row(stats)})

        if not rows:
            raise ValueError("records must not be empty")

        output_path = StatsCsvWriter._solver_csv_path(solver_name)
        fieldnames = StatsCsvWriter._fieldnames_from_rows(rows)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return output_path

    @staticmethod
    def _append_row(output_path: Path, row: dict[str, Any]) -> None:
        if not output_path.exists():
            fieldnames = StatsCsvWriter._fieldnames_from_rows([row])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row)
            return

        with output_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            existing_rows = list(reader)
            existing_fieldnames = reader.fieldnames or []

        merged_fieldnames = StatsCsvWriter._fieldnames_from_rows(
            [{key: "" for key in existing_fieldnames}, row]
        )

        if merged_fieldnames == existing_fieldnames:
            with output_path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=merged_fieldnames)
                writer.writerow(row)
            return

        existing_rows.append(row)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=merged_fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)

    @staticmethod
    def _solver_csv_path(solver_name: str) -> Path:
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "resource" / "output"
        safe_name = "".join(ch.lower() if ch.isalnum() else "_" for ch in solver_name)
        safe_name = "_".join(part for part in safe_name.split("_") if part)
        if not safe_name:
            safe_name = "solver"
        return output_dir / f"{safe_name}.csv"

    @staticmethod
    def _to_row(record: Any) -> dict[str, Any]:
        if is_dataclass(record):
            return asdict(record)

        if isinstance(record, Mapping):
            return dict(record)

        if hasattr(record, "__dict__"):
            return dict(vars(record))

        raise TypeError(
            "record must be a dataclass instance, mapping, or object with __dict__"
        )

    @staticmethod
    def _fieldnames_from_rows(rows: list[Mapping[str, Any]]) -> list[str]:
        fieldnames: list[str] = ["test_name"]
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        return fieldnames
