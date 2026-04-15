"""
InputHandler: translates pygame events into GameApplication actions.

Keeps all event-dispatch and hit-test logic out of GameApplication so the
main application file stays focused on the frame loop and state transitions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from models.game_state import AppMode

if TYPE_CHECKING:
    from app.game_application import GameApplication


class InputHandler:
    """Handles all pygame input events on behalf of GameApplication."""

    def __init__(self, app: "GameApplication") -> None:
        self._app = app

    # ------------------------------------------------------------------
    # Top-level dispatch
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        state = self._app._state

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.handle_click(event.pos)
            elif event.button == 4:   # scroll up
                if state.mode == AppMode.KB and state.kb_show_popup:
                    state._kb_popup_scroll = max(0, getattr(state, "_kb_popup_scroll", 0) - 20)
                elif state.mode == AppMode.KB:
                    state.cnf_kb_scroll = max(0, state.cnf_kb_scroll - 1)
                else:
                    state.puzzle_list_scroll = max(0, state.puzzle_list_scroll - 1)
            elif event.button == 5:   # scroll down
                if state.mode == AppMode.KB and state.kb_show_popup:
                    state._kb_popup_scroll = getattr(state, "_kb_popup_scroll", 0) + 20
                elif state.mode == AppMode.KB:
                    state.cnf_kb_scroll += 1
                else:
                    state.puzzle_list_scroll += 1

        elif event.type == pygame.KEYDOWN:
            self.handle_keydown(event)

        elif event.type == pygame.MOUSEMOTION:
            # Slider drag (SOLVE mode)
            if pygame.mouse.get_pressed()[0]:
                rects = getattr(state, "_hud_rects", {})
                slider = rects.get("speed_slider")
                if slider and slider.collidepoint(event.pos):
                    t = (event.pos[0] - slider.x) / max(1, slider.width)
                    state.speed = round(max(1.0, min(20.0, 1.0 + t * 19.0)), 1)
            # KB hover tracking
            if state.mode == AppMode.KB:
                self._update_kb_hover(event.pos)

    # ------------------------------------------------------------------
    # Click routing
    # ------------------------------------------------------------------

    def handle_click(self, pos: tuple[int, int]) -> None:
        app   = self._app
        state = app._state
        rects: dict[str, Any] = getattr(state, "_hud_rects", {})

        # --- KB reference popup takes priority ---
        if state.mode == AppMode.KB and state.kb_show_popup:
            if rects.get("kb_popup_close", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state.kb_show_popup = False
                return
            if rects.get("kb_popup_scroll_up", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state._kb_popup_scroll = max(0, getattr(state, "_kb_popup_scroll", 0) - 20)
                return
            if rects.get("kb_popup_scroll_down", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state._kb_popup_scroll = getattr(state, "_kb_popup_scroll", 0) + 20
                return
            # Click outside card → close
            from ui.layout import GRID_AREA_RECT
            # Any click that didn't hit a popup button dismisses the popup
            state.kb_show_popup = False
            return

        # --- Overlays take priority ---
        if state.show_puzzle_list:
            self._handle_puzzle_list_click(pos, rects)
            return
        if state.show_generate_dialog:
            return  # wait for generation to finish

        # --- Solver dropdown (must be checked before mode tabs) ---
        if rects.get("solver_select", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            state.show_solver_dropdown = not state.show_solver_dropdown
            return
        if state.show_solver_dropdown:
            for item_rect, sname in rects.get("_solver_dropdown_items", []):
                if item_rect.collidepoint(pos):
                    state.solver_name = sname
                    state.show_solver_dropdown = False
                    return
            state.show_solver_dropdown = False
            return  # consume click so nothing else fires

        # --- Mode tabs ---
        if rects.get("tab_play",  pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            app._switch_mode(AppMode.PLAY);  return
        if rects.get("tab_solve", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            app._switch_mode(AppMode.SOLVE); return
        if rects.get("tab_kb",    pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            app._switch_mode(AppMode.KB);    return

        # --- Solve controls ---
        if state.mode == AppMode.SOLVE:
            if rects.get("solve_play",    pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state.is_playing = True;  return
            if rects.get("solve_pause",   pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state.is_playing = False; return
            if rects.get("solve_step",    pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                app._advance_step(1);     return
            if rects.get("solve_restart", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                app._restart_solve();     return

        # --- Speed slider ---
        slider = rects.get("speed_slider")
        if slider and slider.collidepoint(pos) and state.mode == AppMode.SOLVE:
            t = (pos[0] - slider.x) / max(1, slider.width)
            state.speed = round(max(1.0, min(20.0, 1.0 + t * 19.0)), 1)
            return

        # --- Puzzle panel ---
        if rects.get("load_puzzle", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            state.show_puzzle_list = not state.show_puzzle_list
            return
        if rects.get("generate", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            app._start_generate(state.generate_size, state.generate_difficulty)
            return
        for sz in range(4, 10):
            if rects.get(f"gen_size_{sz}", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state.generate_size = sz
                return
        for diff in ("easy", "medium", "hard"):
            if rects.get(f"gen_diff_{diff}", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state.generate_difficulty = diff
                return

        # --- Play panel ---
        if rects.get("hint", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            if state.mode == AppMode.PLAY and state.board:
                app._apply_hint()
            return
        if rects.get("undo", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            if state.mode == AppMode.PLAY and state.board:
                state.board.undo()
            return
        if rects.get("notes_toggle", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            if state.mode == AppMode.PLAY:
                state.notes_mode = not state.notes_mode
            return

        # --- KB mode clicks ---
        if state.mode == AppMode.KB:
            if rects.get("kb_help_btn", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state.kb_show_popup = not state.kb_show_popup
                state._kb_popup_scroll = 0
                return
            if rects.get("cnf_kb_up", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state.cnf_kb_scroll = max(0, state.cnf_kb_scroll - 1)
                return
            if rects.get("cnf_kb_down", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                state.cnf_kb_scroll += 1
                return
            for row_rect, q_rect, lit in rects.get("_kb_fact_rows", []):
                if q_rect.collidepoint(pos):
                    # Toggle pin: clicking again unpins
                    state.kb_selected_lit = None if state.kb_selected_lit == lit else lit
                    return
            return  # no grid interaction in KB mode

        # --- Grid cell click ---
        if state.mode == AppMode.PLAY and state.board:
            self._handle_grid_click(pos)

    def _update_kb_hover(self, pos: tuple[int, int]) -> None:
        """Update kb_hovered_lit and kb_hovered_cell from mouse position."""
        state = self._app._state
        state.kb_hovered_lit = None
        for row_rect, _q_rect, lit in state._hud_rects.get("_kb_fact_rows", []):
            if row_rect.collidepoint(pos):
                state.kb_hovered_lit = lit
                break

        # Detect which grid cell the mouse is over
        state.kb_hovered_cell = None
        board = state.board
        if board is not None:
            from ui.layout import cell_rect, grid_geometry
            N = board.puzzle.N
            grid_rect, cell_size, gap = grid_geometry(N)
            for i in range(N):
                for j in range(N):
                    if cell_rect(i, j, grid_rect, cell_size, gap).collidepoint(pos):
                        state.kb_hovered_cell = (i, j)
                        return

    def _handle_puzzle_list_click(self, pos: tuple[int, int], rects: dict) -> None:
        app   = self._app
        state = app._state
        if rects.get("puzzle_list_close", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            state.show_puzzle_list = False
            return
        for row_rect, entry in rects.get("_puzzle_rows", []):
            if row_rect.collidepoint(pos):
                state.show_puzzle_list = False
                app._load_puzzle(entry)
                app._switch_mode(AppMode.PLAY)
                return

    def _handle_grid_click(self, pos: tuple[int, int]) -> None:
        from ui.layout import cell_rect, grid_geometry
        board = self._app._state.board
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

    # ------------------------------------------------------------------
    # Keyboard routing
    # ------------------------------------------------------------------

    def handle_keydown(self, event: pygame.event.Event) -> None:
        state = self._app._state

        # Esc closes any modal overlay
        if event.key == pygame.K_ESCAPE:
            if state.kb_show_popup:
                state.kb_show_popup = False
                return
            if state.show_puzzle_list:
                state.show_puzzle_list = False
                return
            if state.show_solver_dropdown:
                state.show_solver_dropdown = False
                return

        # Global shortcuts
        if event.key == pygame.K_F1:
            self._app._switch_mode(AppMode.PLAY);  return
        if event.key == pygame.K_F2:
            self._app._switch_mode(AppMode.SOLVE); return

        if state.mode == AppMode.PLAY and state.board:
            self._handle_play_key(event)
        elif state.mode == AppMode.SOLVE:
            self._handle_solve_key(event)

    def _handle_play_key(self, event: pygame.event.Event) -> None:
        state = self._app._state
        board = state.board
        if board is None or board.selected is None:
            return
        i, j = board.selected

        # Undo
        if event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL):
            board.undo()
            return

        # Notes toggle
        if event.key == pygame.K_n:
            state.notes_mode = not state.notes_mode
            return

        # Clear cell
        if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE, pygame.K_0):
            board.clear_value(i, j)
            return

        # Number entry (1..N)
        digit = _key_to_digit(event.key)
        if digit is not None and 1 <= digit <= board.puzzle.N:
            if state.notes_mode:
                if not board.toggle_note(i, j, digit):
                    state.shake_timers[(i, j)] = 0.4
            else:
                board.set_value(i, j, digit)
            if board.is_complete():
                state.set_notification("Puzzle solved!", 3.0)
            return

        # Arrow key navigation
        di, dj = _arrow_delta(event.key)
        if di != 0 or dj != 0:
            ni = max(0, min(board.puzzle.N - 1, i + di))
            nj = max(0, min(board.puzzle.N - 1, j + dj))
            board.selected = (ni, nj)

    def _handle_solve_key(self, event: pygame.event.Event) -> None:
        state = self._app._state
        if event.key == pygame.K_SPACE:
            state.is_playing = not state.is_playing
        elif event.key == pygame.K_RIGHT:
            self._app._advance_step(1)
        elif event.key == pygame.K_r:
            self._app._restart_solve()


# ---------------------------------------------------------------------------
# Key helpers (module-level so they can be tested independently)
# ---------------------------------------------------------------------------

def _key_to_digit(key: int) -> int | None:
    """Return 1-9 for digit keys (row and numpad), else None."""
    if pygame.K_1 <= key <= pygame.K_9:
        return key - pygame.K_0
    if pygame.K_KP1 <= key <= pygame.K_KP9:
        return key - pygame.K_KP0
    return None


def _arrow_delta(key: int) -> tuple[int, int]:
    """Return (di, dj) for arrow keys, (0, 0) for anything else."""
    return {
        pygame.K_UP:    (-1,  0),
        pygame.K_DOWN:  ( 1,  0),
        pygame.K_LEFT:  ( 0, -1),
        pygame.K_RIGHT: ( 0,  1),
    }.get(key, (0, 0))
