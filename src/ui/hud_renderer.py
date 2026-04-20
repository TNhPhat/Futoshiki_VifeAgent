"""
HUD renderer: draws the title bar, mode tabs, and three side-panel sections
(solver controls, puzzle selection, play controls).

Button hit-test rects are stored in state._hud_rects so GameApplication
can resolve clicks without coupling the renderer to event handling.
"""
from __future__ import annotations

from collections import Counter

import pygame

import ui.theme as T
from models.game_state import AppMode, GameState
from ui.base import BaseRenderer
from ui.layout import (
    GRID_AREA_RECT,
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

# Re-export so import lines stay short
_SIDE = SIDE_PANEL_RECT

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

def _explain_literal(lit) -> list[str]:
    """Return 1-3 human-readable lines explaining what a fact means."""
    n, args, neg = lit.name, lit.args, lit.negated
    if n == "Val":
        r, c, v = args
        if neg:
            return [f"Cell ({r+1},{c+1}) cannot hold", f"value {v}."]
        return [f"Cell ({r+1},{c+1}) holds", f"value {v}."]
    if n == "Given":
        r, c, v = args
        return [f"Cell ({r+1},{c+1}) is a clue:", f"pre-filled with value {v}."]
    if n == "NotVal":
        r, c, v = args
        return [f"Cell ({r+1},{c+1}) is excluded", f"from value {v}."]
    if n == "ValidVal":
        r, c, v = args
        return [f"Value {v} is valid", f"for cell ({r+1},{c+1})."]
    if n == "LessH":
        r, c = args
        if neg:
            return [f"Horiz. constraint:", f"NOT (cell({r+1},{c+1}) < cell({r+1},{c+2}))."]
        return [f"Horiz. constraint:", f"cell({r+1},{c+1}) < cell({r+1},{c+2})."]
    if n == "GreaterH":
        r, c = args
        if neg:
            return [f"Horiz. constraint:", f"NOT (cell({r+1},{c+1}) > cell({r+1},{c+2}))."]
        return [f"Horiz. constraint:", f"cell({r+1},{c+1}) > cell({r+1},{c+2})."]
    if n == "LessV":
        r, c = args
        if neg:
            return [f"Vert. constraint:", f"NOT (cell({r+1},{c+1}) < cell({r+2},{c+1}))."]
        return [f"Vert. constraint:", f"cell({r+1},{c+1}) < cell({r+2},{c+1})."]
    if n == "GreaterV":
        r, c = args
        if neg:
            return [f"Vert. constraint:", f"NOT (cell({r+1},{c+1}) > cell({r+2},{c+1}))."]
        return [f"Vert. constraint:", f"cell({r+1},{c+1}) > cell({r+2},{c+1})."]
    if n == "Less":
        v1, v2 = args
        if neg:
            return [f"Numeric relation:", f"NOT ({v1} < {v2})."]
        return [f"Numeric relation:", f"{v1} < {v2}."]
    if n == "Geq":
        v1, v2 = args
        if neg:
            return [f"Numeric relation:", f"NOT ({v2} >= {v1})."]
        return [f"Numeric relation:", f"{v2} >= {v1}."]
    if n == "Diff":
        a, b = args
        if neg:
            return [f"Numeric relation:", f"NOT ({a} != {b})."]
        return [f"Numeric relation:", f"{a} != {b}."]
    if n == "Domain":
        return [f"Value {args[0]} is in", "the domain (1..N)."]
    sign = "~" if neg else ""
    return [f"{sign}{n}({','.join(str(a) for a in args)})"]

class HudRenderer(BaseRenderer):

    def render(self, surface: pygame.Surface, state: GameState) -> None:
        # Reset hit-test rects every frame so stale entries from a previous
        # mode cannot be accidentally triggered in the current mode.
        state._hud_rects = {}

        mouse_pos = pygame.mouse.get_pos()

        self._draw_title_bar(surface, state, mouse_pos)
        self._draw_side_panel_bg(surface)
        if state.mode == AppMode.KB:
            self._draw_kb_panel(surface, state, mouse_pos)
        else:
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

        # KB reference popup drawn on top of everything
        if state.mode == AppMode.KB and state.kb_show_popup:
            self._draw_kb_popup(surface, state, mouse_pos)

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
            ("KB",    AppMode.KB,    TAB_MENU_RECT),
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
            key = "tab_kb" if label == "KB" else f"tab_{label.lower()}"
            state._hud_rects[key] = rect

    def _draw_side_panel_bg(self, surface):
        pygame.draw.rect(surface, T.CLR_PANEL_BG, SIDE_PANEL_RECT)
        pygame.draw.line(
            surface, T.CLR_PANEL_BORDER,
            (SIDE_PANEL_RECT.x, SIDE_PANEL_RECT.y),
            (SIDE_PANEL_RECT.x, SIDE_PANEL_RECT.bottom), 1,
        )

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
            "forward_then_backward": "FC -> Backward Chain",
            "backward_chaining": "Backward Chaining",
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
        _draw_label(surface, fnt_lbl, f"Speed: {state.speed:.1f}x", px, py)
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
                status = "Solving..."
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
        _draw_button(surface, load_rect, "Load Puzzle...", fnt_btn,
                     active=state.show_puzzle_list,
                     hover=load_rect.collidepoint(mouse_pos))
        state._hud_rects["load_puzzle"] = load_rect
        py += 32

        # Generate section -- size row
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

    def _draw_kb_panel(self, surface, state, mouse_pos):
        r = SIDE_PANEL_RECT
        px = r.x + SIDE_PANEL_PADDING
        pw = r.width - 2 * SIDE_PANEL_PADDING
        py = r.y + SIDE_PANEL_PADDING

        fnt_lbl = T.font("hud_label")
        fnt_val = T.font("hud_value")
        fnt_btn = T.font("btn")

        kb = state.cnf_kb

        _draw_label(surface, fnt_val, "CNF KNOWLEDGE BASE", px, py, T.CLR_LABEL_TITLE)
        help_rect = pygame.Rect(r.right - SIDE_PANEL_PADDING - 22, py, 22, 20)
        _draw_button(surface, help_rect, "?", fnt_btn,
                     active=state.kb_show_popup,
                     hover=help_rect.collidepoint(mouse_pos))
        state._hud_rects["kb_help_btn"] = help_rect
        py += 22

        if kb is None:
            _draw_label(surface, fnt_lbl, "No puzzle loaded.", px, py)
            return

        lengths = Counter(len(c) for c in kb.clauses)
        unit_n   = lengths.get(1, 0)
        binary_n = lengths.get(2, 0)
        longer_n = sum(v for k, v in lengths.items() if k >= 3)

        _draw_label(surface, fnt_lbl,
                    f"Total: {len(kb.clauses)}    Unit (facts): {unit_n}", px, py)
        py += 16
        _draw_label(surface, fnt_lbl,
                    f"Binary: {binary_n}    Longer (3+): {longer_n}", px, py)
        py += 20

        pygame.draw.line(surface, T.CLR_PANEL_BORDER,
                         (px, py), (r.right - SIDE_PANEL_PADDING, py), 1)
        py += 8

        tab_w = (pw - 4) // 2
        facts_tab = pygame.Rect(px,           py, tab_w, 22)
        rules_tab = pygame.Rect(px + tab_w + 4, py, pw - tab_w - 4, 22)
        _draw_button(surface, facts_tab, "FACTS", fnt_btn,
                     active=(state.kb_panel_view == "facts"),
                     hover=facts_tab.collidepoint(mouse_pos))
        _draw_button(surface, rules_tab, "RULES", fnt_btn,
                     active=(state.kb_panel_view == "rules"),
                     hover=rules_tab.collidepoint(mouse_pos))
        state._hud_rects["kb_tab_facts"] = facts_tab
        state._hud_rects["kb_tab_rules"] = rules_tab
        py += 28

        info_box_h   = 12 + 18 + 3 * 15 + 8
        info_box_top = r.bottom - SIDE_PANEL_PADDING - info_box_h

        row_h  = 20
        q_w    = 16
        list_start_y = py + 21   # after list-header + arrows row
        available_h  = info_box_top - list_start_y - 4
        visible_rows = max(1, available_h // row_h)

        if state.kb_panel_view == "facts":
            facts = sorted(kb.facts, key=lambda l: (l.name, l.args, l.negated))
            _draw_label(surface, fnt_val, "FACTS", px, py, T.CLR_LABEL_TITLE)

            arrow_w, arrow_h = 18, 17
            down_rect = pygame.Rect(r.right - SIDE_PANEL_PADDING - arrow_w, py, arrow_w, arrow_h)
            up_rect   = pygame.Rect(down_rect.x - arrow_w - 2, py, arrow_w, arrow_h)

            max_scroll = max(0, len(facts) - visible_rows)
            scroll = max(0, min(state.cnf_kb_scroll, max_scroll))
            state.cnf_kb_scroll = scroll

            if facts:
                end_idx = min(scroll + visible_rows, len(facts))
                pos_txt = fnt_lbl.render(f"{scroll+1}-{end_idx}/{len(facts)}",
                                         True, T.CLR_LABEL)
                surface.blit(pos_txt, (up_rect.x - pos_txt.get_width() - 4, py + 2))

            _draw_button(surface, up_rect,   "^", fnt_btn,
                         disabled=(scroll == 0),
                         hover=up_rect.collidepoint(mouse_pos) and scroll > 0)
            _draw_button(surface, down_rect, "v", fnt_btn,
                         disabled=(scroll >= max_scroll),
                         hover=down_rect.collidepoint(mouse_pos) and scroll < max_scroll)
            state._hud_rects["cnf_kb_up"]   = up_rect
            state._hud_rects["cnf_kb_down"] = down_rect
            py = list_start_y

            fact_rows: list = []
            if not facts:
                _draw_label(surface, fnt_lbl, "(no unit facts)", px + 4, py)
            else:
                for lit in facts[scroll : scroll + visible_rows]:
                    row_rect = pygame.Rect(px, py, pw - q_w - 4, row_h)
                    q_rect   = pygame.Rect(r.right - SIDE_PANEL_PADDING - q_w,
                                           py + 2, q_w, row_h - 4)
                    is_hover = row_rect.collidepoint(mouse_pos) or q_rect.collidepoint(mouse_pos)
                    if is_hover:
                        pygame.draw.rect(surface, T.CLR_BTN_HOVER, row_rect, border_radius=3)
                        fg = T.CLR_BTN_TEXT
                    else:
                        fg = T.CLR_LABEL
                    sign     = "~" if lit.negated else " "
                    args_str = ",".join(str(a) for a in lit.args)
                    text     = f"{sign}{lit.name}({args_str})"
                    if len(text) > 22:
                        text = text[:19] + "..."
                    lbl = fnt_lbl.render(text, True, fg)
                    surface.blit(lbl, (px + 4, py + (row_h - lbl.get_height()) // 2))
                    _draw_button(surface, q_rect, "?", fnt_btn,
                                 hover=q_rect.collidepoint(mouse_pos))
                    fact_rows.append((row_rect, q_rect, lit))
                    py += row_h
            state._hud_rects["_kb_fact_rows"] = fact_rows
            state._hud_rects["_kb_rule_rows"] = []

        else:
            rules = [c for c in kb.clauses if len(c) > 1]
            _draw_label(surface, fnt_val, "RULES", px, py, T.CLR_LABEL_TITLE)

            arrow_w, arrow_h = 18, 17
            down_rect = pygame.Rect(r.right - SIDE_PANEL_PADDING - arrow_w, py, arrow_w, arrow_h)
            up_rect   = pygame.Rect(down_rect.x - arrow_w - 2, py, arrow_w, arrow_h)

            max_scroll = max(0, len(rules) - visible_rows)
            scroll = max(0, min(state.kb_rules_scroll, max_scroll))
            state.kb_rules_scroll = scroll

            if rules:
                end_idx = min(scroll + visible_rows, len(rules))
                pos_txt = fnt_lbl.render(f"{scroll+1}-{end_idx}/{len(rules)}",
                                         True, T.CLR_LABEL)
                surface.blit(pos_txt, (up_rect.x - pos_txt.get_width() - 4, py + 2))

            _draw_button(surface, up_rect,   "^", fnt_btn,
                         disabled=(scroll == 0),
                         hover=up_rect.collidepoint(mouse_pos) and scroll > 0)
            _draw_button(surface, down_rect, "v", fnt_btn,
                         disabled=(scroll >= max_scroll),
                         hover=down_rect.collidepoint(mouse_pos) and scroll < max_scroll)
            state._hud_rects["cnf_kb_up"]   = up_rect
            state._hud_rects["cnf_kb_down"] = down_rect
            py = list_start_y

            rule_rows: list = []
            if not rules:
                _draw_label(surface, fnt_lbl, "(no multi-literal clauses)", px + 4, py)
            else:
                for clause in rules[scroll : scroll + visible_rows]:
                    row_rect = pygame.Rect(px, py, pw, row_h)
                    is_hover = (row_rect.collidepoint(mouse_pos) or
                                clause is state.kb_hovered_clause)
                    if is_hover:
                        pygame.draw.rect(surface, T.CLR_BTN_HOVER, row_rect, border_radius=3)
                        fg = T.CLR_BTN_TEXT
                    else:
                        fg = T.CLR_LABEL
                    text = _format_clause(clause)
                    lbl = fnt_lbl.render(text, True, fg)
                    surface.blit(lbl, (px + 4, py + (row_h - lbl.get_height()) // 2))
                    rule_rows.append((row_rect, clause))
                    py += row_h
            state._hud_rects["_kb_rule_rows"] = rule_rows
            state._hud_rects["_kb_fact_rows"] = []

        pygame.draw.line(surface, T.CLR_PANEL_BORDER,
                         (px, info_box_top), (r.right - SIDE_PANEL_PADDING, info_box_top), 1)
        ipy = info_box_top + 8

        if state.kb_hovered_clause is not None:
            _draw_label(surface, fnt_val, "CLAUSE", px, ipy, T.CLR_LABEL_TITLE)
            ipy += 18
            _draw_label(surface, fnt_lbl, f"Rule: {_format_clause(state.kb_hovered_clause)}", px + 4, ipy)
            ipy += 15
            for line in _explain_clause(state.kb_hovered_clause):
                _draw_label(surface, fnt_lbl, line, px + 4, ipy)
                ipy += 15
        else:
            lit_to_explain = state.kb_selected_lit or state.kb_hovered_lit
            if lit_to_explain is not None:
                _draw_label(surface, fnt_val, "ABOUT", px, ipy, T.CLR_LABEL_TITLE)
                ipy += 18
                for line in _explain_literal(lit_to_explain):
                    _draw_label(surface, fnt_lbl, line, px + 4, ipy)
                    ipy += 15
            else:
                view = state.kb_panel_view
                _draw_label(surface, fnt_lbl,
                            "Hover a fact/rule to highlight" if view == "facts"
                            else "Hover a rule to highlight", px, ipy)
                ipy += 15
                _draw_label(surface, fnt_lbl, "its cells on the grid.", px, ipy)

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
            label = f"{entry.name.replace('_', ' ')}   ({entry.size}x{entry.size}  {entry.difficulty})"
            txt = fnt_lbl.render(label, True, T.CLR_LABEL)
            surface.blit(txt, (row_rect.x + 8, row_rect.y + (row_h - txt.get_height()) // 2 - 1))
            state._hud_rects["_puzzle_rows"].append((row_rect, entry))

    def _draw_solver_dropdown(self, surface, state, mouse_pos):
        solver_names: dict = state._hud_rects.get("_solver_names", {})
        anchor: pygame.Rect = state._hud_rects.get("_solver_select_rect")
        if anchor is None or not solver_names:
            return

        fnt_btn = T.font("btn")
        row_h = 26
        pad = 4
        # solver_names dict preserves insertion order -- use it as the item list
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

    def _draw_kb_popup(self, surface, state, mouse_pos):
        """Modal overlay covering the grid area that explains all CNF clauses."""
        fnt_lbl = T.font("hud_label")
        fnt_val = T.font("hud_value")
        fnt_btn = T.font("btn")

        # Dim the grid area
        dim = pygame.Surface((GRID_AREA_RECT.width, GRID_AREA_RECT.height), pygame.SRCALPHA)
        dim.fill((20, 20, 20, 180))
        surface.blit(dim, GRID_AREA_RECT.topleft)

        # Card dimensions
        card_w = min(580, GRID_AREA_RECT.width - 40)
        card_h = min(520, GRID_AREA_RECT.height - 40)
        card_x = GRID_AREA_RECT.x + (GRID_AREA_RECT.width  - card_w) // 2
        card_y = GRID_AREA_RECT.y + (GRID_AREA_RECT.height - card_h) // 2
        card   = pygame.Rect(card_x, card_y, card_w, card_h)

        pygame.draw.rect(surface, (248, 248, 245), card, border_radius=8)
        pygame.draw.rect(surface, T.CLR_PANEL_BORDER, card, 2, border_radius=8)

        # Top bar: title text + scroll arrows + close button
        _draw_label(surface, fnt_val, "CNF CLAUSE REFERENCE",
                    card_x + 14, card_y + 10, T.CLR_LABEL_TITLE)
        close_rect = pygame.Rect(card.right - 32, card.y + 8, 24, 22)
        _draw_button(surface, close_rect, "X", fnt_btn,
                     hover=close_rect.collidepoint(mouse_pos))
        state._hud_rects["kb_popup_close"] = close_rect

        # Content area with clipping
        content_rect = pygame.Rect(card_x + 14, card_y + 36, card_w - 28, card_h - 44)
        scroll_offset = getattr(state, "_kb_popup_scroll", 0)

        # Build all content lines first so we can compute total height
        # Skip the title item since it's drawn in the fixed top bar
        sections = [s for s in _KB_POPUP_SECTIONS if s[0] != "title"]

        line_h   = 16
        head_h   = 22
        sep_h    = 10
        total_h  = 0
        for kind, *data in sections:
            if kind == "heading":
                total_h += head_h
            elif kind == "text":
                total_h += line_h
            elif kind == "sep":
                total_h += sep_h

        # Clamp scroll
        visible_h = content_rect.height
        max_scroll = max(0, total_h - visible_h)
        scroll_offset = max(0, min(scroll_offset, max_scroll))
        state._kb_popup_scroll = scroll_offset

        # Scroll arrows (top-right of card, left of close button)
        up_rect_p   = pygame.Rect(card.right - 84, card_y + 8, 22, 22)
        down_rect_p = pygame.Rect(card.right - 58, card_y + 8, 22, 22)
        _draw_button(surface, up_rect_p, "^", fnt_btn,
                     disabled=(scroll_offset == 0),
                     hover=up_rect_p.collidepoint(mouse_pos) and scroll_offset > 0)
        _draw_button(surface, down_rect_p, "v", fnt_btn,
                     disabled=(scroll_offset >= max_scroll),
                     hover=down_rect_p.collidepoint(mouse_pos) and scroll_offset < max_scroll)
        state._hud_rects["kb_popup_scroll_up"]   = up_rect_p
        state._hud_rects["kb_popup_scroll_down"] = down_rect_p

        # Separator under top bar
        pygame.draw.line(surface, T.CLR_PANEL_BORDER,
                         (card_x + 8, card_y + 34), (card.right - 8, card_y + 34), 1)

        # Clip drawing to content rect
        old_clip = surface.get_clip()
        surface.set_clip(content_rect)

        py = content_rect.y - scroll_offset
        col_left  = card_x + 14
        col_right = card_x + card_w // 2 + 6

        for item in sections:
            kind = item[0]
            if kind == "heading":
                txt = fnt_val.render(item[1], True, (60, 90, 160))
                surface.blit(txt, (col_left, py))
                py += head_h
            elif kind == "text":
                # item = ("text", left_text, right_text_or_None)
                left_s  = item[1]
                right_s = item[2] if len(item) > 2 else None
                ltxt = fnt_lbl.render(left_s, True, T.CLR_LABEL)
                surface.blit(ltxt, (col_left + 8, py))
                if right_s:
                    rtxt = fnt_lbl.render(right_s, True, T.CLR_LABEL)
                    surface.blit(rtxt, (col_right, py))
                py += line_h
            elif kind == "sep":
                mid_y = py + sep_h // 2
                pygame.draw.line(surface, T.CLR_PANEL_BORDER,
                                 (col_left, mid_y), (card.right - 14, mid_y), 1)
                py += sep_h

        surface.set_clip(old_clip)

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
        _draw_label(surface, fnt_val, "Generating puzzle...", ox + 12, py, T.CLR_LABEL_TITLE)
        py += 28
        _draw_label(surface, T.font("hud_label"), "This may take a few seconds.", ox + 12, py)

def _format_lit_short(lit) -> str:
    """Compact single-literal string for clause display rows."""
    sign = "~" if lit.negated else ""
    n, args = lit.name, lit.args
    if n in ("Val", "NotVal", "Given", "ValidVal"):
        return f"{sign}{n}({args[0]},{args[1]},{args[2]})"
    if n in ("LessH", "GreaterH", "LessV", "GreaterV"):
        return f"{sign}{n}({args[0]},{args[1]})"
    if n == "Less":
        return f"{sign}Less({args[0]},{args[1]})"
    args_str = ",".join(str(a) for a in args)
    return f"{sign}{n}({args_str})"


def _format_clause(clause) -> str:
    """One-line representation of a multi-literal clause, truncated to ~30 chars."""
    parts = [_format_lit_short(l) for l in clause]
    joined = " | ".join(parts)
    if len(joined) > 30:
        joined = joined[:27] + "..."
    return joined


def _explain_clause(clause) -> list[str]:
    """Return 1-4 human-readable lines describing a multi-literal clause."""
    lits = clause
    n = len(lits)

    # Identify cells involved
    cells = []
    seen: set = set()
    for lit in lits:
        na, args = lit.name, lit.args
        if na in ("Val", "NotVal", "Given"):
            c = (args[0], args[1])
            if c not in seen:
                seen.add(c); cells.append(c)

    # Classify by structure
    names = [l.name for l in lits]

    if set(names) == {"Val"} or (all(l.negated for l in lits) and
                                  all(l.name in ("Val", "NotVal") for l in lits)):
        if n == 2 and len(cells) == 2 and lits[0].args[2] == lits[1].args[2]:
            r, c1 = cells[0]; _, c2 = cells[1]
            if c1 == c2:
                return [f"Col {c1+1}: value {lits[0].args[2]}",
                        "cannot appear twice."]
            elif cells[0][0] == cells[1][0]:
                return [f"Row {r+1}: value {lits[0].args[2]}",
                        "cannot appear twice."]
        if n == 2 and len(cells) == 2:
            r, c = cells[0]
            return [f"Cell ({r+1},{c+1}) cannot hold",
                    f"both values at once."]

    if "Less" in names and n == 3:
        val_lits = [l for l in lits if l.name in ("Val", "NotVal") and l.negated]
        less_lit = next((l for l in lits if l.name == "Less"), None)
        if len(val_lits) == 2 and less_lit:
            (r1,c1,v1), (r2,c2,v2) = val_lits[0].args, val_lits[1].args
            a, b = less_lit.args
            return [f"If ({r1+1},{c1+1})={v1} and ({r2+1},{c2+1})={v2}",
                    f"then {a}<{b} must hold",
                    f"(inequality enforcement)."]

    if n >= 2 and all(l.name == "Val" and not l.negated for l in lits):
        if cells:
            r = cells[0][0]
            v = lits[0].args[2]
            return [f"Value {v} must appear",
                    f"somewhere in row/col {r+1}."]

    # Generic fallback
    cell_strs = ", ".join(f"({r+1},{c+1})" for r,c in cells[:3])
    return [f"{n}-literal clause",
            f"cells: {cell_strs}" if cell_strs else "no cell refs"]

_KB_POPUP_SECTIONS = [
    ("title",   "CNF CLAUSE REFERENCE"),
    ("heading", "PREDICATES"),
    ("text",    "Val(r,c,v)      Cell (r,c) holds value v."),
    ("text",    "Given(r,c,v)    Cell (r,c) is a pre-filled clue."),
    ("text",    "LessH(r,c)      Horizontal: cell(r,c) < cell(r,c+1)."),
    ("text",    "GreaterH(r,c)   Horizontal: cell(r,c) > cell(r,c+1)."),
    ("text",    "LessV(r,c)      Vertical:   cell(r,c) < cell(r+1,c)."),
    ("text",    "GreaterV(r,c)   Vertical:   cell(r,c) > cell(r+1,c)."),
    ("text",    "Less(a,b)       Numeric ordering: a < b."),
    ("text",    "Diff(a,b)       Numeric:  a != b."),
    ("text",    "Domain(v)       Value v is in 1..N."),
    ("sep",),
    ("heading", "AXIOM GROUPS"),
    ("text",    "A1  Each cell holds at least one value."),
    ("text",    "    Val(r,c,1) | ... | Val(r,c,N)"),
    ("text",    "A2  A cell cannot hold two different values."),
    ("text",    "    ~Val(r,c,v1) | ~Val(r,c,v2)  for v1!=v2"),
    ("text",    "A3  No value repeats in a row."),
    ("text",    "    ~Val(r,c1,v) | ~Val(r,c2,v)  for c1!=c2"),
    ("text",    "A4  No value repeats in a column."),
    ("text",    "    ~Val(r1,c,v) | ~Val(r2,c,v)  for r1!=r2"),
    ("text",    "A5-A8  Inequality constraints propagate values."),
    ("text",    "    LessH(r,c) | ~Val(r,c,v) | ~Val(r,c+1,u)  for v>=u"),
    ("text",    "A9  Given clue cells are fixed."),
    ("text",    "    Val(r,c,v)  for each pre-filled cell"),
    ("text",    "A11 Numeric Less facts for all a<b."),
    ("text",    "    Less(a,b)  for each pair 1<=a<b<=N"),
    ("text",    "A12/A13  Every value appears in every row/col."),
    ("text",    "    Val(r,1,v) | ... | Val(r,N,v)"),
    ("text",    "A14/A15  Less is irreflexive and asymmetric."),
    ("text",    "    ~Less(a,a)     ~Less(a,b) | ~Less(b,a)"),
    ("text",    "A16  Inequality contrapositive (forbidden pairs)."),
    ("text",    "    ~LessH(r,c) | ~Val(r,c,v) | ~Val(r,c+1,u)  v>=u"),
    ("sep",),
    ("heading", "HOW TO USE"),
    ("text",    "Hover a fact in the panel to highlight its cells"),
    ("text",    "and constraint arrows on the grid."),
    ("text",    "Less(a,b) facts highlight ALL inequality cells"),
    ("text",    "because they support every ordering constraint."),
    ("text",    "Click [?] next to a fact to pin its explanation."),
    ("text",    "Press Esc or click X to close this popup."),
]
