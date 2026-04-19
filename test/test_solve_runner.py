from __future__ import annotations

from pathlib import Path

from futoshiki_vifeagent.solver import solve as solve_runner


INPUT_2X2 = """2
1,0
0,0
1
0
0,-1
"""


def test_solve_file_prints_solution(tmp_path, capsys):
    input_path = tmp_path / "puzzle.txt"
    input_path.write_text(INPUT_2X2, encoding="utf-8")

    exit_code = solve_runner.main(
        [str(input_path), "--solver", "backward_chaining"]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "1 < 2" in output
    assert "2   1" in output


def test_solve_folder_writes_solutions(tmp_path, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    (input_dir / "puzzle.txt").write_text(INPUT_2X2, encoding="utf-8")

    exit_code = solve_runner.main(
        [
            str(input_dir),
            "--solver",
            "backward_chaining",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    output_path = output_dir / "puzzle_solution.txt"
    assert output_path.exists()
    assert "1 < 2" in output_path.read_text(encoding="utf-8")
    assert "Solved 1/1 file(s)" in capsys.readouterr().out
