"""
Visual theme: colours, fonts, and sizing constants for the Futoshiki UI.
All values are module-level constants so renderers can import them directly.
"""
from __future__ import annotations

import pygame

# ---------------------------------------------------------------------------
# Colours  (R, G, B)
# ---------------------------------------------------------------------------

CLR_BG            = (245, 245, 240)   # app background
CLR_PANEL_BG      = (230, 230, 225)   # side-panel background
CLR_PANEL_BORDER  = (180, 180, 175)   # panel border / divider
CLR_GRID_LINE     = (100, 100, 100)   # thick grid outer border
CLR_CELL_LINE     = (180, 180, 180)   # thin inner cell borders

# Cell fills
CLR_CELL_DEFAULT  = (255, 255, 255)   # empty user cell
CLR_CELL_GIVEN    = (210, 210, 205)   # pre-filled clue cell
CLR_CELL_SELECTED = (180, 210, 255)   # currently selected cell
CLR_CELL_ERROR    = (255, 180, 180)   # conflict / error
CLR_CELL_SOLVER   = (180, 220, 255)   # cell filled by solver
CLR_CELL_BACKTRACK= (255, 200, 130)   # backtrack flash (fades out)
CLR_CELL_SOLVED   = (180, 255, 190)   # final solved state

# Text
CLR_TEXT_GIVEN    = (30,  30,  30)    # given-clue numeral (bold)
CLR_TEXT_USER     = (40,  80, 180)    # user-entered numeral
CLR_TEXT_SOLVER   = (20, 100, 200)    # solver-placed numeral
CLR_TEXT_ERROR    = (200,  30,  30)   # numeral in error cell
CLR_TEXT_NOTE     = (100, 100, 100)   # pencil-mark digit
CLR_TEXT_CONSTRAINT = (60, 60, 60)    # < > ^ v symbols

# HUD
CLR_BTN_NORMAL    = (200, 200, 195)
CLR_BTN_HOVER     = (170, 190, 230)
CLR_BTN_ACTIVE    = (130, 170, 230)
CLR_BTN_DISABLED  = (215, 215, 215)
CLR_BTN_TEXT      = (30,  30,  30)
CLR_BTN_TEXT_DIS  = (160, 160, 160)
CLR_LABEL         = (60,  60,  60)
CLR_LABEL_TITLE   = (30,  30,  30)
CLR_SLIDER_TRACK  = (180, 180, 175)
CLR_SLIDER_THUMB  = (100, 140, 220)
CLR_TAB_ACTIVE    = (100, 140, 220)
CLR_TAB_INACTIVE  = (200, 200, 195)
CLR_TAB_TEXT      = (255, 255, 255)
CLR_TAB_TEXT_INACT= (60,  60,  60)

# ---------------------------------------------------------------------------
# Font helpers  (lazy-initialised so pygame.init() need not be called at
# import time; call init_fonts() once after pygame.init())
# ---------------------------------------------------------------------------

_fonts: dict[str, pygame.font.Font] = {}


def init_fonts() -> None:
    """Initialise all fonts.  Must be called after ``pygame.init()``."""
    _fonts["title"]       = pygame.font.SysFont("segoeui",  24, bold=True)
    _fonts["cell_large"]  = pygame.font.SysFont("segoeui",  32, bold=True)
    _fonts["cell_medium"] = pygame.font.SysFont("segoeui",  24, bold=True)
    _fonts["cell_small"]  = pygame.font.SysFont("segoeui",  18, bold=False)
    _fonts["note_large"]  = pygame.font.SysFont("segoeui",  11)
    _fonts["note_small"]  = pygame.font.SysFont("segoeui",   9)
    _fonts["constraint"]  = pygame.font.SysFont("segoeui",  14, bold=True)
    _fonts["hud_label"]   = pygame.font.SysFont("segoeui",  13)
    _fonts["hud_value"]   = pygame.font.SysFont("segoeui",  13, bold=True)
    _fonts["btn"]         = pygame.font.SysFont("segoeui",  13)
    _fonts["btn_large"]   = pygame.font.SysFont("segoeui",  16)
    _fonts["tab"]         = pygame.font.SysFont("segoeui",  14, bold=True)


def font(name: str) -> pygame.font.Font:
    """Return a pre-initialised font by name."""
    return _fonts[name]


def cell_font(N: int) -> pygame.font.Font:
    """Return the best cell font for a grid of size N."""
    if N <= 5:
        return _fonts["cell_large"]
    if N <= 7:
        return _fonts["cell_medium"]
    return _fonts["cell_small"]


def note_font(N: int) -> pygame.font.Font:
    if N <= 6:
        return _fonts["note_large"]
    return _fonts["note_small"]
