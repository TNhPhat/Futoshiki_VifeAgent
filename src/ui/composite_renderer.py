"""
Composite renderer: draws background then delegates to all sub-renderers.
"""
from __future__ import annotations

import pygame

import ui.theme as T
from models.game_state import GameState
from ui.base import BaseRenderer
from ui.constraint_renderer import ConstraintRenderer
from ui.grid_renderer import GridRenderer
from ui.hud_renderer import HudRenderer
from ui.layout import GRID_AREA_RECT


class CompositeRenderer(BaseRenderer):
    def __init__(self) -> None:
        self._grid       = GridRenderer()
        self._constraints = ConstraintRenderer()
        self._hud        = HudRenderer()

    def render(self, surface: pygame.Surface, state: GameState) -> None:
        # Clear the whole screen
        surface.fill(T.CLR_BG)

        # Fill grid area slightly differently to distinguish it
        pygame.draw.rect(surface, (252, 252, 248), GRID_AREA_RECT)

        # Renderers in draw order
        self._grid.render(surface, state)
        self._constraints.render(surface, state)
        self._hud.render(surface, state)
