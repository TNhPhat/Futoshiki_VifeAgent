"""
GameState: top-level application state machine.

Holds the current mode, board, solver selection, solve-thread bookkeeping,
and per-frame visualization state (backtrack timers, solver cells, stats).
"""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from models.board import Board


# ---------------------------------------------------------------------------
# Mode enum
# ---------------------------------------------------------------------------

class AppMode(Enum):
    MENU  = auto()   # puzzle / solver selection (no active game)
    PLAY  = auto()   # manual user interaction
    SOLVE = auto()   # step-by-step solver visualization


# ---------------------------------------------------------------------------
# Solve step (produced by the worker thread)
# ---------------------------------------------------------------------------

@dataclass
class SolveStep:
    """A single snapshot emitted by the solver worker thread."""
    grid: np.ndarray          # full N×N grid at this step
    is_backtrack: bool        # True if fewer filled cells than previous step
    node_count: int           # A* node expansions so far
    elapsed_ms: float         # wall-clock ms since solve started
    backtrack_count: int = 0  # cumulative backtracks so far


# ---------------------------------------------------------------------------
# Main game state
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """
    Centralised application state.

    All mutable fields are public so renderers and the game loop
    can read / write them directly.
    """

    mode: AppMode = AppMode.MENU

    # Active board (set when a puzzle is loaded / generated).
    board: "Board | None" = None

    # ------------------------------------------------------------------
    # UI interaction state
    # ------------------------------------------------------------------

    # True when the user is entering pencil-mark notes instead of values.
    notes_mode: bool = False

    # Name of the solver to use for visualization.
    # Matches the keys returned by _make_solver() in GameApplication.
    solver_name: str = "astar_h2"

    # ------------------------------------------------------------------
    # Solve visualization state
    # ------------------------------------------------------------------

    # Steps produced by the worker thread.
    solve_steps: queue.Queue = field(default_factory=queue.Queue)

    # Background solver thread (None when idle).
    solve_thread: threading.Thread | None = None

    # Signal for the worker thread to stop early.
    stop_event: threading.Event = field(default_factory=threading.Event)

    # Auto-advance when True; paused when False.
    is_playing: bool = False

    # Steps per second (1.0 – 20.0).
    speed: float = 1.0

    # Fractional step accumulator for sub-frame speed control.
    step_accumulator: float = 0.0

    # The grid currently displayed in SOLVE mode.
    current_display_grid: np.ndarray | None = None

    # Cells filled by the solver (blue tint) — set of (row, col).
    solver_cells: set[tuple[int, int]] = field(default_factory=set)

    # Backtrack flash timers: cell → remaining seconds.
    backtrack_timers: dict[tuple[int, int], float] = field(default_factory=dict)

    # Solve stats for the HUD.
    node_count: int = 0
    elapsed_ms: float = 0.0
    backtrack_count: int = 0

    # True once the solver has finished (thread exited).
    solve_finished: bool = False

    # Whether the puzzle was solved successfully.
    solve_succeeded: bool = False

    # ------------------------------------------------------------------
    # Puzzle list overlay (shown when [Load Puzzle] is clicked)
    # ------------------------------------------------------------------

    show_puzzle_list: bool = False
    puzzle_list_scroll: int = 0  # scroll offset in entries

    # ------------------------------------------------------------------
    # Generate-puzzle overlay
    # ------------------------------------------------------------------

    show_generate_dialog: bool = False
    generate_size: int = 5  # selected size for generation

    # ------------------------------------------------------------------
    # Notification message (displayed briefly in the grid area)
    # ------------------------------------------------------------------

    notification: str = ""
    notification_timer: float = 0.0  # seconds remaining

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def set_notification(self, msg: str, duration: float = 2.0) -> None:
        self.notification = msg
        self.notification_timer = duration

    def is_solving(self) -> bool:
        """Return True if the solver thread is currently running."""
        return (
            self.solve_thread is not None
            and self.solve_thread.is_alive()
        )

    def reset_solve_state(self) -> None:
        """Clear all solve-visualization state (call before starting a new solve)."""
        # Signal any running thread to stop.
        self.stop_event.set()
        if self.solve_thread is not None:
            self.solve_thread.join(timeout=2.0)

        # Drain the queue.
        while not self.solve_steps.empty():
            try:
                self.solve_steps.get_nowait()
            except queue.Empty:
                break

        self.solve_thread = None
        self.stop_event = threading.Event()
        self.is_playing = False
        self.step_accumulator = 0.0
        self.current_display_grid = None
        self.solver_cells = set()
        self.backtrack_timers = {}
        self.node_count = 0
        self.elapsed_ms = 0.0
        self.backtrack_count = 0
        self.solve_finished = False
        self.solve_succeeded = False
