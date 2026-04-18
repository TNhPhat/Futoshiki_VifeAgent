"""
GameApplication: main pygame event loop and application controller.

Owns the GameState and coordinates the three main subsystems:
  - InputHandler  -- translates pygame events into state changes
  - solve_worker  -- runs solvers in a background thread
  - CompositeRenderer -- draws everything each frame
"""
from __future__ import annotations

import queue
import threading

import numpy as np
import pygame

from fol.cnf_generator import CNFGenerator
from models.board import Board
from models.game_state import AppMode, GameState, SolveStep
from models.puzzle_repository import InMemoryPuzzleRepository, PuzzleEntry
from ui.composite_renderer import CompositeRenderer
from ui.layout import SCREEN_H, SCREEN_W
import ui.theme as T
from app.input_handler import InputHandler
from app.solve_worker import start_solve


class GameApplication:
    """Main application.  Instantiate and call .run()."""

    def __init__(self, repo: InMemoryPuzzleRepository) -> None:
        pygame.init()
        pygame.display.set_caption("Futoshiki")
        self._screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self._clock  = pygame.time.Clock()

        T.init_fonts()

        self._repo     = repo
        self._state    = GameState()
        self._input    = InputHandler(self)
        self._renderer = CompositeRenderer()

        # Pre-load puzzle list so the HUD can display it immediately.
        self._state._puzzle_entries = repo.list_entries()
        self._state._puzzle_name    = ""

        # Auto-load the first benchmark puzzle if one exists.
        entries = self._state._puzzle_entries
        if entries:
            self._load_puzzle(entries[0])
            self._state.mode = AppMode.PLAY

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        while True:
            dt = self._clock.tick(60) / 1000.0  # seconds

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._shutdown()
                    return
                self._input.handle_event(event)

            self._update(dt)
            self._renderer.render(self._screen, self._state)
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def _update(self, dt: float) -> None:
        state = self._state

        # Notification countdown
        if state.notification_timer > 0:
            state.notification_timer = max(0.0, state.notification_timer - dt)
            if state.notification_timer == 0:
                state.notification = ""

        # Backtrack flash timers
        expired = [c for c, t in state.backtrack_timers.items() if t <= 0]
        for c in expired:
            del state.backtrack_timers[c]
        for c in list(state.backtrack_timers):
            state.backtrack_timers[c] = max(0.0, state.backtrack_timers[c] - dt)

        # Shake timers (invalid note attempt feedback)
        expired = [c for c, t in state.shake_timers.items() if t <= 0]
        for c in expired:
            del state.shake_timers[c]
        for c in list(state.shake_timers):
            state.shake_timers[c] = max(0.0, state.shake_timers[c] - dt)

        # Drain solver steps while auto-playing.
        if state.mode == AppMode.SOLVE and state.is_playing:
            self._drain_available_steps()

    # ------------------------------------------------------------------
    # Solve step management
    # ------------------------------------------------------------------

    def _drain_available_steps(self) -> None:
        """
        Consume every SolveStep currently waiting in the queue.
        Called each frame while is_playing.  Marks the solve finished when
        the queue is empty and the worker thread has exited.
        """
        state = self._state
        prev_grid = state.current_display_grid
        drained = False

        while True:
            try:
                step: SolveStep = state.solve_steps.get_nowait()
            except queue.Empty:
                break
            self._apply_step(step, prev_grid)
            prev_grid = state.current_display_grid
            drained = True

        if not drained and not state.is_solving() and not state.solve_finished:
            self._mark_finished()

    def _advance_step(self, count: int) -> None:
        """Manually advance by `count` steps (Step button / arrow key)."""
        state = self._state
        prev_grid = state.current_display_grid

        for _ in range(count):
            try:
                step: SolveStep = state.solve_steps.get_nowait()
            except queue.Empty:
                if not state.is_solving() and not state.solve_finished:
                    self._mark_finished()
                break
            self._apply_step(step, prev_grid)
            prev_grid = state.current_display_grid

    def _mark_finished(self) -> None:
        state = self._state
        state.solve_finished = True
        state.is_playing = False
        state.solve_succeeded = (
            state.current_display_grid is not None
            and state.board is not None
            and int(np.count_nonzero(state.current_display_grid))
               == state.board.puzzle.N ** 2
        )
        if state.solve_succeeded:
            state.set_notification("Puzzle solved!", 3.0)
        else:
            state.set_notification("No solution found.", 3.0)

    def _apply_step(self, step: SolveStep, prev_grid) -> None:
        state = self._state
        board = state.board

        state.current_display_grid = step.grid.copy()
        state.node_count      = step.node_count
        state.elapsed_ms      = step.elapsed_ms
        state.backtrack_count = step.backtrack_count

        if board is None:
            return

        N = board.puzzle.N
        given_set = {(r, c) for r, c, _ in board.puzzle.get_given_cells()}
        state.solver_cells = {
            (r, c)
            for r in range(N)
            for c in range(N)
            if step.grid[r, c] != 0 and (r, c) not in given_set
        }

        # Flash cells that were filled but have just been cleared (backtrack).
        if step.is_backtrack and prev_grid is not None:
            for r in range(N):
                for c in range(N):
                    if prev_grid[r, c] != 0 and step.grid[r, c] == 0:
                        state.backtrack_timers[(r, c)] = 0.5

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _switch_mode(self, new_mode: AppMode) -> None:
        state    = self._state
        old_mode = state.mode

        if new_mode == AppMode.SOLVE and old_mode != AppMode.SOLVE:
            if state.board is None:
                state.set_notification("Load a puzzle first.", 2.0)
                return
            self._start_solve()
        elif new_mode != AppMode.SOLVE and old_mode == AppMode.SOLVE:
            state.stop_event.set()

        if new_mode != AppMode.KB:
            state.kb_hovered_lit    = None
            state.kb_selected_lit   = None
            state.kb_hovered_cell   = None
            state.kb_hovered_clause = None

        state.mode = new_mode

    # ------------------------------------------------------------------
    # Solver
    # ------------------------------------------------------------------

    def _start_solve(self) -> None:
        start_solve(self._state)

    def _restart_solve(self) -> None:
        if self._state.board is None:
            return
        self._state.mode = AppMode.SOLVE
        self._start_solve()

    # ------------------------------------------------------------------
    # Puzzle loading / generation
    # ------------------------------------------------------------------

    def _load_puzzle(self, entry: PuzzleEntry) -> None:
        state = self._state
        state.reset_solve_state()
        puzzle = self._repo.load(entry.path)
        state.board = Board(puzzle=puzzle)
        state._puzzle_name = entry.name.replace("_", " ")
        state.notes_mode = False
        state.cnf_kb = CNFGenerator.generate(puzzle)
        state.cnf_kb_scroll = 0

    def _start_generate(self, n: int, difficulty: str = "medium") -> None:
        state = self._state
        state.show_generate_dialog = True
        state.reset_solve_state()

        def worker():
            try:
                puzzle = self._repo.generate(n, difficulty=difficulty)
                state.board = Board(puzzle=puzzle)
                state._puzzle_name = f"Random {n}x{n}"
                state.notes_mode = False
                state.cnf_kb = CNFGenerator.generate(puzzle)
                state.cnf_kb_scroll = 0
            except Exception as exc:
                print(f"[generate worker] {exc}")
            finally:
                state.show_generate_dialog = False
                state.mode = AppMode.PLAY

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Hint
    # ------------------------------------------------------------------

    def _apply_hint(self) -> None:
        state = self._state
        board = state.board
        if board is None:
            return
        result = board.get_hint()
        if result is None:
            state.set_notification("No forced cell found.", 2.0)
            return
        r, c, v = result
        board.set_value(r, c, v)
        board.selected = (r, c)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _shutdown(self) -> None:
        self._state.stop_event.set()
        pygame.quit()
