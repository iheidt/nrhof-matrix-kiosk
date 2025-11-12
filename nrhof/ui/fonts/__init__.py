#!/usr/bin/env python3
"""
Font loading and management utilities.

This module provides a unified interface for font loading, caching, and rendering
with support for:
- Custom TTF/OTF fonts from assets/fonts/
- System font fallbacks (cross-platform)
- Japanese/English mixed-font rendering
- LRU caching for performance
- Localization-aware font selection

Architecture:
    The font system has been refactored into modular components:
    - font_loader.py: Font loading and caching
    - localization.py: Localization-aware font selection
    - ui/text_renderer.py: Mixed-font text rendering strategies

Public API:
    - init_custom_fonts(config): Initialize font system
    - get_font(size, mono, prefer, bold): Get cached font
    - get_theme_font(size, font_type): Get font from theme
    - get_localized_font(size, font_type, text): Get language-appropriate font
    - render_mixed_text(text, size, font_type, color): Render with mixed fonts
    - render_localized_text(text, size, font_type, color, english_font): Convenience wrapper
    - render_text(text, size, mono, color, antialias, prefer): Simple text rendering
    - clear_render_cache(): Clear text rendering cache
    - evict_all_font_caches(): Clear all font caches
"""

from functools import lru_cache

import pygame

# Import from modular components in same package
from .font_loader import (
    evict_all_font_caches,
    get_font,
    get_theme_font,
    init_custom_fonts,
    preload_japanese_fonts,
)
from .localization import (
    get_english_font_by_type as _get_english_font_by_type,
)
from .localization import (
    get_localized_font,
    render_localized_text,
)

# Re-export for backward compatibility
__all__ = [
    "init_custom_fonts",
    "preload_japanese_fonts",
    "get_font",
    "get_theme_font",
    "get_localized_font",
    "render_mixed_text",
    "render_text",
    "render_localized_text",
    "clear_render_cache",
    "evict_all_font_caches",
]


# =============================================================================
# Mixed Text Rendering (Uses TextRenderer Strategy)
# =============================================================================


@lru_cache(maxsize=256)
def _render_mixed_text_cached(
    text: str,
    size: int,
    font_type: str,
    color: tuple,
    antialias: bool,
    language: str,
) -> pygame.Surface:
    """Internal cached version of render_mixed_text.

    Args:
        text: Text to render
        size: Font size
        font_type: 'primary', 'secondary', or 'label'
        color: Text color tuple
        antialias: Whether to use antialiasing
        language: Current language (for cache key)

    Returns:
        pygame.Surface with the rendered text
    """
    from nrhof.ui.text_renderer import TextRendererFactory

    # For English, use the font type mapping directly
    # For other languages, use the localized font loader
    if language == "en":
        localized_loader = _get_english_font_by_type
    else:
        localized_loader = get_localized_font

    # Create appropriate renderer for the language
    renderer = TextRendererFactory.create_renderer(
        language=language,
        localized_font_loader=localized_loader,
        english_font_loader=_get_english_font_by_type,  # Use font type mapping
    )

    # Render using the strategy
    return renderer.render(text, size, font_type, color, antialias)


def render_mixed_text(
    text: str,
    size: int,
    font_type: str,
    color: tuple,
    antialias: bool = True,
) -> pygame.Surface:
    """Render text with mixed fonts: numbers use English font, other characters use localized font.

    Uses the TextRenderer strategy pattern to handle different rendering requirements.
    Results are cached to prevent recreating surfaces for the same text.

    Args:
        text: Text to render
        size: Font size
        font_type: 'primary', 'primary_italic', 'secondary', or 'label'
        color: Text color tuple
        antialias: Whether to use antialiasing

    Returns:
        pygame.Surface with the rendered text
    """
    from nrhof.core.localization import get_language

    # Get current language for cache key
    language = get_language()

    # Automatically lowercase text for primary_italic font type (English only)
    if font_type == "primary_italic" and language == "en":
        text = text.lower()

    # Use cached version
    return _render_mixed_text_cached(text, size, font_type, color, antialias, language)


def render_text(
    text: str,
    size: int = 24,
    *,
    mono: bool = True,
    color=(0, 255, 0),
    antialias=True,
    prefer: str | None = None,
) -> pygame.Surface:
    """Convenience: get a font and render one line of text to a surface."""
    font = get_font(size, mono=mono, prefer=prefer)
    return font.render(text, antialias, color)


def clear_render_cache():
    """Clear the text rendering cache.

    Call this when font configuration changes to force re-rendering.
    """
    _render_mixed_text_cached.cache_clear()
