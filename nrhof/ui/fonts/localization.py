#!/usr/bin/env python3
"""Localization-aware font selection.

This module handles:
- Language-specific font selection (English vs Japanese)
- Font mapping for different languages
- Special rules for specific text (NRHOF, version strings, labels)
- Mixed-font rendering support

Public API:
    - get_localized_font(size, font_type, text): Get language-appropriate font
    - get_english_font_by_type(size, font_type, text): Get English font
    - render_localized_text(text, size, font_type, color, antialias, english_font): Render with localization
"""

from pathlib import Path

import pygame


def get_localized_font(
    size: int = 24,
    font_type: str = "primary",
    text: str = None,
) -> pygame.font.Font:
    """Get a font that supports the current language.

    For Japanese (jp), maps fonts as follows:
    - IBM Plex Mono Regular -> Noto Sans JP Regular
    - IBM Plex Mono Italic -> Noto Sans JP Regular
    - IBM Plex Mono SemiBold -> Noto Sans JP SemiBold
    - Miland -> Dela Gothic One-Regular

    Special rules:
    - Label fonts (Compadre) always stay English and use the standard font.
    - "NRHOF" text always uses Miland font (secondary) and is never translated.

    Args:
        size: Font size in points
        font_type: 'primary', 'secondary', or 'label'
        text: Optional text content to check for special cases like "NRHOF"

    Returns:
        pygame.Font object
    """
    from nrhof.core.localization import get_language

    from .font_loader import get_theme_font

    try:
        pygame.font.get_init() or pygame.font.init()
    except Exception:
        pass

    # Get current language
    current_lang = get_language()

    # Special rule: "NRHOF" always uses Miland font (never translated, never uses Japanese font)
    if text and text == "NRHOF":
        return get_theme_font(size, font_type)

    # Special rule: Version strings (e.g., "v0.2.0") always use IBM Plex Mono
    if text and text.startswith("v") and any(c.isdigit() for c in text):
        return get_theme_font(size, font_type)

    # Labels always use English fonts (Compadre)
    if font_type == "label":
        return get_theme_font(size, font_type)

    # For non-Japanese, use standard fonts
    if current_lang != "jp":
        return get_theme_font(size, font_type)

    # Japanese font mapping
    from nrhof.core.theme_loader import get_theme_loader

    theme_loader = get_theme_loader()
    style = theme_loader.load_style("pipboy")
    # Normalize primary_italic to primary for theme lookup (theme doesn't have primary_italic_font)
    theme_font_type = "primary" if font_type == "primary_italic" else font_type
    font_key = f"{theme_font_type}_font"
    font_filename = style.get("typography", {}).get(font_key, "")

    # Map to Japanese fonts
    jp_font_map = {
        "IBMPlexMono-Regular.ttf": "NotoSansJP-Regular.ttf",
        "IBMPlexMono-Italic.ttf": "NotoSansJP-Regular.ttf",
        "IBMPlexMono-SemiBoldItalic.ttf": "NotoSansJP-SemiBold.ttf",
        "miland.otf": "DelaGothicOne-Regular.ttf",
    }

    jp_font_filename = jp_font_map.get(font_filename, font_filename)

    # Load the Japanese font
    project_root = Path(__file__).parent.parent.parent.parent
    font_path = project_root / "assets" / "fonts" / jp_font_filename
    if font_path.exists():
        try:
            return pygame.font.Font(str(font_path), size)
        except Exception as e:
            print(f"Failed to load Japanese font {jp_font_filename}: {e}")

    # Fallback to standard font
    return get_theme_font(size, font_type)


def get_english_font_by_type(size: int, font_type: str, text: str = "") -> pygame.font.Font:
    """Get English font based on font_type, respecting the font mapping.

    Args:
        size: Font size
        font_type: 'primary', 'secondary', or 'label'
        text: Text to render (unused, for compatibility with font loader signature)

    Returns:
        pygame.font.Font
    """
    from .font_loader import get_theme_font

    # Map font_type to English font files
    font_map = {
        "primary": "IBMPlexMono-Regular.ttf",  # Primary is regular
        "primary_italic": "IBMPlexMono-Italic.ttf",  # Primary italic for tabs/titles
        "secondary": "miland.otf",
        "label": "Compadre-Extended.otf",
    }
    font_filename = font_map.get(font_type, "IBMPlexMono-Regular.ttf")
    project_root = Path(__file__).parent.parent.parent.parent
    font_path = project_root / "assets" / "fonts" / font_filename
    if font_path.exists():
        try:
            return pygame.font.Font(str(font_path), size)
        except Exception as e:
            print(f"Failed to load English font {font_filename}: {e}")
    # Fallback to theme font
    return get_theme_font(size, font_type)


def render_localized_text(
    text: str,
    size: int,
    font_type: str,
    color: tuple,
    antialias: bool = True,
    english_font: pygame.font.Font = None,
) -> pygame.Surface:
    """Render text with automatic localization support.

    This function automatically detects Japanese characters in the text and uses
    appropriate fonts:
    - Japanese characters (Hiragana, Katakana, Kanji) -> Noto Sans JP
    - English/ASCII characters -> IBM Plex Mono (or custom font)

    This allows mixed-language text like "ura • 椎名林檎" to render correctly
    with each portion using the appropriate font.

    Args:
        text: Text to render
        size: Font size
        font_type: 'primary', 'secondary', or 'label'
        color: Text color tuple
        antialias: Whether to use antialiasing
        english_font: Optional custom font to use for English (if None, uses theme font)

    Returns:
        pygame.Surface with the rendered text

    Example:
        # Automatically handles both English and Japanese
        surface = render_localized_text('listening', 48, 'primary', (233, 30, 99))
        surface = render_localized_text('音楽認識中', 48, 'primary', (233, 30, 99))
        surface = render_localized_text('ura • 椎名林檎', 48, 'primary', (233, 30, 99))

        # With custom English font (e.g., IBM Plex Mono Italic)
        custom_font = pygame.font.Font('path/to/font.ttf', 48)
        surface = render_localized_text('listening', 48, 'primary', (233, 30, 99), english_font=custom_font)
    """
    from nrhof.ui.text_renderer import CharacterMixedFontTextRenderer, contains_japanese

    from .font_loader import get_theme_font

    # Check if text contains Japanese characters
    has_japanese = contains_japanese(text)

    # If text contains Japanese characters, use character-level mixed font rendering
    # This works regardless of UI language setting and ensures:
    # - English/ASCII text uses the appropriate English font (IBM Plex Mono, etc.)
    # - Japanese text uses Noto Sans JP
    if has_japanese:
        # Create a Japanese font loader that returns Noto Sans JP
        def _get_japanese_font(size: int, font_type: str, text: str) -> pygame.font.Font:
            """Get Japanese font (Noto Sans JP).

            Args:
                size: Font size
                font_type: Font type (unused for Japanese)
                text: Text to render (unused)
            """
            # Go up from nrhof/ui/fonts/localization.py to project root
            project_root = Path(__file__).parent.parent.parent.parent
            jp_font_path = project_root / "assets" / "fonts" / "NotoSansJP-Regular.ttf"
            if jp_font_path.exists():
                try:
                    return pygame.font.Font(str(jp_font_path), size)
                except Exception as e:
                    print(f"Failed to load Japanese font: {e}")
            # Fallback to theme font
            return get_theme_font(size, font_type)

        # Create English font loader (uses custom font or theme font)
        def english_font_loader_wrapper(size: int, font_type: str) -> pygame.font.Font:
            if english_font:
                return english_font
            # Always use English fonts, not localized fonts
            # Map font_type to English font files
            font_map = {
                "primary": "IBMPlexMono-Italic.ttf",  # Primary is italic for body text
                "secondary": "miland.otf",
                "label": "Compadre-Extended.otf",
            }
            font_filename = font_map.get(font_type, "IBMPlexMono-Regular.ttf")
            # Go up from nrhof/ui/fonts/localization.py to project root
            project_root = Path(__file__).parent.parent.parent.parent
            font_path = project_root / "assets" / "fonts" / font_filename
            if font_path.exists():
                try:
                    return pygame.font.Font(str(font_path), size)
                except Exception as e:
                    print(f"Failed to load English font {font_filename}: {e}")
            # Fallback to theme font
            return get_theme_font(size, font_type)

        # Use character-level mixed font renderer
        renderer = CharacterMixedFontTextRenderer(english_font_loader_wrapper, _get_japanese_font)
        return renderer.render(text, size, font_type, color, antialias)

    # No Japanese characters, use standard English rendering
    if english_font:
        return english_font.render(text, antialias, color)
    else:
        # Always use English fonts, not localized fonts
        # Map font_type to English font files
        font_map = {
            "primary": "IBMPlexMono-Italic.ttf",  # Primary is italic for body text
            "secondary": "miland.otf",
            "label": "Compadre-Extended.otf",
        }
        font_filename = font_map.get(font_type, "IBMPlexMono-Regular.ttf")
        # Go up from nrhof/ui/fonts/localization.py to project root
        project_root = Path(__file__).parent.parent.parent.parent
        font_path = project_root / "assets" / "fonts" / font_filename
        if font_path.exists():
            try:
                font = pygame.font.Font(str(font_path), size)
                return font.render(text, antialias, color)
            except Exception as e:
                print(f"Failed to load English font {font_filename}: {e}")
        # Fallback to theme font
        font = get_theme_font(size, font_type)
        return font.render(text, antialias, color)
