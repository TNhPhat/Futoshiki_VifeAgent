"""
Solver worker: runs a solver in a background thread and emits SolveStep
objects onto a queue for the main thread to consume.

Call start_solve(state) to launch the worker for the puzzle in state.board.
"""
from __future__ import annotations

import time
import threading

import numpy as np

from models.game_state import GameState, SolveStep
from app.solver_registry import make_solver

# Solvers that support live animation via the on_step callback.
_ANIMATED_SOLVERS = {
    "astar_h1", "astar_h2", "astar_h3", "astar_h4",
    "forward_chaining", "btfc", "brute_force", "forward_then_backward",
    "backward_chaining",
}


def start_solve(state: GameState) -> None:
    """
    Launch a background solver thread for the puzzle in state.board.

    Resets all solve-visualisation state first.  The worker thread pushes
    SolveStep objects onto state.solve_steps; the main loop drains them.
    Sets state.is_playing = True so animation begins immediately.
    """
    state.reset_solve_state()

    if state.board is None:
        return

    puzzle      = state.board.puzzle
    solver_name = state.solver_name
    stop_event  = state.stop_event
    step_queue  = state.solve_steps
    t0          = time.perf_counter()

    # Mutable stats shared between the closures.
    _stats: dict = {"nodes": 0, "backtracks": 0, "prev_grid": None}

    def _emit(grid: np.ndarray, is_bt: bool) -> None:
        """Push one SolveStep and throttle to state.speed steps/second."""
        _stats["nodes"] += 1
        step_queue.put(SolveStep(
            grid=grid.copy(),
            is_backtrack=is_bt,
            node_count=_stats["nodes"],
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            backtrack_count=_stats["backtracks"],
        ))
        delay = 1.0 / max(0.5, state.speed)
        if stop_event.wait(timeout=delay):
            raise StopIteration

    def on_step(grid_snapshot: np.ndarray, is_backtrack: bool = False) -> None:
        """
        Callback invoked by solvers after each node expansion.

        Detects backtracks automatically when the solver does not flag them
        explicitly.  On forward progress, decomposes bulk assignments into
        individual cell-fill steps so each cell appears one by one.
        """
        if stop_event.is_set():
            raise StopIteration

        prev = _stats["prev_grid"]
        _stats["prev_grid"] = grid_snapshot.copy()

        is_bt = is_backtrack or (
            prev is not None
            and int(np.count_nonzero(grid_snapshot)) < int(np.count_nonzero(prev))
        )

        if is_bt:
            _stats["backtracks"] += 1
            _emit(grid_snapshot, is_bt=True)
        else:
            # Diff against previous (or puzzle givens on the first step).
            base = puzzle.grid.copy() if prev is None else prev.copy()
            newly_filled = [
                (r, c)
                for r in range(puzzle.N)
                for c in range(puzzle.N)
                if grid_snapshot[r, c] != 0 and base[r, c] == 0
            ]
            if not newly_filled:
                # Nothing changed visually -- emit anyway so stats update.
                _emit(grid_snapshot, is_bt=False)
            else:
                # One step per newly filled cell.
                running = base.copy()
                for r, c in newly_filled:
                    running[r, c] = grid_snapshot[r, c]
                    _emit(running, is_bt=False)

    def worker() -> None:
        try:
            if solver_name in _ANIMATED_SOLVERS:
                # These solvers accept on_step natively (including all A* variants).
                solver = make_solver(solver_name)
                solver.solve(puzzle, on_step=on_step)

            else:
                # Fallback: run fully, push a single final step.
                solver = make_solver(solver_name)
                solution, _stats_obj = solver.solve(puzzle)
                if solution is not None and not stop_event.is_set():
                    step_queue.put(SolveStep(
                        grid=solution.grid.copy(),
                        is_backtrack=False,
                        node_count=getattr(_stats_obj, "node_expansions", 1),
                        elapsed_ms=(time.perf_counter() - t0) * 1000,
                        backtrack_count=getattr(_stats_obj, "backtracks", 0),
                    ))

        except StopIteration:
            pass
        except Exception as exc:
            print(f"[solver worker] {type(exc).__name__}: {exc}")

    state.solve_thread = threading.Thread(target=worker, daemon=True)
    state.solve_thread.start()
    state.is_playing = True
