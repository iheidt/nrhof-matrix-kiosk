#!/usr/bin/env python3
"""Unified UI Components Library.

This module provides a centralized interface to all UI components used throughout
the application. Components are organized by category for easy discovery.

Categories:
    - Cards: Title cards, content cards
    - Buttons: Regular buttons, toggle buttons
    - Layout: Footer, back arrow, scanlines
    - Widgets: Clock, D20, Now Playing, Marquee text

Example:
    from nrhof.ui.components import draw_button, draw_title_card, draw_footer

    # Draw a button
    rect = draw_button(screen, x=100, y=100, container_width=800,
                       text="Click Me", theme=theme)

    # Draw a title card
    content_rect = draw_title_card(screen, x=50, y=50, width=700,
                                    height=200, title="SETTINGS", theme=theme)
"""

# ============================================================================
# CARDS
# ============================================================================
# ============================================================================
# CONSTANTS AND UTILITIES
# ============================================================================
from ..colors import (
    dim_color,
)
from ..constants import (
    FOOTER_HEIGHT,
    MARGIN_BOTTOM,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
)

# ============================================================================
# BUTTONS
# ============================================================================
from .buttons import (
    draw_button,
    draw_toggle_button,
)

# ============================================================================
# WIDGETS
# ============================================================================
from .d20 import draw_d20

# ============================================================================
# LAYOUT COMPONENTS
# ============================================================================
from .layout import (
    draw_back_arrow,
    draw_footer,
    draw_hud,
    draw_scanlines,
    draw_status,
)
from .marquee import MarqueeText
from .now_playing import draw_now_playing
from .primary_card import (
    draw_card,
    draw_title_card,
    draw_title_card_container,
)
from .secondary_card import (
    draw_secondary_card,
)
from .timeclock import draw_timeclock

# ============================================================================
# PUBLIC API
# ============================================================================
__all__ = [
    # Cards
    "draw_card",
    "draw_title_card",
    "draw_title_card_container",
    # Buttons
    "draw_button",
    "draw_toggle_button",
    # Layout
    "draw_footer",
    "draw_back_arrow",
    "draw_scanlines",
    "draw_status",
    # Widgets
    "draw_timeclock",
    "draw_d20",
    "draw_now_playing",
    "MarqueeText",
    # Utilities
    "dim_color",
    "MARGIN_TOP",
    "MARGIN_LEFT",
    "MARGIN_RIGHT",
    "MARGIN_BOTTOM",
    "FOOTER_HEIGHT",
]

# ============================================================================
# VERSION INFO
# ============================================================================
__version__ = "1.0.0"
__author__ = "NRHOF Team"
