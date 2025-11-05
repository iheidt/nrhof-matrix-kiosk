#!/usr/bin/env python3
import subprocess
from pathlib import Path

import pygame
from pygame import Surface

ROOT = Path(__file__).resolve().parent

# Screen margin constants - loaded from _base.yaml at module import
def _load_margins_from_yaml():
    """Load margins from _base.yaml."""
    try:
        from theme_loader import get_theme_loader
        theme_loader = get_theme_loader()
        base_layout = theme_loader.load_layout('_base')
        margins = base_layout.get('margins', {})
        footer = base_layout.get('footer', {})
        return {
            'top': margins.get('top', 50),
            'left': margins.get('left', 50),
            'right': margins.get('right', 50),
            'bottom': margins.get('bottom', 130),
            'footer_height': footer.get('height', 130)
        }
    except Exception:
        # Fallback to defaults if YAML can't be loaded
        return {
            'top': 50,
            'left': 50,
            'right': 50,
            'bottom': 130,
            'footer_height': 130
        }

_margins = _load_margins_from_yaml()
MARGIN_TOP = _margins['top']
MARGIN_LEFT = _margins['left']
MARGIN_RIGHT = _margins['right']
MARGIN_BOTTOM = _margins['bottom']
FOOTER_HEIGHT = _margins['footer_height']

# Hub scene layout constants
HUB_TITLE_Y_OFFSET = 60      # Title position from top margin
HUB_SUBTITLE_Y_OFFSET = 120  # Subtitle position from top margin
HUB_MENU_START_Y_OFFSET = 180  # Menu items start position from top margin
HUB_MENU_LINE_HEIGHT = 50    # Spacing between menu items


# get_matrix_green() removed - use theme_loader.load_style() instead


def dim_color(color: tuple, factor: float = 0.5) -> tuple:
    """Dim a color by a given factor.
    
    Args:
        color: RGB color tuple
        factor: Dimming factor (0.0 = black, 1.0 = original)
        
    Returns:
        Dimmed RGB color tuple
    """
    return tuple(int(c * factor) for c in color)


def draw_scanlines(surface: Surface, strength: float = 0.15):
    w, h = surface.get_size()
    scan = pygame.Surface((w, h), pygame.SRCALPHA)
    dark = int(255 * strength)
    for y in range(0, h, 2):
        pygame.draw.line(scan, (0, 0, 0, dark), (0, y), (w, y))
    surface.blit(scan, (0, 0), special_flags=pygame.BLEND_SUB)


# ============================================================================
# UI DRAWING COMPONENTS (moved to ui/drawing.py)
# ============================================================================

# Backward-compatible imports
from ui.drawing import (
    draw_back_arrow,
    draw_card,
    draw_button,
    draw_footer,
    draw_title_card,
    draw_now_playing,
    draw_timeclock,
    draw_d20
)

# Icon loading (moved to ui/icons.py)
from ui.icons import load_icon

# ============================================================================
# SYSTEM UTILITIES
# ============================================================================

def launch_command(cmd: str):
    try:
        # Use shell so simple strings work; you can switch to list if needed
        subprocess.Popen(cmd, shell=True)
    except Exception as e:
        print(f"Failed to launch '{cmd}': {e}")


# ============================================================================
# FONT MANAGEMENT (moved to ui/fonts.py)
# ============================================================================

# Backward-compatible imports
from ui.fonts import (
    init_custom_fonts,
    get_font,
    get_theme_font,
    render_text
)
