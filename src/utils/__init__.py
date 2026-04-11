from __future__ import annotations

from dataclasses import dataclass

from .stats_csv import StatsCsvWriter


@dataclass
class Stats:
    """
    Performance statistics returned by every solver.

    Attributes
    ----------
    time_ms : float
        Wall-clock solving time in milliseconds (``time.perf_counter``).
    memory_kb : float
        Peak memory usage in kilobytes (``tracemalloc``).
    inference_count : int
        Number of rule firings (Forward/Backward Chaining); 0 for other solvers.
    node_expansions : int
        Nodes/assignments expanded (A*, Brute Force); 0 for chain-based solvers.
    backtracks : int
        Number of backtracks (Backtracking solver); 0 for other solvers.
    completion_ratio : float
        Ratio of cells solved by the algorithm:
        (# initially-empty cells solved) / (# initially-empty cells).
    """

    time_ms: float
    memory_kb: float
    inference_count: int
    node_expansions: int
    backtracks: int
    completion_ratio: float = 0.0


__all__ = ["Stats", "StatsCsvWriter"]
