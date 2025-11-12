#!/usr/bin/env python3
"""Now Playing widget component."""

from pathlib import Path

import pygame
from pygame import Surface

from ..icons import load_icon
from .marquee import MarqueeText

# Font cache for now_playing
_font_cache = {}
_FONT_CACHE_MAX_SIZE = 20


def evict_now_playing_font_cache():
    """Clear the now_playing font cache."""
    global _font_cache
    _font_cache.clear()


def draw_now_playing(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    title: str = "NOW PLAYING",
    line1: str = "",
    line2: str = "",
    theme: dict = None,
    border_y: int = None,
    marquee: MarqueeText = None,
    progress_ms: int = None,
    duration_ms: int = None,
    is_playing: bool = False,
    fade_amount: float = 0.0,
) -> pygame.Rect:
    """Draw a 'Now Playing' component with title, border, and two body lines.

    Args:
        surface: Pygame surface to draw on
        x, y: Component position (top-left)
        width: Component width
        title: Title text (default: "NOW PLAYING")
        line1: First body line (song/artist)
        line2: Second body line (rank info)
        theme: Dict with 'layout' and 'style' keys
        border_y: Optional override for border Y position
        marquee: Optional MarqueeText instance for line1 scrolling
        progress_ms: Current playback position in milliseconds
        duration_ms: Total track duration in milliseconds
        is_playing: Whether track is currently playing
        fade_amount: Border fade amount (0.0 = primary, 1.0 = dim)

    Returns:
        pygame.Rect of the entire component
    """
    from nrhof.core.theme_loader import get_theme_loader

    # Load theme if not provided
    if theme is None:
        theme_loader = get_theme_loader()
        style = theme_loader.load_style("pipboy")
    else:
        style = theme.get("style", theme)

    # Colors
    primary_color = tuple(style["colors"].get("primary", (233, 30, 99)))
    dim_color = tuple(style["colors"].get("dim", (100, 100, 100)))  # Dim/muted color
    title_color = primary_color
    bg_color_hex = "#1797CD"
    # Convert hex to RGB with 33% alpha
    bg_r = int(bg_color_hex[1:3], 16)
    bg_g = int(bg_color_hex[3:5], 16)
    bg_b = int(bg_color_hex[5:7], 16)
    bg_alpha = int(255 * 0.33)

    # Border
    border_width = 6

    # Calculate progress percentage
    progress_pct = 0.0
    if is_playing and progress_ms is not None and duration_ms and duration_ms > 0:
        progress_pct = min(1.0, progress_ms / duration_ms)

    # Animate border color fade (primary -> dim when playing)
    # Interpolate between primary and dim based on fade_amount
    if fade_amount > 0:
        # Linear interpolation between colors
        border_color = tuple(
            int(primary_color[i] + (dim_color[i] - primary_color[i]) * fade_amount)
            for i in range(3)
        )
    else:
        border_color = primary_color

    # Fonts - cached to prevent loading every frame
    # Title: Compadre Extended (label_font), label size (16)
    title_font_size = style["typography"]["fonts"].get("label", 16)
    title_cache_key = f"now_playing_title_{title_font_size}"
    if title_cache_key not in _font_cache:
        # Evict oldest entry if cache is full
        if len(_font_cache) >= _FONT_CACHE_MAX_SIZE:
            _font_cache.pop(next(iter(_font_cache)))
        # Go up from nrhof/ui/components/now_playing.py to project root
        title_font_path = (
            Path(__file__).parent.parent.parent.parent
            / "assets"
            / "fonts"
            / "Compadre-Extended.otf"
        )
        _font_cache[title_cache_key] = pygame.font.Font(str(title_font_path), title_font_size)
    title_font = _font_cache[title_cache_key]

    # Line 1: IBM Plex Mono Italic, body size (48)
    line1_font_size = style["typography"]["fonts"].get("body", 48)
    line1_cache_key = f"now_playing_line1_{line1_font_size}"
    if line1_cache_key not in _font_cache:
        # Evict oldest entry if cache is full
        if len(_font_cache) >= _FONT_CACHE_MAX_SIZE:
            _font_cache.pop(next(iter(_font_cache)))
        line1_font_path = (
            Path(__file__).parent.parent.parent.parent
            / "assets"
            / "fonts"
            / "IBMPlexMono-Italic.ttf"
        )
        _font_cache[line1_cache_key] = pygame.font.Font(str(line1_font_path), line1_font_size)
    line1_font = _font_cache[line1_cache_key]

    # Render title
    title_surface = title_font.render(title, True, title_color)
    title_height = title_surface.get_height()

    # Calculate component dimensions
    padding = 24  # Internal padding

    # If border_y parameter is provided, use it directly and calculate title_y backwards
    if border_y is not None:
        calculated_border_y = border_y
        title_y = border_y - title_height - 6  # 6px gap between title and border
    else:
        title_y = y
        calculated_border_y = title_y + title_height + 6  # 6px gap between title and border

    content_y = calculated_border_y + border_width  # Content starts immediately after border

    # Calculate background width (40px narrower from right)
    bg_width = width - 40
    max_text_width = bg_width - (padding * 2)

    # Render line1 (with marquee support)
    line1_surface = None
    line1_offset = 0
    draw_second_copy = False

    if line1:
        # Render full text with localization support
        from nrhof.ui.fonts import render_localized_text

        # Use render_localized_text with automatic font detection
        # English chars use IBM Plex Mono Italic, Japanese chars use Noto Sans JP
        line1_surface = render_localized_text(
            line1,
            line1_font_size,
            "primary",
            title_color,
        )
        line1_width = line1_surface.get_width()

        # Use marquee if text is too wide and marquee is provided
        if marquee and line1_width > max_text_width:
            # Update marquee text if changed
            if marquee.text != line1:
                marquee.reset(line1)
            line1_offset, draw_second_copy = marquee.update(line1_width)
            line1_offset = -line1_offset  # Negative for left scroll
        elif line1_width > max_text_width:
            # No marquee provided, truncate with ellipsis
            truncated = line1
            while (
                truncated
                and render_localized_text(
                    truncated + "...",
                    line1_font_size,
                    "primary",
                    title_color,
                    english_font=line1_font,
                ).get_width()
                > max_text_width
            ):
                truncated = truncated[:-1]
            line1_surface = render_localized_text(
                truncated + "...",
                line1_font_size,
                "primary",
                title_color,
                english_font=line1_font,
            )

    # Fixed content height (set to match Japanese text height for consistency)
    # This prevents the container from resizing when switching between English and Japanese
    top_padding = 5
    bottom_padding = 22
    # Use fixed height based on maximum text height (Japanese characters)
    # This ensures the box doesn't shift in size during state transitions
    content_height = (
        top_padding + 58 + bottom_padding
    )  # 5 + 58 (max Japanese text height) + 13 = 76

    # Total component height
    total_height = (calculated_border_y - title_y) + border_width + content_height

    # Draw background box (with alpha) - 40px narrower from right
    bg_surface = pygame.Surface((bg_width, content_height), pygame.SRCALPHA)
    bg_surface.fill((bg_r, bg_g, bg_b, bg_alpha))
    surface.blit(bg_surface, (x, content_y))

    # Draw border (secondary color when playing)
    pygame.draw.rect(surface, border_color, (x, calculated_border_y, width, border_width), 0)

    # Draw progress bar overlay (primary color) if playing
    if is_playing:
        # Calculate progress width (stop before circle starts)
        circle_size = 80
        circle_left_edge = x + width - circle_size  # Where circle actually starts
        max_progress_width = circle_left_edge - x
        progress_width = int(max_progress_width * progress_pct)

        # Draw primary progress bar on top of dim border
        if progress_width > 0:
            pygame.draw.rect(
                surface,
                primary_color,
                (x, calculated_border_y, progress_width, border_width),
                0,
            )

    # Draw title
    surface.blit(title_surface, (x, title_y))

    # Draw body lines with explicit top padding
    text_x = x + padding
    if line1_surface:
        # Use explicit top padding (20px)
        text_y = content_y + top_padding
    else:
        text_y = content_y + top_padding

    if line1_surface:
        # Create a clipping rect for marquee scrolling
        clip_rect = pygame.Rect(text_x, text_y, max_text_width, line1_surface.get_height())
        surface.set_clip(clip_rect)

        # Draw first copy
        surface.blit(line1_surface, (text_x + line1_offset, text_y))

        # Draw second copy for seamless loop if needed
        if draw_second_copy and marquee:
            second_x = text_x + line1_offset + line1_surface.get_width() + marquee.gap
            surface.blit(line1_surface, (second_x, text_y))

        surface.set_clip(None)  # Reset clipping

    # Draw circle element (80x80px) aligned with border
    circle_size = 80
    circle_border = 6
    circle_x = x + width - (circle_size // 2)  # Right edge, half overlapping
    circle_y = (
        calculated_border_y - (circle_size // 2) + (border_width // 2) + 40
    )  # Centered on border, moved down 40px

    # Draw outer circle (border) - use same color as top border
    pygame.draw.circle(surface, border_color, (circle_x, circle_y), circle_size // 2, 0)

    # Draw inner circle (background fill)
    bg_color_solid = tuple(style["colors"].get("background", (0, 0, 0)))
    inner_radius = (circle_size // 2) - circle_border
    pygame.draw.circle(surface, bg_color_solid, (circle_x, circle_y), inner_radius, 0)

    # Load and draw SVG icon (40x40px)
    icon_path = (
        Path(__file__).parent.parent.parent.parent / "assets" / "icons" / "icon_happysad.svg"
    )
    if icon_path.exists():
        icon_surface = load_icon(icon_path, (40, 40), fill_color=title_color)
        if icon_surface:
            icon_x = circle_x - 20  # Center 40px icon
            icon_y = circle_y - 20
            surface.blit(icon_surface, (icon_x, icon_y))
        else:
            print(f"Warning: Failed to load icon from {icon_path}")
    else:
        print(f"Warning: Icon not found at {icon_path}")

    return pygame.Rect(x, y, width, total_height)
