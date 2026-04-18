# Futoshiki_VifeAgent

Futoshiki solver and benchmark suite with multiple solving strategies:
forward chaining, backward chaining, brute force, and A*.

## Concise project report

The codebase currently has two layers:

1. **Core implementation (`src\`)**  
   Contains puzzle parsing/modeling, constraints, inference engines, solvers,
   heuristics, search, and benchmarking utilities.
2. **Package entrypoints (`src\futoshiki_vifeagent\`)**  
   Thin CLI wrappers that expose scripts from `pyproject.toml`:
   `futoshiki`, `futoshiki-solver`, and `futoshiki-ui`.

### Main modules

| Module | Purpose |
| --- | --- |
| `src\core` | Puzzle model, parser, formatter |
| `src\constraints` | Row/column/inequality constraints, AC-3 |
| `src\fol`, `src\inference` | FOL predicates/KB + forward/backward chaining engines |
| `src\solver` | Solver implementations and shared solver interface |
| `src\heuristics`, `src\search` | A* state/search and heuristic functions |
| `src\benchmark` | Corpus generation, validation, benchmark execution |
| `test` | Unit and integration tests across parser, inference, solvers, and benchmark flow |

### Current test scope (high level)

- Parsing and puzzle model integration
- Knowledge base and inference logic (forward/backward chaining)
- Solver behavior across algorithm variants
- Benchmark runner and stats CSV writing

## Testing guide

For heuristic-focused experimentation and benchmark comparison workflows, see
`docs\heuristic_testing.md`.

### 1) Setup

```powershell
uv sync --group dev
```

### 2) Run the full test suite

```powershell
uv run pytest
```

### 3) Run focused test files

```powershell
uv run pytest test\test_forward_chaining.py
uv run pytest test\test_backward_chaining.py
uv run pytest test\test_benchmark_runner.py
```

### 4) Run solver benchmark from CLI

```powershell
uv run futoshiki-solver --solver backward_chaining
uv run futoshiki-solver --solver all
```

### 5) Validate or regenerate benchmark corpus

```powershell
uv run python -m benchmark.validator src\benchmark\input --expected-dir src\benchmark\expected
uv run python -m benchmark.generator --benchmark-root src\benchmark
```
