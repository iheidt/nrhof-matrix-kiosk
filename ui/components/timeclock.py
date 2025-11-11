#!/usr/bin/env python3
"""Timeclock widget component."""

from datetime import datetime
from pathlib import Path

import pygame
from pygame import Surface

from ..components.primary_card import draw_card

# Font cache for timeclock
_font_cache = {}
_FONT_CACHE_MAX_SIZE = 20


def evict_timeclock_font_cache():
    """Clear the timeclock font cache."""
    global _font_cache
    _font_cache.clear()


def draw_timeclock(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    theme: dict = None,
) -> pygame.Rect:
    """Draw timeclock component with card border and live time/date.

    Args:
        surface: Surface to draw on
        x: X position
        y: Y position
        width: Card width
        height: Card height
        theme: Theme dict with style

    Returns:
        Rect of the component
    """
    if theme is None:
        theme = {}
    style = theme.get("style", {})
    layout = theme.get("layout", {})

    # Get colors
    primary_color = tuple(style.get("colors", {}).get("primary", (255, 20, 147)))
    dim_color_hex = style["colors"].get("dim", "#2C405B")
    if isinstance(dim_color_hex, str) and dim_color_hex.startswith("#"):
        dim_color = tuple(int(dim_color_hex[i : i + 2], 16) for i in (1, 3, 5))
    else:
        dim_color = (
            tuple(dim_color_hex) if isinstance(dim_color_hex, list | tuple) else (44, 64, 91)
        )

    # Get timeclock settings from layout
    timeclock_settings = layout.get("timeclock", {})
    border_fade_pct = timeclock_settings.get("border_fade_pct", 0.9)
    border_height_pct = timeclock_settings.get("border_height_pct", 1.0)

    # Draw card border with fade (top solid, bottom/sides fade)
    draw_card(
        surface,
        x,
        y,
        width,
        height,
        theme=theme,
        border_solid="top",
        border_fade_pct=border_fade_pct,
        border_height_pct=border_height_pct,
    )

    # Get current time and date
    now = datetime.now()

    # Format time
    from core.localization import t
    from ui.fonts import get_localized_font

    # Get localized AM/PM
    hour = now.hour
    if hour < 12:
        ampm = t("common.am")
    else:
        ampm = t("common.pm")

    time_str = now.strftime("%I:%M")  # 05:30 (with leading zero)

    # Load fonts with localization support
    # AM/PM: Miland 30px (maps to Dela Gothic One for Japanese)
    ampm_font = get_localized_font(30, "secondary", ampm)

    # Time: IBM Plex Semibold Italic 124px (display size) - cached
    time_cache_key = "timeclock_time_124"
    if time_cache_key not in _font_cache:
        # Evict oldest entry if cache is full
        if len(_font_cache) >= _FONT_CACHE_MAX_SIZE:
            _font_cache.pop(next(iter(_font_cache)))
        time_font_path = (
            Path(__file__).parent.parent.parent
            / "assets"
            / "fonts"
            / "IBMPlexMono-SemiBoldItalic.ttf"
        )
        _font_cache[time_cache_key] = pygame.font.Font(str(time_font_path), 124)
    time_font = _font_cache[time_cache_key]

    # Render text
    ampm_surface = ampm_font.render(ampm, True, dim_color)
    time_surface = time_font.render(time_str, True, primary_color)

    # Layout with 24px top padding
    padding = 24

    # AM/PM right-justified with padding
    ampm_x = x + width - padding - ampm_surface.get_width()
    ampm_y = y + padding
    surface.blit(ampm_surface, (ampm_x, ampm_y))

    # Time centered horizontally, 10px below AM/PM, moved up 48px
    time_x = x + (width - time_surface.get_width()) // 2
    time_y = ampm_y + ampm_surface.get_height() - 25
    surface.blit(time_surface, (time_x, time_y))

    return pygame.Rect(x, y, width, height)
