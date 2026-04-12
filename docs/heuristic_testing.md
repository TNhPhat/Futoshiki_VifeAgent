# Heuristic Testing Guide

This guide is for validating and comparing heuristic approaches used by the A* solver.

## 1. Environment setup

```powershell
uv sync --group dev
```

## 2. Fast correctness checks for heuristic code

Run the focused tests first while iterating on heuristic logic:

```powershell
uv run pytest test\test_heuristics.py -q
uv run pytest test\test_astar.py -q
uv run pytest test\test_ac3_heuristic.py -q
```

Useful targeted runs:

```powershell
uv run pytest test\test_heuristics.py -k "h1 or h2 or h3" -q
uv run pytest test\test_ac3_heuristic.py -k "AC3Heuristic or H4" -q
uv run pytest test\test_astar.py -k "AStarSolver2x2 or AStarSolver3x3" -q
```

## 3. Run benchmark comparisons by heuristic

Use `futoshiki-solver` with benchmark solver keys:

- `astar_h1` = Empty Cell heuristic
- `astar_h2` = Domain Size heuristic
- `astar_h3` = Min Conflicts heuristic
- `astar_h4` = AC-3 heuristic

`astar_h4` is available in the benchmark registry even if current CLI help text
only lists `astar_h1`–`astar_h3`.

Run each variant against the same corpus:

```powershell
uv run futoshiki-solver --solver astar_h1 --benchmark-root src\benchmark
uv run futoshiki-solver --solver astar_h2 --benchmark-root src\benchmark
uv run futoshiki-solver --solver astar_h3 --benchmark-root src\benchmark
uv run futoshiki-solver --solver astar_h4 --benchmark-root src\benchmark
```

You can also run all registered solver variants in one pass:

```powershell
uv run futoshiki-solver --solver all --benchmark-root src\benchmark
```

## 4. Compare performance metrics

Benchmark runs write CSV files under `resource\output\`.
Compare average runtime and node expansions across the most recent runs:

```powershell
$csvs = Get-ChildItem .\resource\output\*.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 8
$summary = foreach ($f in $csvs) {
  $rows = Import-Csv $f
  [pscustomobject]@{
    file                = $f.Name
    avg_time_ms         = [math]::Round((($rows | Measure-Object -Property time_ms -Average).Average), 2)
    avg_node_expansions = [math]::Round((($rows | Measure-Object -Property node_expansions -Average).Average), 2)
    avg_memory_kb       = [math]::Round((($rows | Measure-Object -Property memory_kb -Average).Average), 2)
    failed_cases        = ($rows | Where-Object { $_.ok -ne "True" }).Count
  }
}
$summary | Sort-Object avg_node_expansions, avg_time_ms | Format-Table -AutoSize
```

Recommended interpretation order:

1. `failed_cases` (correctness gate; should be zero)
2. `avg_node_expansions` (search efficiency)
3. `avg_time_ms` and `avg_memory_kb` (runtime trade-offs)

## 5. Workflow for adding a new heuristic

When introducing a new heuristic approach:

1. Implement/update heuristic class in `src\heuristics\`.
2. Expose it through `src\heuristics\__init__.py` if needed.
3. Add a benchmark solver key in `src\benchmark\benchmark.py` (`_solver_registry`).
4. Add unit tests in `test\test_heuristics.py` (or a dedicated test file).
5. Add A* integration tests in `test\test_astar.py` or heuristic-specific solver tests.
6. Re-run focused tests, then full suite:

```powershell
uv run pytest
```

## 6. Common pitfalls

- Comparing heuristics on different benchmark roots or different puzzle sets.
- Evaluating speed without checking `ok` / failed cases first.
- Editing heuristic logic without re-running `test\test_ac3_heuristic.py` when AC-3 behavior is involved.
