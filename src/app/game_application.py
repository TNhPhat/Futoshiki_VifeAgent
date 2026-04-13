"""
GameApplication: main pygame event loop and application controller.

Owns the GameState, handles all events, manages the solver worker thread,
and drives the CompositeRenderer each frame.
"""
from __future__ import annotations

import queue
import time
import threading
from typing import Any

import numpy as np
import pygame

from heuristics.domain_size_heuristic import DomainSizeHeuristic
from heuristics.empty_cell_heuristic import EmptyCellHeuristic
from heuristics.min_conflicts_heuristic import MinConflictsHeuristic
from models.board import Board
from models.game_state import AppMode, GameState, SolveStep
from models.puzzle_repository import InMemoryPuzzleRepository, PuzzleEntry
from search.astar import AStarEngine
from solver import (
    AC3BackwardChaining,
    AStarSolver,
    BackwardChaining,
    BacktrackingForwardChaining,
    BruteForceSolver,
    ForwardChaining,
    ForwardThenAC3BackwardChaining,
)
from ui.composite_renderer import CompositeRenderer
from ui.layout import SCREEN_H, SCREEN_W, cell_rect, grid_geometry
import ui.theme as T


# ---------------------------------------------------------------------------
# Solver registry
# ---------------------------------------------------------------------------

def _make_solver(name: str):
    """Return a BaseSolver instance for the given name key."""
    if name == "astar_h1":
        return AStarSolver(EmptyCellHeuristic())
    if name == "astar_h2":
        return AStarSolver(DomainSizeHeuristic())
    if name == "astar_h3":
        return AStarSolver(MinConflictsHeuristic())
    if name == "forward_chaining":
        return ForwardChaining()
    if name == "backward_chaining":
        return BackwardChaining()
    if name == "ac3_backward_chaining":
        return AC3BackwardChaining()
    if name == "forward_then_ac3":
        return ForwardThenAC3BackwardChaining()
    if name == "btfc":
        return BacktrackingForwardChaining()
    if name == "brute_force":
        return BruteForceSolver()
    return AStarSolver(DomainSizeHeuristic())


_SOLVER_CYCLE = [
    "astar_h2",
    "astar_h1",
    "astar_h3",
    "forward_chaining",
    "btfc",
    "forward_then_ac3",
    "backward_chaining",
    "ac3_backward_chaining",
    "brute_force",
]


# ---------------------------------------------------------------------------
# GameApplication
# ---------------------------------------------------------------------------

class GameApplication:
    """Main application.  Instantiate and call .run()."""

    def __init__(self, repo: InMemoryPuzzleRepository) -> None:
        pygame.init()
        pygame.display.set_caption("Futoshiki")
        self._screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self._clock  = pygame.time.Clock()

        T.init_fonts()

        self._repo = repo
        self._state = GameState()

        # Pre-load puzzle list entries so the HUD can display them
        self._state._puzzle_entries = repo.list_entries()
        self._state._puzzle_name    = ""

        self._renderer = CompositeRenderer()

        # Load the first benchmark puzzle automatically if available
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
                self._handle_event(event)

            self._update(dt)
            self._renderer.render(self._screen, self._state)
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def _handle_event(self, event: pygame.event.Event) -> None:
        state = self._state

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_click(event.pos)
            elif event.button == 4:   # scroll up
                state.puzzle_list_scroll = max(0, state.puzzle_list_scroll - 1)
            elif event.button == 5:   # scroll down
                state.puzzle_list_scroll += 1

        elif event.type == pygame.KEYDOWN:
            self._handle_keydown(event)

        elif event.type == pygame.MOUSEMOTION:
            # Speed slider drag
            if pygame.mouse.get_pressed()[0]:
                rects = getattr(state, "_hud_rects", {})
                slider = rects.get("speed_slider")
                if slider and slider.collidepoint(event.pos):
                    t = (event.pos[0] - slider.x) / max(1, slider.width)
                    state.speed = round(max(1.0, min(20.0, 1.0 + t * 19.0)), 1)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        state  = self._state
        rects: dict[str, Any] = getattr(state, "_hud_rects", {})

        # --- Overlays take priority ---
        if state.show_puzzle_list:
            self._handle_puzzle_list_click(pos, rects)
            return
        if state.show_generate_dialog:
            return  # wait for generation to finish

        # --- Mode tabs ---
        if rects.get("tab_play", pygame.Rect(0,0,0,0)).collidepoint(pos):
            self._switch_mode(AppMode.PLAY)
            return
        if rects.get("tab_solve", pygame.Rect(0,0,0,0)).collidepoint(pos):
            self._switch_mode(AppMode.SOLVE)
            return
        if rects.get("tab_menu", pygame.Rect(0,0,0,0)).collidepoint(pos):
            self._switch_mode(AppMode.MENU)
            return

        # --- Solver panel buttons ---
        if rects.get("solver_select", pygame.Rect(0,0,0,0)).collidepoint(pos):
            self._cycle_solver()
            return
        if state.mode == AppMode.SOLVE:
            if rects.get("solve_play",    pygame.Rect(0,0,0,0)).collidepoint(pos):
                state.is_playing = True;  return
            if rects.get("solve_pause",   pygame.Rect(0,0,0,0)).collidepoint(pos):
                state.is_playing = False; return
            if rects.get("solve_step",    pygame.Rect(0,0,0,0)).collidepoint(pos):
                self._advance_step(1);    return
            if rects.get("solve_restart", pygame.Rect(0,0,0,0)).collidepoint(pos):
                self._restart_solve();    return

        # Speed slider
        slider = rects.get("speed_slider")
        if slider and slider.collidepoint(pos) and state.mode == AppMode.SOLVE:
            t = (pos[0] - slider.x) / max(1, slider.width)
            state.speed = round(max(1.0, min(20.0, 1.0 + t * 19.0)), 1)
            return

        # --- Puzzle panel ---
        if rects.get("load_puzzle", pygame.Rect(0,0,0,0)).collidepoint(pos):
            state.show_puzzle_list = not state.show_puzzle_list
            return
        if rects.get("generate", pygame.Rect(0,0,0,0)).collidepoint(pos):
            self._start_generate(state.generate_size)
            return
        for sz in range(4, 10):
            if rects.get(f"gen_size_{sz}", pygame.Rect(0,0,0,0)).collidepoint(pos):
                state.generate_size = sz
                return

        # --- Play panel ---
        if rects.get("hint", pygame.Rect(0,0,0,0)).collidepoint(pos):
            if state.mode == AppMode.PLAY and state.board:
                self._apply_hint()
            return
        if rects.get("undo", pygame.Rect(0,0,0,0)).collidepoint(pos):
            if state.mode == AppMode.PLAY and state.board:
                state.board.undo()
            return
        if rects.get("notes_toggle", pygame.Rect(0,0,0,0)).collidepoint(pos):
            if state.mode == AppMode.PLAY:
                state.notes_mode = not state.notes_mode
            return

        # --- Grid cell click ---
        if state.mode == AppMode.PLAY and state.board:
            self._handle_grid_click(pos)

    def _handle_puzzle_list_click(self, pos, rects):
        state = self._state
        if rects.get("puzzle_list_close", pygame.Rect(0,0,0,0)).collidepoint(pos):
            state.show_puzzle_list = False
            return
        for row_rect, entry in rects.get("_puzzle_rows", []):
            if row_rect.collidepoint(pos):
                state.show_puzzle_list = False
                self._load_puzzle(entry)
                self._switch_mode(AppMode.PLAY)
                return

    def _handle_grid_click(self, pos: tuple[int, int]) -> None:
        board = self._state.board
        if board is None:
            return
        N = board.puzzle.N
        grid_rect, cell_size, gap = grid_geometry(N)
        for i in range(N):
            for j in range(N):
                r = cell_rect(i, j, grid_rect, cell_size, gap)
                if r.collidepoint(pos):
                    board.selected = (i, j)
                    return
        board.selected = None  # click outside grid deselects

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        state = self._state

        # Global shortcuts
        if event.key == pygame.K_F1:
            self._switch_mode(AppMode.PLAY)
            return
        if event.key == pygame.K_F2:
            self._switch_mode(AppMode.SOLVE)
            return

        if state.mode == AppMode.PLAY and state.board:
            self._handle_play_key(event)
        elif state.mode == AppMode.SOLVE:
            self._handle_solve_key(event)

    def _handle_play_key(self, event: pygame.event.Event) -> None:
        board = self._state.board
        if board is None or board.selected is None:
            return
        i, j = board.selected

        # Undo
        if event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL):
            board.undo()
            return

        # Notes toggle
        if event.key == pygame.K_n:
            self._state.notes_mode = not self._state.notes_mode
            return

        # Clear cell
        if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE, pygame.K_0):
            board.clear_value(i, j)
            return

        # Number entry (1..9)
        digit = _key_to_digit(event.key)
        if digit is not None and 1 <= digit <= board.puzzle.N:
            if self._state.notes_mode:
                board.toggle_note(i, j, digit)
            else:
                board.set_value(i, j, digit)
            if board.is_complete():
                self._state.set_notification("Puzzle solved!", 3.0)
            return

        # Arrow key navigation
        di, dj = _arrow_delta(event.key)
        if di != 0 or dj != 0:
            ni = max(0, min(board.puzzle.N - 1, i + di))
            nj = max(0, min(board.puzzle.N - 1, j + dj))
            board.selected = (ni, nj)

    def _handle_solve_key(self, event: pygame.event.Event) -> None:
        state = self._state
        if event.key == pygame.K_SPACE:
            state.is_playing = not state.is_playing
        elif event.key == pygame.K_RIGHT:
            self._advance_step(1)
        elif event.key == pygame.K_r:
            self._restart_solve()

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def _update(self, dt: float) -> None:
        state = self._state

        # Notification timer
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

        # Auto-advance solve steps.
        # The worker throttles itself via stop_event.wait(), so there is
        # usually at most one step ready per frame.  Drain everything that's
        # available immediately — no accumulator needed.
        if state.mode == AppMode.SOLVE and state.is_playing:
            self._drain_available_steps()

    # ------------------------------------------------------------------
    # Solve step management
    # ------------------------------------------------------------------

    def _drain_available_steps(self) -> None:
        """Drain every step currently in the queue and apply them.
        Called each frame while is_playing.  Marks the solve finished when
        the queue empties and the worker thread has exited."""
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

        # If nothing was in the queue and the thread is gone, we're done.
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

        # Determine new solver cells (non-given, non-zero cells)
        given_set = {(r, c) for r, c, _ in board.puzzle.get_given_cells()}
        state.solver_cells = {
            (r, c)
            for r in range(N)
            for c in range(N)
            if step.grid[r, c] != 0 and (r, c) not in given_set
        }

        # Flash backtrack cells (cells that were filled but are now 0)
        if step.is_backtrack and prev_grid is not None:
            for r in range(N):
                for c in range(N):
                    if prev_grid[r, c] != 0 and step.grid[r, c] == 0:
                        state.backtrack_timers[(r, c)] = 0.5

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _switch_mode(self, new_mode: AppMode) -> None:
        state = self._state
        old_mode = state.mode

        if new_mode == AppMode.SOLVE and old_mode != AppMode.SOLVE:
            if state.board is None:
                state.set_notification("Load a puzzle first.", 2.0)
                return
            self._start_solve()

        elif new_mode != AppMode.SOLVE and old_mode == AppMode.SOLVE:
            # Stop any running solve
            state.stop_event.set()

        state.mode = new_mode

    # ------------------------------------------------------------------
    # Solver worker
    # ------------------------------------------------------------------

    def _start_solve(self) -> None:
        state = self._state
        state.reset_solve_state()

        if state.board is None:
            return

        # Snapshot the puzzle at solve start
        puzzle = state.board.puzzle

        solver_name = state.solver_name
        stop_event  = state.stop_event
        step_queue  = state.solve_steps
        t0 = time.perf_counter()

        # Running stats (shared between closure and engine ref)
        _stats: dict = {"nodes": 0, "backtracks": 0, "prev_grid": None}

        def _emit(grid: np.ndarray, is_bt: bool) -> None:
            """Put one SolveStep on the queue, then wait 1/speed seconds.
            Raises StopIteration if stop_event fires during the wait."""
            _stats["nodes"] += 1
            step_queue.put(SolveStep(
                grid=grid.copy(),
                is_backtrack=is_bt,
                node_count=_stats["nodes"],
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                backtrack_count=_stats["backtracks"],
            ))
            # Throttle: wait 1/speed seconds before the next step.
            # wait() returns True if stop_event is set during the wait.
            delay = 1.0 / max(0.5, state.speed)
            if stop_event.wait(timeout=delay):
                raise StopIteration

        def on_step(grid_snapshot: np.ndarray, is_backtrack: bool = False) -> None:
            if stop_event.is_set():
                raise StopIteration

            prev = _stats["prev_grid"]
            _stats["prev_grid"] = grid_snapshot.copy()

            # Trust the explicit flag if the solver provides it; otherwise infer.
            is_bt = is_backtrack or (
                prev is not None
                and int(np.count_nonzero(grid_snapshot))
                   < int(np.count_nonzero(prev))
            )
            if is_bt:
                _stats["backtracks"] += 1
                # Backtrack: emit the new (partially-cleared) grid as one step
                _emit(grid_snapshot, is_bt=True)
            else:
                # Forward progress: decompose into individual cell assignments
                # so the user sees each cell being filled one by one.
                if prev is None:
                    # First node: diff against the original puzzle givens
                    base = puzzle.grid.copy()
                else:
                    base = prev.copy()

                # Collect cells that are newly assigned in this node
                newly_filled = [
                    (r, c)
                    for r in range(puzzle.N)
                    for c in range(puzzle.N)
                    if grid_snapshot[r, c] != 0 and base[r, c] == 0
                ]

                if not newly_filled:
                    # Nothing changed visually — still emit so stats update
                    _emit(grid_snapshot, is_bt=False)
                else:
                    # Emit each cell being filled as a separate step
                    running = base.copy()
                    for r, c in newly_filled:
                        running[r, c] = grid_snapshot[r, c]
                        _emit(running, is_bt=False)

        # Solvers whose solve() accepts an on_step callback directly.
        _ANIMATED_SOLVERS = {
            "forward_chaining", "btfc", "brute_force", "forward_then_ac3",
        }

        def worker() -> None:
            try:
                if solver_name.startswith("astar"):
                    # Use AStarEngine directly so we can pass on_step.
                    heuristic_map = {
                        "astar_h1": EmptyCellHeuristic(),
                        "astar_h2": DomainSizeHeuristic(),
                        "astar_h3": MinConflictsHeuristic(),
                    }
                    heuristic = heuristic_map.get(solver_name, DomainSizeHeuristic())
                    engine = AStarEngine(heuristic=heuristic)
                    engine.solve(puzzle, on_step=on_step)

                elif solver_name in _ANIMATED_SOLVERS:
                    # These solvers accept on_step natively.
                    solver = _make_solver(solver_name)
                    solver.solve(puzzle, on_step=on_step)

                elif solver_name in ("backward_chaining", "ac3_backward_chaining"):
                    # BC solvers operate at the logical level; no intermediate
                    # grid state during proof.  Run fully, then replay the
                    # solution cell-by-cell so the user sees something.
                    solver = _make_solver(solver_name)
                    solution, _stats_obj = solver.solve(puzzle)
                    if solution is not None and not stop_event.is_set():
                        base = puzzle.grid.copy()
                        for r in range(puzzle.N):
                            for c in range(puzzle.N):
                                if solution.grid[r, c] != 0 and base[r, c] == 0:
                                    base[r, c] = solution.grid[r, c]
                                    on_step(base.copy())

                else:
                    # Fallback: run fully, push single final step.
                    solver = _make_solver(solver_name)
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

    def _restart_solve(self) -> None:
        state = self._state
        if state.board is None:
            return
        state.mode = AppMode.SOLVE
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

    def _start_generate(self, n: int) -> None:
        state = self._state
        state.show_generate_dialog = True
        state.reset_solve_state()

        def worker():
            try:
                puzzle = self._repo.generate(n)
                board  = Board(puzzle=puzzle)
                state.board = board
                state._puzzle_name = f"Random {n}x{n}"
                state.notes_mode = False
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
    # Solver cycling
    # ------------------------------------------------------------------

    def _cycle_solver(self) -> None:
        state = self._state
        try:
            idx = _SOLVER_CYCLE.index(state.solver_name)
        except ValueError:
            idx = -1
        state.solver_name = _SOLVER_CYCLE[(idx + 1) % len(_SOLVER_CYCLE)]

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _shutdown(self) -> None:
        self._state.stop_event.set()
        pygame.quit()


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def _key_to_digit(key: int) -> int | None:
    """Return 1-9 for digit keys (both row and numpad), else None."""
    if pygame.K_1 <= key <= pygame.K_9:
        return key - pygame.K_0
    if pygame.K_KP1 <= key <= pygame.K_KP9:
        return key - pygame.K_KP0
    return None


def _arrow_delta(key: int) -> tuple[int, int]:
    """Return (di, dj) for arrow keys."""
    return {
        pygame.K_UP:    (-1, 0),
        pygame.K_DOWN:  ( 1, 0),
        pygame.K_LEFT:  ( 0,-1),
        pygame.K_RIGHT: ( 0, 1),
    }.get(key, (0, 0))
