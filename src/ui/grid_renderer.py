"""
Grid renderer: draws the NxN cell grid with values, notes, and highlights.
"""
from __future__ import annotations

import math
import pygame

import ui.theme as T
from models.game_state import AppMode, GameState
from ui.base import BaseRenderer
from ui.layout import GRID_AREA_RECT, cell_rect, grid_geometry


class GridRenderer(BaseRenderer):
    def render(self, surface: pygame.Surface, state: GameState) -> None:
        board = state.board
        if board is None:
            return

        N = board.puzzle.N
        grid_rect, cell_size, gap = grid_geometry(N)

        # Determine which grid to display.
        if state.mode == AppMode.SOLVE and state.current_display_grid is not None:
            display_grid = state.current_display_grid
        else:
            display_grid = board.grid

        for i in range(N):
            for j in range(N):
                rect = cell_rect(i, j, grid_rect, cell_size, gap)
                # Apply shake offset for invalid note attempts.
                t = state.shake_timers.get((i, j), 0.0)
                if t > 0:
                    elapsed = 0.4 - t
                    shake_x = int(math.sin(elapsed * 45) * 6 * (t / 0.4))
                    rect = rect.move(shake_x, 0)
                self._draw_cell(
                    surface, state, board, display_grid,
                    i, j, rect, cell_size, N,
                )

        # Draw outer grid border
        pygame.draw.rect(surface, T.CLR_GRID_LINE, grid_rect, 2)

        # KB mode: highlight cells referenced by the hovered / selected fact or clause
        if state.mode == AppMode.KB:
            if state.kb_hovered_clause is not None:
                highlight_cells = _clause_cells(state.kb_hovered_clause)
            else:
                lit = state.kb_hovered_lit or state.kb_selected_lit
                highlight_cells = _lit_cells_for_puzzle(lit, board.puzzle)
            for (hi, hj) in highlight_cells:
                hrect = cell_rect(hi, hj, grid_rect, cell_size, gap)
                hl = pygame.Surface((hrect.width, hrect.height), pygame.SRCALPHA)
                hl.fill((*T.CLR_CELL_KB_HL, 160))
                surface.blit(hl, hrect.topleft)
                pygame.draw.rect(surface, T.CLR_KB_CONSTRAINT, hrect, 3)

        # Notification overlay
        self._draw_notification(surface, state, grid_rect)

        # KB mode: domain tooltip for hovered cell
        if state.mode == AppMode.KB and state.kb_hovered_cell is not None:
            self._draw_domain_tooltip(surface, state, board, grid_rect, cell_size, gap)

    # ------------------------------------------------------------------
    # Single cell
    # ------------------------------------------------------------------

    def _draw_cell(
        self, surface, state, board, display_grid,
        i, j, rect, cell_size, N,
    ):
        value     = int(display_grid[i, j])
        is_given  = board.puzzle.is_given(i, j)
        is_sel    = (board.selected == (i, j)) and state.mode != AppMode.SOLVE
        is_error  = (i, j) in board.errors and state.mode == AppMode.PLAY
        is_solved = state.solve_succeeded and value != 0
        is_solver_cell = (i, j) in state.solver_cells and state.mode == AppMode.SOLVE
        is_backtrack   = (i, j) in state.backtrack_timers

        # Background colour
        if is_given:
            bg = T.CLR_CELL_GIVEN
        elif is_error:
            bg = T.CLR_CELL_ERROR
        elif is_backtrack:
            # Blend orange with white based on remaining timer
            t = state.backtrack_timers[(i, j)]  # 0..0.5
            alpha = min(1.0, t / 0.5)
            bg = _blend(T.CLR_CELL_BACKTRACK, T.CLR_CELL_DEFAULT, alpha)
        elif is_solved:
            bg = T.CLR_CELL_SOLVED
        elif is_solver_cell:
            bg = T.CLR_CELL_SOLVER
        elif is_sel:
            bg = T.CLR_CELL_SELECTED
        else:
            bg = T.CLR_CELL_DEFAULT

        pygame.draw.rect(surface, bg, rect)
        pygame.draw.rect(surface, T.CLR_CELL_LINE, rect, 1)

        if value != 0:
            self._draw_value(surface, value, is_given, is_error, is_solver_cell, rect, N)
        elif state.mode == AppMode.PLAY:
            notes = board.notes.get((i, j), set())
            if notes:
                self._draw_notes(surface, notes, rect, cell_size, N)

    def _draw_value(self, surface, value, is_given, is_error, is_solver, rect, N):
        fnt = T.cell_font(N)
        if is_error:
            colour = T.CLR_TEXT_ERROR
        elif is_given:
            colour = T.CLR_TEXT_GIVEN
        elif is_solver:
            colour = T.CLR_TEXT_SOLVER
        else:
            colour = T.CLR_TEXT_USER

        txt = fnt.render(str(value), True, colour)
        trect = txt.get_rect(center=rect.center)
        surface.blit(txt, trect)

    def _draw_notes(self, surface, notes, rect, cell_size, N):
        fnt = T.note_font(N)
        # Layout pencil marks in a sub-grid
        cols = max(3, N // 2 + 1)
        rows = (N + cols - 1) // cols
        cell_w = rect.width  // cols
        cell_h = rect.height // rows

        for v in sorted(notes):
            idx = v - 1
            nc = idx % cols
            nr = idx // cols
            cx = rect.x + nc * cell_w + cell_w // 2
            cy = rect.y + nr * cell_h + cell_h // 2
            txt = fnt.render(str(v), True, T.CLR_TEXT_NOTE)
            trect = txt.get_rect(center=(cx, cy))
            surface.blit(txt, trect)

    # ------------------------------------------------------------------
    # KB domain tooltip
    # ------------------------------------------------------------------

    def _draw_domain_tooltip(self, surface, state, board, grid_rect, cell_size, gap):
        i, j = state.kb_hovered_cell
        N = board.puzzle.N
        grid = board.grid

        cell_val = int(grid[i, j])
        if cell_val != 0:
            lines = [f"Cell ({i+1},{j+1})", f"Fixed: {cell_val}"]
        else:
            used = set()
            for c in range(N):
                v = int(grid[i, c])
                if v:
                    used.add(v)
            for r in range(N):
                v = int(grid[r, j])
                if v:
                    used.add(v)
            domain = sorted(set(range(1, N + 1)) - used)
            domain_str = "{" + ",".join(str(v) for v in domain) + "}" if domain else "\u2205"
            lines = [f"Cell ({i+1},{j+1})", f"Domain: {domain_str}"]

        fnt = T.font("hud_label")
        pad = 6
        line_h = fnt.size("A")[1] + 2
        w = max(fnt.size(l)[0] for l in lines) + pad * 2
        h = len(lines) * line_h + pad * 2

        # Position tooltip below-right of the cell, clamp inside grid area
        crect = cell_rect(i, j, grid_rect, cell_size, gap)
        tx = crect.right + 4
        ty = crect.top
        if tx + w > GRID_AREA_RECT.right - 4:
            tx = crect.left - w - 4
        if ty + h > GRID_AREA_RECT.bottom - 4:
            ty = GRID_AREA_RECT.bottom - h - 4

        tip = pygame.Rect(tx, ty, w, h)
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((40, 40, 40, 220))
        surface.blit(bg, tip.topleft)
        pygame.draw.rect(surface, (180, 180, 180), tip, 1)

        for k, line in enumerate(lines):
            colour = (255, 220, 80) if k == 0 else (240, 240, 240)
            txt = fnt.render(line, True, colour)
            surface.blit(txt, (tip.x + pad, tip.y + pad + k * line_h))

    # ------------------------------------------------------------------
    # Notification
    # ------------------------------------------------------------------

    def _draw_notification(self, surface, state, grid_rect):
        if not state.notification or state.notification_timer <= 0:
            return

        fnt = T.font("hud_value")
        txt = fnt.render(state.notification, True, (255, 255, 255))
        w, h = txt.get_size()
        pad = 10
        bg_rect = pygame.Rect(
            grid_rect.centerx - w // 2 - pad,
            grid_rect.centery - h // 2 - pad,
            w + pad * 2,
            h + pad * 2,
        )
        s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        s.fill((40, 40, 40, 200))
        surface.blit(s, bg_rect.topleft)
        surface.blit(txt, (bg_rect.x + pad, bg_rect.y + pad))


# ---------------------------------------------------------------------------
# KB literal -> cell helper
# ---------------------------------------------------------------------------

def _lit_cells_for_puzzle(lit, puzzle) -> list[tuple[int, int]]:
    """Return the grid cells (row, col) to highlight for a CNF literal."""
    if lit is None:
        return []
    n, args = lit.name, lit.args
    if n in ("Val", "NotVal", "Given", "ValidVal"):
        return [(args[0], args[1])]
    if n in ("LessH", "GreaterH"):
        r, c = args[0], args[1]
        return [(r, c), (r, c + 1)]
    if n in ("LessV", "GreaterV"):
        r, c = args[0], args[1]
        return [(r, c), (r + 1, c)]
    return []


def _clause_cells(clause) -> list[tuple[int, int]]:
    """Return deduplicated grid cells referenced by any literal in a clause."""
    seen: set[tuple[int, int]] = set()
    cells: list[tuple[int, int]] = []
    for lit in clause:
        n, args = lit.name, lit.args
        if n in ("Val", "NotVal", "Given", "ValidVal"):
            cell = (args[0], args[1])
        elif n in ("LessH", "GreaterH"):
            for cell in ((args[0], args[1]), (args[0], args[1] + 1)):
                if cell not in seen:
                    seen.add(cell); cells.append(cell)
            continue
        elif n in ("LessV", "GreaterV"):
            for cell in ((args[0], args[1]), (args[0] + 1, args[1])):
                if cell not in seen:
                    seen.add(cell); cells.append(cell)
            continue
        else:
            continue
        if cell not in seen:
            seen.add(cell); cells.append(cell)
    return cells


# ---------------------------------------------------------------------------
# Colour blending helper
# ---------------------------------------------------------------------------

def _blend(c1, c2, t: float):
    """Linearly interpolate between c1 (t=1) and c2 (t=0)."""
    return tuple(int(a * t + b * (1 - t)) for a, b in zip(c1, c2))
