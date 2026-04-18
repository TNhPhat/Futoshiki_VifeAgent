"""
Solver registry: maps solver name keys to BaseSolver instances.
"""
from __future__ import annotations

from heuristics.ac3_heuristic import AC3Heuristic
from heuristics.domain_size_heuristic import DomainSizeHeuristic
from heuristics.empty_cell_heuristic import EmptyCellHeuristic
from heuristics.min_conflicts_heuristic import MinConflictsHeuristic
from solver import (
    AStarSolver,
    BackwardChaining,
    BacktrackingForwardChaining,
    BruteForceSolver,
    ForwardChaining,
    ForwardThenBackwardChaining,
)


def make_solver(name: str):
    """Return a BaseSolver instance for the given name key."""
    if name == "astar_h1":
        return AStarSolver(EmptyCellHeuristic())
    if name == "astar_h2":
        return AStarSolver(DomainSizeHeuristic())
    if name == "astar_h3":
        return AStarSolver(MinConflictsHeuristic())
    if name == "astar_h4":
        return AStarSolver(AC3Heuristic())
    if name == "forward_chaining":
        return ForwardChaining()
    if name == "backward_chaining":
        return BackwardChaining()
    if name == "forward_then_backward":
        return ForwardThenBackwardChaining()
    if name == "btfc":
        return BacktrackingForwardChaining()
    if name == "brute_force":
        return BruteForceSolver()
    return AStarSolver(DomainSizeHeuristic())


SOLVER_CYCLE = [
    "astar_h2",
    "astar_h1",
    "astar_h3",
    "astar_h4",
    "forward_chaining",
    "btfc",
    "forward_then_backward",
    "backward_chaining",
    "brute_force",
]
