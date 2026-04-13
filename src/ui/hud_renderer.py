"""
HUD renderer: draws the title bar, mode tabs, and three side-panel sections
(solver controls, puzzle selection, play controls).

Button hit-test rects are stored in state._hud_rects so GameApplication
can resolve clicks without coupling the renderer to event handling.
"""
from __future__ import annotations

import pygame

import ui.theme as T
from models.game_state import AppMode, GameState
from ui.base import BaseRenderer
from ui.layout import (
    PLAY_PANEL_RECT,
    PUZZLE_PANEL_RECT,
    SCREEN_W,
    SIDE_PANEL_PADDING,
    SIDE_PANEL_RECT,
    SOLVER_PANEL_RECT,
    TAB_MENU_RECT,
    TAB_PLAY_RECT,
    TAB_SOLVE_RECT,
    TITLE_BAR_H,
    TITLE_BAR_RECT,
)


# ---------------------------------------------------------------------------
# Button helper
# ---------------------------------------------------------------------------

def _draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    fnt: pygame.font.Font,
    active: bool = False,
    disabled: bool = False,
    hover: bool = False,
) -> None:
    if disabled:
        bg = T.CLR_BTN_DISABLED
        fg = T.CLR_BTN_TEXT_DIS
    elif active:
        bg = T.CLR_BTN_ACTIVE
        fg = (255, 255, 255)
    elif hover:
        bg = T.CLR_BTN_HOVER
        fg = T.CLR_BTN_TEXT
    else:
        bg = T.CLR_BTN_NORMAL
        fg = T.CLR_BTN_TEXT

    pygame.draw.rect(surface, bg, rect, border_radius=4)
    pygame.draw.rect(surface, T.CLR_PANEL_BORDER, rect, 1, border_radius=4)
    txt = fnt.render(label, True, fg)
    trect = txt.get_rect(center=rect.center)
    surface.blit(txt, trect)


def _draw_label(surface, fnt, text, x, y, colour=None):
    colour = colour or T.CLR_LABEL
    txt = fnt.render(text, True, colour)
    surface.blit(txt, (x, y))
    return txt.get_height()


# ---------------------------------------------------------------------------
# HUD Renderer
# ---------------------------------------------------------------------------

class HudRenderer(BaseRenderer):

    def render(self, surface: pygame.Surface, state: GameState) -> None:
        # Initialise hit-test rect dict on state (duck-typed)
        if not hasattr(state, "_hud_rects"):
            state._hud_rects = {}

        mouse_pos = pygame.mouse.get_pos()

        self._draw_title_bar(surface, state, mouse_pos)
        self._draw_side_panel_bg(surface)
        self._draw_solver_panel(surface, state, mouse_pos)
        self._draw_puzzle_panel(surface, state, mouse_pos)
        self._draw_play_panel(surface, state, mouse_pos)

        # Overlay: puzzle list or generate dialog
        if state.show_puzzle_list:
            self._draw_puzzle_list_overlay(surface, state, mouse_pos)
        elif state.show_generate_dialog:
            self._draw_generate_dialog(surface, state, mouse_pos)

        # Solver dropdown drawn last so it appears above everything else
        if state.show_solver_dropdown:
            self._draw_solver_dropdown(surface, state, mouse_pos)

    # ------------------------------------------------------------------
    # Title bar
    # ------------------------------------------------------------------

    def _draw_title_bar(self, surface, state, mouse_pos):
        pygame.draw.rect(surface, (50, 80, 130), TITLE_BAR_RECT)

        # Title text
        fnt = T.font("title")
        txt = fnt.render("FUTOSHIKI", True, (255, 255, 255))
        surface.blit(txt, (14, (TITLE_BAR_H - txt.get_height()) // 2))

        # Mode tabs
        tabs = [
            ("PLAY",  AppMode.PLAY,  TAB_PLAY_RECT),
            ("SOLVE", AppMode.SOLVE, TAB_SOLVE_RECT),
            ("MENU",  AppMode.MENU,  TAB_MENU_RECT),
        ]
        fnt_tab = T.font("tab")
        for label, mode, rect in tabs:
            active = (state.mode == mode)
            bg = T.CLR_TAB_ACTIVE if active else T.CLR_TAB_INACTIVE
            fg = T.CLR_TAB_TEXT   if active else T.CLR_TAB_TEXT_INACT
            pygame.draw.rect(surface, bg, rect, border_radius=4)
            txt = fnt_tab.render(label, True, fg)
            trect = txt.get_rect(center=rect.center)
            surface.blit(txt, trect)
            state._hud_rects[f"tab_{label.lower()}"] = rect

    # ------------------------------------------------------------------
    # Side panel background
    # ------------------------------------------------------------------

    def _draw_side_panel_bg(self, surface):
        pygame.draw.rect(surface, T.CLR_PANEL_BG, SIDE_PANEL_RECT)
        pygame.draw.line(
            surface, T.CLR_PANEL_BORDER,
            (SIDE_PANEL_RECT.x, SIDE_PANEL_RECT.y),
            (SIDE_PANEL_RECT.x, SIDE_PANEL_RECT.bottom), 1,
        )

    # ------------------------------------------------------------------
    # Solver panel
    # ------------------------------------------------------------------

    def _draw_solver_panel(self, surface, state, mouse_pos):
        r = SOLVER_PANEL_RECT
        px = r.x + SIDE_PANEL_PADDING
        py = r.y + SIDE_PANEL_PADDING
        pw = r.width - 2 * SIDE_PANEL_PADDING

        fnt_lbl = T.font("hud_label")
        fnt_val = T.font("hud_value")
        fnt_btn = T.font("btn")

        # Section header
        _draw_label(surface, fnt_val, "SOLVER", px, py, T.CLR_LABEL_TITLE)
        py += 20

        # Solver selector dropdown button
        solver_names = {
            "astar_h2": "A* h2 (domain size)",
            "astar_h1": "A* h1 (empty cells)",
            "astar_h3": "A* h3 (min conflicts)",
            "astar_h4": "A* h4 (AC-3 domain)",
            "forward_chaining": "Forward Chaining",
            "btfc": "Backtrack + Fwd Chain",
            "forward_then_ac3": "FC -> AC3 + BC",
            "backward_chaining": "Backward Chaining",
            "ac3_backward_chaining": "AC3 + Backward Chain",
            "brute_force": "Brute Force",
        }
        display_name = solver_names.get(state.solver_name, state.solver_name)
        arrow = "v" if not state.show_solver_dropdown else "^"
        sel_rect = pygame.Rect(px, py, pw, 26)
        _draw_button(surface, sel_rect, f"{display_name}  {arrow}", fnt_btn,
                     active=state.show_solver_dropdown,
                     hover=sel_rect.collidepoint(mouse_pos))
        state._hud_rects["solver_select"] = sel_rect
        # Store solver_names for the dropdown overlay drawn at end of render()
        state._hud_rects["_solver_names"] = solver_names
        state._hud_rects["_solver_select_rect"] = sel_rect
        py += 32

        # Control buttons: Play / Pause / Step / Restart
        btn_w = (pw - 9) // 4
        in_solve = (state.mode == AppMode.SOLVE)
        can_step = in_solve and (not state.solve_steps.empty() or state.is_solving())
        solving_done = in_solve and state.solve_finished

        btns = [
            ("Play",  "solve_play",    in_solve and not state.is_playing and not solving_done),
            ("Pause", "solve_pause",   in_solve and state.is_playing),
            ("Step",  "solve_step",    can_step),
            ("Reset", "solve_restart", in_solve),
        ]
        bx = px
        for label, key, active in btns:
            br = pygame.Rect(bx, py, btn_w, 28)
            _draw_button(surface, br, label, fnt_btn,
                         active=active,
                         disabled=not in_solve,
                         hover=br.collidepoint(mouse_pos) and in_solve)
            state._hud_rects[key] = br
            bx += btn_w + 3
        py += 34

        # Speed slider
        _draw_label(surface, fnt_lbl, f"Speed: {state.speed:.1f}×", px, py)
        py += 16
        slider_rect = pygame.Rect(px, py, pw, 12)
        self._draw_slider(surface, slider_rect, state.speed, 1.0, 20.0, in_solve)
        state._hud_rects["speed_slider"] = slider_rect
        py += 20

        # Stats
        _draw_label(surface, fnt_lbl, f"Nodes:      {state.node_count}", px, py)
        py += 16
        _draw_label(surface, fnt_lbl, f"Time:       {state.elapsed_ms:.1f} ms", px, py)
        py += 16
        _draw_label(surface, fnt_lbl, f"Backtracks: {state.backtrack_count}", px, py)
        py += 16

        # Status line
        if in_solve:
            if state.solve_finished:
                status = "Solved!" if state.solve_succeeded else "No solution"
                colour = (0, 140, 0) if state.solve_succeeded else (200, 30, 30)
            elif state.is_solving():
                status = "Solving…"
                colour = T.CLR_LABEL
            else:
                status = "Paused"
                colour = T.CLR_LABEL
            _draw_label(surface, fnt_lbl, status, px, py, colour)

        # Divider
        pygame.draw.line(
            surface, T.CLR_PANEL_BORDER,
            (r.x, r.bottom - 1), (r.right, r.bottom - 1), 1,
        )

    # ------------------------------------------------------------------
    # Puzzle panel
    # ------------------------------------------------------------------

    def _draw_puzzle_panel(self, surface, state, mouse_pos):
        r = PUZZLE_PANEL_RECT
        px = r.x + SIDE_PANEL_PADDING
        py = r.y + SIDE_PANEL_PADDING
        pw = r.width - 2 * SIDE_PANEL_PADDING

        fnt_lbl = T.font("hud_label")
        fnt_val = T.font("hud_value")
        fnt_btn = T.font("btn")

        _draw_label(surface, fnt_val, "PUZZLE", px, py, T.CLR_LABEL_TITLE)
        py += 20

        # Currently loaded puzzle name
        if state.board is not None:
            name = getattr(state, "_puzzle_name", "Custom")
            _draw_label(surface, fnt_lbl, f"Loaded: {name}", px, py)
        else:
            _draw_label(surface, fnt_lbl, "No puzzle loaded", px, py)
        py += 18

        # Load from corpus button
        load_rect = pygame.Rect(px, py, pw, 26)
        _draw_button(surface, load_rect, "Load Puzzle…", fnt_btn,
                     active=state.show_puzzle_list,
                     hover=load_rect.collidepoint(mouse_pos))
        state._hud_rects["load_puzzle"] = load_rect
        py += 32

        # Generate section — size row
        _draw_label(surface, fnt_lbl, "Generate  size:", px, py)
        py += 16
        sizes = [4, 5, 6, 7, 8, 9]
        bw = (pw - (len(sizes) - 1) * 3) // len(sizes)
        bx = px
        for sz in sizes:
            sr = pygame.Rect(bx, py, bw, 24)
            _draw_button(surface, sr, str(sz), fnt_btn,
                         active=(state.generate_size == sz),
                         hover=sr.collidepoint(mouse_pos))
            state._hud_rects[f"gen_size_{sz}"] = sr
            bx += bw + 3
        py += 30

        # Difficulty row
        _draw_label(surface, fnt_lbl, "Difficulty:", px, py)
        py += 16
        diffs = [("Easy", "easy"), ("Med", "medium"), ("Hard", "hard")]
        dw = (pw - 2 * 4) // 3
        bx = px
        for label, diff in diffs:
            dr = pygame.Rect(bx, py, dw, 24)
            _draw_button(surface, dr, label, fnt_btn,
                         active=(state.generate_difficulty == diff),
                         hover=dr.collidepoint(mouse_pos))
            state._hud_rects[f"gen_diff_{diff}"] = dr
            bx += dw + 4
        py += 30

        gen_rect = pygame.Rect(px, py, pw, 26)
        _draw_button(surface, gen_rect, "Generate!", fnt_btn,
                     hover=gen_rect.collidepoint(mouse_pos))
        state._hud_rects["generate"] = gen_rect
        py += 32

        # Divider
        pygame.draw.line(
            surface, T.CLR_PANEL_BORDER,
            (r.x, r.bottom - 1), (r.right, r.bottom - 1), 1,
        )

    # ------------------------------------------------------------------
    # Play panel
    # ------------------------------------------------------------------

    def _draw_play_panel(self, surface, state, mouse_pos):
        r = PLAY_PANEL_RECT
        px = r.x + SIDE_PANEL_PADDING
        py = r.y + SIDE_PANEL_PADDING
        pw = r.width - 2 * SIDE_PANEL_PADDING

        fnt_val = T.font("hud_value")
        fnt_btn = T.font("btn")

        _draw_label(surface, fnt_val, "PLAY", px, py, T.CLR_LABEL_TITLE)
        py += 20

        in_play = (state.mode == AppMode.PLAY)
        has_board = state.board is not None

        btn_w = (pw - 4) // 2
        hint_rect = pygame.Rect(px, py, btn_w, 26)
        undo_rect  = pygame.Rect(px + btn_w + 4, py, btn_w, 26)
        _draw_button(surface, hint_rect, "Hint", fnt_btn,
                     disabled=not (in_play and has_board),
                     hover=hint_rect.collidepoint(mouse_pos) and in_play and has_board)
        _draw_button(surface, undo_rect, "Undo", fnt_btn,
                     disabled=not (in_play and has_board),
                     hover=undo_rect.collidepoint(mouse_pos) and in_play and has_board)
        state._hud_rects["hint"] = hint_rect
        state._hud_rects["undo"] = undo_rect
        py += 32

        notes_rect = pygame.Rect(px, py, pw, 26)
        _draw_button(surface, notes_rect,
                     "Notes: ON" if state.notes_mode else "Notes: OFF",
                     fnt_btn,
                     active=state.notes_mode,
                     disabled=not (in_play and has_board),
                     hover=notes_rect.collidepoint(mouse_pos) and in_play and has_board)
        state._hud_rects["notes_toggle"] = notes_rect

    # ------------------------------------------------------------------
    # Slider
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_slider(surface, rect, value, min_v, max_v, enabled):
        track_col = T.CLR_SLIDER_TRACK if enabled else T.CLR_BTN_DISABLED
        thumb_col = T.CLR_SLIDER_THUMB if enabled else T.CLR_BTN_DISABLED
        pygame.draw.rect(surface, track_col, rect, border_radius=4)
        if max_v > min_v:
            t = (value - min_v) / (max_v - min_v)
            tx = int(rect.x + t * rect.width)
            thumb = pygame.Rect(tx - 6, rect.y - 4, 12, rect.height + 8)
            pygame.draw.rect(surface, thumb_col, thumb, border_radius=4)

    # ------------------------------------------------------------------
    # Puzzle list overlay
    # ------------------------------------------------------------------

    def _draw_puzzle_list_overlay(self, surface, state, mouse_pos):
        if not hasattr(state, "_puzzle_entries"):
            return

        entries = state._puzzle_entries
        overlay_w = 380
        overlay_h = min(520, TITLE_BAR_H + 40 + len(entries) * 28 + 16)
        ox = (SCREEN_W - overlay_w) // 2
        oy = TITLE_BAR_H + 30

        # Background
        bg = pygame.Rect(ox, oy, overlay_w, overlay_h)
        pygame.draw.rect(surface, (245, 245, 240), bg, border_radius=6)
        pygame.draw.rect(surface, T.CLR_PANEL_BORDER, bg, 2, border_radius=6)

        fnt_val = T.font("hud_value")
        fnt_lbl = T.font("hud_label")
        fnt_btn = T.font("btn")

        # Header
        py = oy + 10
        _draw_label(surface, fnt_val, "Select a Puzzle", ox + 12, py, T.CLR_LABEL_TITLE)
        close_rect = pygame.Rect(bg.right - 34, oy + 8, 26, 22)
        _draw_button(surface, close_rect, "X", fnt_btn, hover=close_rect.collidepoint(mouse_pos))
        state._hud_rects["puzzle_list_close"] = close_rect
        py += 28

        # Entries (scrolled)
        row_h = 28
        visible = max(1, (overlay_h - 50) // row_h)
        scroll = max(0, min(state.puzzle_list_scroll, max(0, len(entries) - visible)))
        state.puzzle_list_scroll = scroll

        state._hud_rects["_puzzle_rows"] = []
        for idx in range(scroll, min(scroll + visible, len(entries))):
            entry = entries[idx]
            ry = py + (idx - scroll) * row_h
            row_rect = pygame.Rect(ox + 6, ry, overlay_w - 12, row_h - 2)
            hover = row_rect.collidepoint(mouse_pos)
            bg_c = T.CLR_BTN_HOVER if hover else (255, 255, 255)
            pygame.draw.rect(surface, bg_c, row_rect, border_radius=3)
            label = f"{entry.name.replace('_', ' ')}   ({entry.size}×{entry.size}  {entry.difficulty})"
            txt = fnt_lbl.render(label, True, T.CLR_LABEL)
            surface.blit(txt, (row_rect.x + 8, row_rect.y + (row_h - txt.get_height()) // 2 - 1))
            state._hud_rects["_puzzle_rows"].append((row_rect, entry))

    # ------------------------------------------------------------------
    # Generate dialog
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Solver dropdown overlay
    # ------------------------------------------------------------------

    def _draw_solver_dropdown(self, surface, state, mouse_pos):
        solver_names: dict = state._hud_rects.get("_solver_names", {})
        anchor: pygame.Rect = state._hud_rects.get("_solver_select_rect")
        if anchor is None or not solver_names:
            return

        fnt_btn = T.font("btn")
        row_h = 26
        pad = 4
        # solver_names dict preserves insertion order — use it as the item list
        items = list(solver_names.items())
        overlay_w = anchor.width
        overlay_h = len(items) * row_h + 2 * pad

        ox = anchor.x
        oy = anchor.bottom + 2

        bg_rect = pygame.Rect(ox, oy, overlay_w, overlay_h)
        pygame.draw.rect(surface, (245, 245, 240), bg_rect, border_radius=4)
        pygame.draw.rect(surface, T.CLR_PANEL_BORDER, bg_rect, 1, border_radius=4)

        state._hud_rects["_solver_dropdown_items"] = []
        for idx, (skey, sname) in enumerate(items):
            iy = oy + pad + idx * row_h
            item_rect = pygame.Rect(ox + 2, iy, overlay_w - 4, row_h - 2)
            is_current = (state.solver_name == skey)
            is_hover = item_rect.collidepoint(mouse_pos)
            if is_current:
                bg = T.CLR_BTN_ACTIVE
                fg = (255, 255, 255)
            elif is_hover:
                bg = T.CLR_BTN_HOVER
                fg = T.CLR_BTN_TEXT
            else:
                bg = (245, 245, 240)
                fg = T.CLR_LABEL
            pygame.draw.rect(surface, bg, item_rect, border_radius=3)
            txt = fnt_btn.render(sname, True, fg)
            surface.blit(txt, (item_rect.x + 6, item_rect.centery - txt.get_height() // 2))
            state._hud_rects["_solver_dropdown_items"].append((item_rect, skey))

    # ------------------------------------------------------------------
    # Generate dialog
    # ------------------------------------------------------------------

    def _draw_generate_dialog(self, surface, state, mouse_pos):
        overlay_w = 300
        overlay_h = 140
        ox = (SCREEN_W - overlay_w) // 2
        oy = TITLE_BAR_H + 80

        bg = pygame.Rect(ox, oy, overlay_w, overlay_h)
        pygame.draw.rect(surface, (245, 245, 240), bg, border_radius=6)
        pygame.draw.rect(surface, T.CLR_PANEL_BORDER, bg, 2, border_radius=6)

        fnt_val = T.font("hud_value")
        fnt_btn = T.font("btn")

        py = oy + 12
        _draw_label(surface, fnt_val, "Generating puzzle…", ox + 12, py, T.CLR_LABEL_TITLE)
        py += 28
        _draw_label(surface, T.font("hud_label"), "This may take a few seconds.", ox + 12, py)
