from __future__ import annotations

import argparse
import random
from pathlib import Path

from z3 import Distinct, Int, Or, Solver, sat

BENCHMARK_SPECS = []
_FILE_INDEX = 1
for _size in (4, 5, 6, 7, 8, 9):
    for _difficulty, _fill_ratio, _density in (
        ("easy", 0.50, 0.55),
        ("medium", 0.35, 0.45),
        ("medium", 0.30, 0.40),
        ("hard", 0.22, 0.35),
    ):
        BENCHMARK_SPECS.append(
            {
                "filename": f"puzzle_{_FILE_INDEX:02d}_{_size}x{_size}_{_difficulty}.txt",
                "size": _size,
                "seed": 1000 + _FILE_INDEX,
                "fill_ratio": _fill_ratio,
                "density": _density,
            }
        )
        _FILE_INDEX += 1

class FutoshikiGenerator:
    def __init__(self, n, seed=None):
        self.n = n
        self.grid = [[0] * n for _ in range(n)]
        self.h_const = [[0] * (n - 1) for _ in range(n)]
        self.v_const = [[0] * n for _ in range(n - 1)]
        self.solution_grid = []
        self.rng = random.Random(seed)

    def is_valid(self, grid, r, c, val):
        for i in range(self.n):
            if grid[r][i] == val or grid[i][c] == val:
                return False

        if c > 0 and self.h_const[r][c - 1] != 0 and grid[r][c - 1] != 0:
            if self.h_const[r][c - 1] == 1 and not (grid[r][c - 1] < val): return False
            if self.h_const[r][c - 1] == -1 and not (grid[r][c - 1] > val): return False
            
        if c < self.n - 1 and self.h_const[r][c] != 0 and grid[r][c + 1] != 0:
            if self.h_const[r][c] == 1 and not (val < grid[r][c + 1]): return False
            if self.h_const[r][c] == -1 and not (val > grid[r][c + 1]): return False

        if r > 0 and self.v_const[r - 1][c] != 0 and grid[r - 1][c] != 0:
            if self.v_const[r - 1][c] == 1 and not (grid[r - 1][c] < val): return False
            if self.v_const[r - 1][c] == -1 and not (grid[r - 1][c] > val): return False
            
        if r < self.n - 1 and self.v_const[r][c] != 0 and grid[r + 1][c] != 0:
            if self.v_const[r][c] == 1 and not (val < grid[r + 1][c]): return False
            if self.v_const[r][c] == -1 and not (val > grid[r + 1][c]): return False

        return True

    def find_empty(self, grid):
        """
        Đã tối ưu bằng heuristic MRV (Minimum Remaining Values).
        Luôn ưu tiên ô có ít lựa chọn hợp lệ nhất để cắt tỉa cây tìm kiếm.
        """
        min_options = self.n + 1
        best_cell = None
        
        for r in range(self.n):
            for c in range(self.n):
                if grid[r][c] == 0:
                    options = 0
                    for val in range(1, self.n + 1):
                        if self.is_valid(grid, r, c, val):
                            options += 1
                    
                    # Cắt tỉa nhánh tuyệt đối: Tìm thấy ô không thể điền số nào
                    if options == 0:
                        return (r, c)
                        
                    if options < min_options:
                        min_options = options
                        best_cell = (r, c)
                        # Cắt tỉa nhanh: Nếu có ô chỉ có 1 lựa chọn duy nhất, lấy luôn
                        if min_options == 1:
                            return best_cell
                            
        return best_cell

    def count_solutions(self, grid, limit=2):
        solver, cells = self._build_base_solver()
        return self._count_solutions_with_base(solver, cells, grid, limit=limit)

    def _build_base_solver(self):
        solver = Solver()
        cells = [[Int(f"cell_{r}_{c}") for c in range(self.n)] for r in range(self.n)]

        for r in range(self.n):
            for c in range(self.n):
                solver.add(cells[r][c] >= 1, cells[r][c] <= self.n)

        for r in range(self.n):
            solver.add(Distinct(cells[r]))

        for c in range(self.n):
            solver.add(Distinct([cells[r][c] for r in range(self.n)]))

        for r in range(self.n):
            for c in range(self.n - 1):
                if self.h_const[r][c] == 1:
                    solver.add(cells[r][c] < cells[r][c + 1])
                elif self.h_const[r][c] == -1:
                    solver.add(cells[r][c] > cells[r][c + 1])

        for r in range(self.n - 1):
            for c in range(self.n):
                if self.v_const[r][c] == 1:
                    solver.add(cells[r][c] < cells[r + 1][c])
                elif self.v_const[r][c] == -1:
                    solver.add(cells[r][c] > cells[r + 1][c])

        return solver, cells

    def _count_solutions_with_base(self, solver, cells, grid, limit=2):
        if limit <= 0:
            return 0

        solver.push()

        for r in range(self.n):
            for c in range(self.n):
                if grid[r][c] != 0:
                    solver.add(cells[r][c] == grid[r][c])

        count = 0
        while count < limit and solver.check() == sat:
            model = solver.model()
            count += 1
            solver.add(
                Or(
                    [
                        cells[r][c] != model.evaluate(cells[r][c], model_completion=True).as_long()
                        for r in range(self.n)
                        for c in range(self.n)
                    ]
                )
            )

        solver.pop()
        return count

    def generate_full_grid(self):
        def fill(grid):
            empty = self.find_empty(grid)
            if not empty: return True
            r, c = empty
            
            vals = list(range(1, self.n + 1))
            self.rng.shuffle(vals)
            
            for val in vals:
                if self.is_valid(grid, r, c, val):
                    grid[r][c] = val
                    if fill(grid):
                        return True
                    grid[r][c] = 0
            return False
            
        fill(self.grid)
        self.solution_grid = [row[:] for row in self.grid]

    def add_constraints(self, density=0.4):
        for r in range(self.n):
            for c in range(self.n - 1):
                if self.rng.random() < density:
                    self.h_const[r][c] = 1 if self.solution_grid[r][c] < self.solution_grid[r][c + 1] else -1

        for r in range(self.n - 1):
            for c in range(self.n):
                if self.rng.random() < density:
                    self.v_const[r][c] = 1 if self.solution_grid[r][c] < self.solution_grid[r + 1][c] else -1

    def _filled_cells(self):
        return sum(1 for row in self.grid for value in row if value != 0)

    def create_puzzle(self, target_fill_ratio=None):
        cells = [(r, c) for r in range(self.n) for c in range(self.n)]
        self.rng.shuffle(cells)
        solver, z3_cells = self._build_base_solver()
        target_filled = None
        if target_fill_ratio is not None:
            target_filled = max(1, int(round(self.n * self.n * target_fill_ratio)))
        
        for r, c in cells:
            if target_filled is not None and self._filled_cells() <= target_filled:
                break

            temp = self.grid[r][c]
            self.grid[r][c] = 0
            
            if self._count_solutions_with_base(solver, z3_cells, self.grid, limit=2) != 1:
                self.grid[r][c] = temp

    def format_output(self, target_grid):
        lines = [
            str(self.n),
        ]
        for row in target_grid:
            lines.append(",".join(map(str, row)))

        for row in self.h_const:
            lines.append(",".join(map(str, row)))

        for row in self.v_const:
            lines.append(",".join(map(str, row)))
            
        return "\n".join(lines)

def _serialize_benchmark(n, grid, h_rows, v_rows):
    lines = [str(n)]
    lines.extend(",".join(map(str, row)) for row in grid)
    lines.extend(",".join(map(str, row)) for row in h_rows)
    lines.extend(",".join(map(str, row)) for row in v_rows)
    return "\n".join(lines) + "\n"


def _constraint_rows_from_puzzle(puzzle):
    h_rows = [[0] * (puzzle.N - 1) for _ in range(puzzle.N)]
    for constraint in puzzle.h_constraints:
        r, c = constraint.cell1
        h_rows[r][c] = 1 if constraint.direction == "<" else -1

    v_rows = [[0] * puzzle.N for _ in range(puzzle.N - 1)]
    for constraint in puzzle.v_constraints:
        r, c = constraint.cell1
        v_rows[r][c] = 1 if constraint.direction == "<" else -1

    return h_rows, v_rows


def generate_benchmark_corpus(output_root: Path) -> list[Path]:
    input_dir = output_root / "input"
    expected_dir = output_root / "expected"
    input_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)

    # from futoshiki_vifeagent.benchmark import validator

    written_files: list[Path] = []

    for spec in BENCHMARK_SPECS:
        generator = FutoshikiGenerator(spec["size"], seed=spec["seed"])
        generator.generate_full_grid()
        generator.add_constraints(density=spec["density"])
        generator.create_puzzle(target_fill_ratio=spec["fill_ratio"])

        h_rows = [row[:] for row in generator.h_const]
        v_rows = [row[:] for row in generator.v_const]

        input_file = input_dir / spec["filename"]
        expected_file = expected_dir / spec["filename"]

        input_file.write_text(
            _serialize_benchmark(generator.n, generator.grid, h_rows, v_rows),
            encoding="utf-8",
        )
        expected_file.write_text(
            _serialize_benchmark(generator.n, generator.solution_grid, h_rows, v_rows),
            encoding="utf-8",
        )

        # validation = validator.validate_file(input_file, expected_dir=expected_dir)
        # if not validation.ok:
        #     raise RuntimeError(f"{input_file}: {validation.message}")

        written_files.extend([input_file, expected_file])

    return written_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the benchmark corpus for the project."
    )
    parser.add_argument(
        "--benchmark-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Benchmark directory that contains the input and expected folders.",
    )
    args = parser.parse_args(argv)

    written_files = generate_benchmark_corpus(args.benchmark_root)
    print(f"Generated {len(written_files) // 2} benchmark pair(s) under {args.benchmark_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
