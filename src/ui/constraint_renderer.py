"""
Constraint renderer: draws < > ^ v inequality symbols between adjacent cells.
"""
from __future__ import annotations

import pygame

import ui.theme as T
from models.game_state import GameState
from ui.base import BaseRenderer
from ui.layout import cell_rect, grid_geometry, h_gap_rect, v_gap_rect


class ConstraintRenderer(BaseRenderer):
    def render(self, surface: pygame.Surface, state: GameState) -> None:
        board = state.board
        if board is None:
            return

        puzzle = board.puzzle
        N = puzzle.N
        grid_rect, cell_size, gap = grid_geometry(N)
        fnt = T.font("constraint")

        # Horizontal constraints: cell(i,j) [op] cell(i,j+1)
        for constraint in puzzle.h_constraints:
            i, j = constraint.cell1
            gap_r = h_gap_rect(i, j, grid_rect, cell_size, gap)
            symbol = constraint.direction   # '<' or '>'
            self._draw_symbol(surface, fnt, symbol, gap_r)

        # Vertical constraints: cell(i,j) [op] cell(i+1,j)
        for constraint in puzzle.v_constraints:
            i, j = constraint.cell1
            gap_r = v_gap_rect(i, j, grid_rect, cell_size, gap)
            # '<' means cell(i,j) < cell(i+1,j) → top < bottom → use '^'
            symbol = "^" if constraint.direction == "<" else "v"
            self._draw_symbol(surface, fnt, symbol, gap_r)

    @staticmethod
    def _draw_symbol(surface, fnt, symbol, gap_rect):
        txt = fnt.render(symbol, True, T.CLR_TEXT_CONSTRAINT)
        trect = txt.get_rect(center=gap_rect.center)
        surface.blit(txt, trect)
