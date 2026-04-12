"""Base renderer interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pygame

from models.game_state import GameState


class BaseRenderer(ABC):
    @abstractmethod
    def render(self, surface: pygame.Surface, state: GameState) -> None:
        """Draw this renderer's elements onto *surface*."""
