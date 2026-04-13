"""
Screen layout constants and helpers.

The window is fixed at SCREEN_W × SCREEN_H.
A top bar holds the title and mode-tab buttons.
The left area is the grid panel; the right column is the side panel.
"""
from __future__ import annotations

import pygame

# ---------------------------------------------------------------------------
# Window dimensions
# ---------------------------------------------------------------------------

SCREEN_W: int = 900
SCREEN_H: int = 680

# ---------------------------------------------------------------------------
# Title / tab bar
# ---------------------------------------------------------------------------

TITLE_BAR_H: int = 50

TITLE_BAR_RECT = pygame.Rect(0, 0, SCREEN_W, TITLE_BAR_H)

# Mode-tab buttons (Play / Solve / Menu) — positioned in the title bar
TAB_W:  int = 80
TAB_H:  int = 32
TAB_Y:  int = (TITLE_BAR_H - TAB_H) // 2

TAB_PLAY_RECT  = pygame.Rect(SCREEN_W - 3 * (TAB_W + 6) - 10, TAB_Y, TAB_W, TAB_H)
TAB_SOLVE_RECT = pygame.Rect(SCREEN_W - 2 * (TAB_W + 6) - 10, TAB_Y, TAB_W, TAB_H)
TAB_MENU_RECT  = pygame.Rect(SCREEN_W - 1 * (TAB_W + 6) - 10, TAB_Y, TAB_W, TAB_H)

# ---------------------------------------------------------------------------
# Main areas
# ---------------------------------------------------------------------------

SIDE_PANEL_W: int = 260
SIDE_PANEL_PADDING: int = 10

GRID_AREA_RECT = pygame.Rect(
    0,
    TITLE_BAR_H,
    SCREEN_W - SIDE_PANEL_W,
    SCREEN_H - TITLE_BAR_H,
)

SIDE_PANEL_RECT = pygame.Rect(
    SCREEN_W - SIDE_PANEL_W,
    TITLE_BAR_H,
    SIDE_PANEL_W,
    SCREEN_H - TITLE_BAR_H,
)

# ---------------------------------------------------------------------------
# Side-panel sub-sections  (solver / puzzle / play)
# The panel is divided into three stacked sections.
# Heights are approximate; HudRenderer clips as needed.
# ---------------------------------------------------------------------------

_px = SIDE_PANEL_RECT.x
_py = SIDE_PANEL_RECT.y
_pw = SIDE_PANEL_W

SOLVER_PANEL_RECT = pygame.Rect(_px, _py,           _pw, 185)
PUZZLE_PANEL_RECT = pygame.Rect(_px, _py + 185,     _pw, 265)
PLAY_PANEL_RECT   = pygame.Rect(_px, _py + 185+265, _pw, SCREEN_H - TITLE_BAR_H - 185 - 265)

# ---------------------------------------------------------------------------
# Grid geometry helpers
# ---------------------------------------------------------------------------

# Gaps between cells (for constraint symbols)
CONSTRAINT_GAP: int = 18   # pixels reserved between adjacent cells for symbols

# Outer padding inside GRID_AREA_RECT
GRID_PADDING: int = 30


def grid_geometry(N: int) -> tuple[pygame.Rect, int, int]:
    """
    Compute the grid rect, cell size, and gap size for an N×N puzzle.

    Returns
    -------
    grid_rect : pygame.Rect
        Bounding rect of the entire grid (cells + gaps), centred in GRID_AREA_RECT.
    cell_size : int
        Pixel size of each cell (square).
    gap : int
        Pixel gap between adjacent cells (for constraint symbols).
    """
    gap = CONSTRAINT_GAP
    available_w = GRID_AREA_RECT.width  - 2 * GRID_PADDING
    available_h = GRID_AREA_RECT.height - 2 * GRID_PADDING

    # total width = N * cell_size + (N-1) * gap
    cell_size_from_w = (available_w - (N - 1) * gap) // N
    cell_size_from_h = (available_h - (N - 1) * gap) // N
    cell_size = max(20, min(cell_size_from_w, cell_size_from_h))

    total_w = N * cell_size + (N - 1) * gap
    total_h = N * cell_size + (N - 1) * gap

    # Centre in GRID_AREA_RECT
    ox = GRID_AREA_RECT.x + (GRID_AREA_RECT.width  - total_w) // 2
    oy = GRID_AREA_RECT.y + (GRID_AREA_RECT.height - total_h) // 2

    grid_rect = pygame.Rect(ox, oy, total_w, total_h)
    return grid_rect, cell_size, gap


def cell_rect(i: int, j: int, grid_rect: pygame.Rect, cell_size: int, gap: int) -> pygame.Rect:
    """
    Return the pixel rect for cell (i, j) given the pre-computed geometry.
    """
    x = grid_rect.x + j * (cell_size + gap)
    y = grid_rect.y + i * (cell_size + gap)
    return pygame.Rect(x, y, cell_size, cell_size)


def h_gap_rect(i: int, j: int, grid_rect: pygame.Rect, cell_size: int, gap: int) -> pygame.Rect:
    """Rect of the horizontal gap between cell (i,j) and (i,j+1)."""
    x = grid_rect.x + j * (cell_size + gap) + cell_size
    y = grid_rect.y + i * (cell_size + gap)
    return pygame.Rect(x, y, gap, cell_size)


def v_gap_rect(i: int, j: int, grid_rect: pygame.Rect, cell_size: int, gap: int) -> pygame.Rect:
    """Rect of the vertical gap between cell (i,j) and (i+1,j)."""
    x = grid_rect.x + j * (cell_size + gap)
    y = grid_rect.y + i * (cell_size + gap) + cell_size
    return pygame.Rect(x, y, cell_size, gap)
