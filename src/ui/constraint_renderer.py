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
        from models.game_state import AppMode
        board = state.board
        if board is None:
            return

        puzzle = board.puzzle
        N = puzzle.N
        grid_rect, cell_size, gap = grid_geometry(N)
        fnt     = T.font("constraint")
        fnt_hl  = T.font("constraint")   # same size, different colour below

        # Determine highlight source in KB mode.
        hl_lit    = None
        hl_clause = None
        if state.mode == AppMode.KB:
            hl_clause = state.kb_hovered_clause
            if hl_clause is None:
                hl_lit = state.kb_hovered_lit or state.kb_selected_lit

        # Horizontal constraints
        for constraint in puzzle.h_constraints:
            i, j = constraint.cell1
            gap_r  = h_gap_rect(i, j, grid_rect, cell_size, gap)
            symbol = constraint.direction  # '<' or '>'
            if hl_clause is not None:
                highlighted = _clause_constraint_matches(hl_clause, "H", i, j, symbol)
            else:
                highlighted = _constraint_matches(hl_lit, "H", i, j, symbol)
            self._draw_symbol(surface, fnt, symbol, gap_r, highlighted)

        # Vertical constraints
        for constraint in puzzle.v_constraints:
            i, j = constraint.cell1
            gap_r  = v_gap_rect(i, j, grid_rect, cell_size, gap)
            symbol = "^" if constraint.direction == "<" else "v"
            if hl_clause is not None:
                highlighted = _clause_constraint_matches(hl_clause, "V", i, j,
                                                         constraint.direction)
            else:
                highlighted = _constraint_matches(hl_lit, "V", i, j,
                                                  constraint.direction)
            self._draw_symbol(surface, fnt, symbol, gap_r, highlighted)

    @staticmethod
    def _draw_symbol(surface, fnt, symbol, gap_rect, highlighted: bool = False):
        if highlighted:
            # Bright fill + contrasting text
            pygame.draw.rect(surface, T.CLR_CELL_KB_HL, gap_rect, border_radius=3)
            colour = T.CLR_KB_CONSTRAINT
        else:
            colour = T.CLR_TEXT_CONSTRAINT
        txt   = fnt.render(symbol, True, colour)
        trect = txt.get_rect(center=gap_rect.center)
        surface.blit(txt, trect)


def _constraint_matches(hl_lit, axis: str, i: int, j: int,
                        direction: str) -> bool:
    """Return True if hl_lit refers to the constraint at (axis, i, j)."""
    if hl_lit is None:
        return False
    n, args = hl_lit.name, hl_lit.args
    if axis == "H":
        if n == "LessH"    and args == (i, j) and direction == "<": return True
        if n == "GreaterH" and args == (i, j) and direction == ">": return True
    else:  # V
        if n == "LessV"    and args == (i, j) and direction == "<": return True
        if n == "GreaterV" and args == (i, j) and direction == ">": return True
    return False


def _clause_constraint_matches(clause, axis: str, i: int, j: int,
                                direction: str) -> bool:
    """Return True if a multi-literal clause is related to constraint (axis,i,j).

    A clause is considered related when it contains a LessH/GreaterH/LessV/GreaterV
    literal that names this constraint, OR when it references both cells that the
    constraint connects via Val/NotVal literals (e.g. A5-A8 and A16 clauses).
    """
    if axis == "H":
        cell_a, cell_b = (i, j), (i, j + 1)
    else:
        cell_a, cell_b = (i, j), (i + 1, j)

    has_a = has_b = False
    for lit in clause:
        n, args = lit.name, lit.args
        # Direct constraint literal
        if axis == "H":
            if n == "LessH"    and args == (i, j) and direction == "<": return True
            if n == "GreaterH" and args == (i, j) and direction == ">": return True
        else:
            if n == "LessV"    and args == (i, j) and direction == "<": return True
            if n == "GreaterV" and args == (i, j) and direction == ">": return True
        # Val/NotVal referencing one of the two constraint cells
        if n in ("Val", "NotVal", "Given"):
            cell = (args[0], args[1])
            if cell == cell_a:
                has_a = True
            elif cell == cell_b:
                has_b = True
    return has_a and has_b
