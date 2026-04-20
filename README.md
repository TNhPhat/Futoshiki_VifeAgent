# Futoshiki VifeAgent

Futoshiki VifeAgent is a Python project for solving, validating, benchmarking,
and visualizing Futoshiki puzzles. The repository includes several solver
strategies, a command-line interface, a Pygame UI entry point, benchmark corpus
tools, and tests for the core puzzle, inference, solver, and benchmark flows.

Futoshiki is a Latin-square puzzle: each row and column must contain every
number from `1` to `N` exactly once, while also satisfying inequality
constraints between adjacent cells.

## Features

- Parse Futoshiki puzzle files with grid values and horizontal or vertical
  inequality constraints.
- Solve a single puzzle file or a directory of puzzle files.
- Compare multiple solver strategies:
  - `forward_chaining`
  - `forward_then_backward_chaining`
  - `backtracking_forward_chaining`
  - `backward_chaining`
  - `brute_force`
  - `astar_h1`
  - `astar_h2`
  - `astar_h3`
  - `astar_h4`
- Generate, validate, run, and visualize benchmark cases.
- Export benchmark metrics as CSV files and optional PNG or LaTeX outputs.
- Launch a local UI application through the packaged CLI.

## Project Layout

```text
src/
  app/                     Pygame application wiring and UI input flow
  benchmark/               Benchmark runner, generator, validator, visualizer
  constraints/             Row, column, inequality, and AC-3 constraints
  core/                    Puzzle model, parser, and formatter
  fol/                     Predicate, knowledge base, and FOL utilities
  heuristics/              A* heuristic implementations
  inference/               Forward and backward chaining engines
  models/                  UI-facing board, game state, and repository models
  search/                  A* state and search logic
  solver/                  Solver implementations
  ui/                      Pygame rendering components
  futoshiki_vifeagent/     Package entry points and compatibility exports
test/                      Unit and integration tests
docs/                      Design notes and algorithm documentation
resource/                  Generated plots, LaTeX, and benchmark outputs
```

## Requirements

- Python `3.13`
- `uv` for dependency management

The project is configured in `pyproject.toml` and depends on `numpy`,
`pygame`, `z3-solver`, `matplotlib`, `seaborn`, and `pandas`. Test execution
uses `pytest`.

## Setup and Build

From the repository root:

```powershell
uv sync --group dev
```

This creates or updates the local virtual environment and installs the project
with development dependencies.

To verify the installation:

```powershell
uv run futoshiki --help
uv run pytest
```

If you only need runtime dependencies, omit the development group:

```powershell
uv sync
```

## Puzzle File Format

Puzzle files are plain text files. Blank lines and lines beginning with `#` are
ignored by the parser.

The expected format is:

```text
N
N grid rows with N comma-separated values each
N horizontal-constraint rows with N-1 comma-separated values each
N-1 vertical-constraint rows with N comma-separated values each
```

Grid values:

- `0` means an empty cell.
- `1..N` are given clue values.

Constraint values:

- `0` means no constraint.
- `1` means the left or upper cell is less than the right or lower cell.
- `-1` means the left or upper cell is greater than the right or lower cell.

Example `4x4` puzzle:

```text
4
1,0,0,0
0,0,0,0
0,0,0,0
0,0,0,0
1,0,0
0,0,0
0,0,0
0,0,0
0,0,0,0
0,0,0,0
0,0,0,0
```

In this example, the first row starts with a given `1`, and the first
horizontal constraint row says cell `(0,0) < (0,1)`.

## CLI Usage

The main CLI command is `futoshiki`:

```powershell
uv run futoshiki --help
```

Available subcommands:

```text
futoshiki solver      Solve a puzzle file or folder
futoshiki benchmark   Run benchmark tools
futoshiki ui          Launch the UI application
```

### Solve One Puzzle

```powershell
uv run futoshiki solver test\fixtures\input_4x4.txt
```

By default, the solver command uses `backward_chaining` and prints the solved
board to standard output.

Choose a solver explicitly:

```powershell
uv run futoshiki solver test\fixtures\input_4x4.txt --solver astar_h2
```

Valid solver keys:

```text
astar_h1
astar_h2
astar_h3
astar_h4
backtracking_forward_chaining
backward_chaining
brute_force
forward_chaining
forward_then_backward_chaining
```

### Solve a Folder

When the input path is a directory, the CLI solves every `.txt` file in that
directory and writes solution files instead of printing each board.

```powershell
uv run futoshiki solver src\benchmark\input --solver backward_chaining
```

By default, folder-mode output is written to:

```text
<input>\solutions
```

Use a custom output directory:

```powershell
uv run futoshiki solver src\benchmark\input --solver astar_h4 --output-dir resource\solutions
```

### Benchmark Commands

Benchmark commands are grouped under `futoshiki benchmark`.

Show benchmark help:

```powershell
uv run futoshiki benchmark --help
```

Run one solver against the benchmark corpus:

```powershell
uv run futoshiki benchmark run --solver backward_chaining
```

Run all benchmarked solvers:

```powershell
uv run futoshiki benchmark run --solver all
```

Limit benchmark cases to puzzles up to a maximum size:

```powershell
uv run futoshiki benchmark run --solver astar_h2 --max-n 6
```

Use a custom benchmark root containing `input\` and `expected\` folders:

```powershell
uv run futoshiki benchmark run --solver backward_chaining --benchmark-root src\benchmark
```

Benchmark CSV files are written to:

```text
resource\output
```

### Generate Benchmark Data

Regenerate the benchmark input and expected-solution corpus:

```powershell
uv run futoshiki benchmark generate --benchmark-root src\benchmark
```

This writes paired puzzle and expected-solution files under:

```text
src\benchmark\input
src\benchmark\expected
```

### Validate Benchmark Data

Validate a file or directory with Z3:

```powershell
uv run futoshiki benchmark validate src\benchmark\input --expected-dir src\benchmark\expected
```

Validation checks that each puzzle is satisfiable, has a unique solution, and
optionally matches the corresponding expected solution file.

### Visualize Benchmark Results

Create charts from benchmark CSV files:

```powershell
uv run futoshiki benchmark visualize --data-dir resource\output --output-dir resource\plots
```

Generate LaTeX tables as well:

```powershell
uv run futoshiki benchmark visualize --data-dir resource\output --output-dir resource\plots --latex-dir resource\latex
```

If `--output-dir` is omitted, the visualizer displays charts interactively.

### UI

Launch the UI:

```powershell
uv run futoshiki ui
```

The UI uses the Pygame application layer in `src\app`, `src\models`, and
`src\ui`.

## Alternate Entry Points

The package also exposes direct scripts:

```powershell
uv run futoshiki-solver test\fixtures\input_4x4.txt --solver backward_chaining
uv run futoshiki-ui
```

The top-level `main.py` delegates to the package entry point:

```powershell
uv run python main.py --help
```

## Development

Run the full test suite:

```powershell
uv run pytest
```

Run a focused test file:

```powershell
uv run pytest test\test_astar.py
uv run pytest test\test_benchmark_runner.py
```

Helpful documentation:

- `docs\architecture.md`
- `docs\futoshiki.md`
- `docs\forward_chaining.md`
- `docs\backward_chaining.md`
- `docs\astar_search.md`
- `docs\heuristic_testing.md`

## License

This project is distributed under the license included in `LICENSE`.
