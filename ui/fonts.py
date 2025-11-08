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
    1. Font Loading: Load custom fonts or fall back to system fonts
    2. Font Caching: LRU cache to prevent reloading (@lru_cache)
    3. Text Rendering: Mixed-font rendering for Japanese (numbers in English font)
    4. Localization: Language-aware font selection

Public API:
    - init_custom_fonts(config): Initialize font system
    - get_font(size, family, bold): Get cached font
    - get_theme_font(size, font_type): Get font from theme
    - get_localized_font(size, font_type, text): Get language-appropriate font
    - render_mixed_text(text, size, font_type, color): Render with mixed fonts
    - render_localized_text(text, size, font_type, color, english_font): Convenience wrapper

Internal:
    - _load_custom_font(): Load TTF/OTF from assets
    - _first_available_font(): Find first available system font
    - _render_mixed_text_cached(): Cached mixed-font rendering
"""

from functools import lru_cache
from pathlib import Path

import pygame

# =============================================================================
# Module-level State and Configuration
# =============================================================================

# Custom fonts cache
_CUSTOM_FONTS = {}
_FONTS_DIR = None
_FONT_CONFIG = None

# Preferred fonts (mono first for "matrix" look, then common mac/win fallbacks)
_MONO_FONT_CANDIDATES = [
    "DejaVu Sans Mono",  # present on Raspberry Pi via fonts-dejavu-core
    "Menlo",  # macOS default mono
    "Courier New",  # Windows common mono
    "Liberation Mono",  # Linux common
]

_SANS_FONT_CANDIDATES = [
    "DejaVu Sans",
    "Arial",
    "Liberation Sans",
]


# =============================================================================
# Initialization and Preloading
# =============================================================================


def init_custom_fonts(config: dict):
    """Initialize custom fonts from config.

    Args:
        config: Full config dictionary with 'fonts' section
    """
    global _FONTS_DIR, _FONT_CONFIG
    _FONT_CONFIG = config.get("fonts", {})
    # Get parent directory (project root) since this is now in ui/ subfolder
    project_root = Path(__file__).parent.parent
    _FONTS_DIR = project_root / _FONT_CONFIG.get("directory", "assets/fonts")

    # Preload Japanese fonts to prevent first-use hang
    preload_japanese_fonts()


def preload_japanese_fonts():
    """Preload Japanese fonts to avoid lag on first use."""
    if not _FONTS_DIR:
        return

    # Common font sizes used in the app
    common_sizes = [18, 24, 30, 32, 76, 124]
    japanese_fonts = [
        "NotoSansJP-Regular.ttf",
        "NotoSansJP-SemiBold.ttf",
        "DelaGothicOne-Regular.ttf",
    ]

    for font_file in japanese_fonts:
        font_path = _FONTS_DIR / font_file
        if font_path.exists():
            for size in common_sizes:
                try:
                    # Load font into cache
                    pygame.font.Font(str(font_path), size)
                except Exception:
                    pass  # Silently skip if font fails to load


# =============================================================================
# Font Loading (Custom and System Fonts)
# =============================================================================


def _load_custom_font(filename: str, size: int) -> pygame.font.Font | None:
    """Load a custom font file.

    Args:
        filename: Font filename (e.g., 'JetBrainsMono-Regular.ttf')
        size: Font size

    Returns:
        pygame.Font or None if not found
    """
    if not filename or not _FONTS_DIR:
        return None

    font_path = _FONTS_DIR / filename
    if not font_path.exists():
        return None

    try:
        return pygame.font.Font(str(font_path), size)
    except Exception as e:
        print(f"Failed to load custom font {filename}: {e}")
        return None


def _first_available_font(candidates):
    """Return the first available font name from the candidate list."""
    for name in candidates:
        try:
            # SysFont returns a Font even if it needs to map; we still prefer ordered list
            f = pygame.font.SysFont(name, 12)
            if isinstance(f, pygame.font.Font):
                return name
        except Exception:
            pass
    # As a last resort, None lets pygame pick a default
    return None


# =============================================================================
# Font Caching (Public API)
# =============================================================================


@lru_cache(maxsize=64)
def get_font(
    size: int = 24,
    *,
    mono: bool = True,
    prefer: str | None = None,
    bold: bool = False,
) -> pygame.font.Font:
    """
    Centralized font getter with caching and sane fallbacks.
    - size: point size
    - mono: True picks monospaced candidates; False picks sans candidates
    - prefer: exact font name to try first (optional)
    - bold: Use bold variant if available
    """
    try:
        pygame.font.get_init() or pygame.font.init()
    except Exception:
        # Will be initialized by pygame.init() elsewhere, but we try anyway
        pass

    # Try custom fonts first
    if _FONT_CONFIG:
        if bold:
            custom_font_key = "mono_bold" if mono else "sans_bold"
        else:
            custom_font_key = "mono" if mono else "sans"

        custom_font_file = _FONT_CONFIG.get(custom_font_key)
        if custom_font_file:
            custom_font = _load_custom_font(custom_font_file, size)
            if custom_font:
                return custom_font

    # Fall back to system fonts
    candidates = []
    if prefer:
        candidates.append(prefer)
    candidates.extend(_MONO_FONT_CANDIDATES if mono else _SANS_FONT_CANDIDATES)

    chosen = _first_available_font(candidates)
    try:
        if chosen:
            return pygame.font.SysFont(chosen, size, bold=bold)
        else:
            return pygame.font.Font(None, size)
    except Exception:
        return pygame.font.Font(None, size)


@lru_cache(maxsize=64)
def get_theme_font(size: int = 24, font_type: str = "primary") -> pygame.font.Font:
    """Get a font from the theme.

    Args:
        size: Font size in points
        font_type: 'primary', 'secondary', or 'label'

    Returns:
        pygame.Font object
    """
    from core.theme_loader import get_theme_loader

    try:
        pygame.font.get_init() or pygame.font.init()
    except Exception:
        pass

    # Load theme
    theme_loader = get_theme_loader()
    style = theme_loader.load_style("pipboy")

    # Get font filename from theme
    font_key = f"{font_type}_font"
    font_filename = style.get("typography", {}).get(font_key)

    if font_filename:
        # Try to load custom font (get project root since we're in ui/ subfolder)
        project_root = Path(__file__).parent.parent
        font_path = project_root / "assets" / "fonts" / font_filename
        if font_path.exists():
            try:
                return pygame.font.Font(str(font_path), size)
            except Exception as e:
                print(f"Failed to load theme font {font_filename}: {e}")

    # Fallback to system font
    return pygame.font.Font(None, size)


# =============================================================================
# Localization-Aware Font Selection
# =============================================================================


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
    from core.localization import get_language
    from core.theme_loader import get_theme_loader

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
    theme_loader = get_theme_loader()
    style = theme_loader.load_style("pipboy")
    font_key = f"{font_type}_font"
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
    project_root = Path(__file__).parent.parent
    font_path = project_root / "assets" / "fonts" / jp_font_filename
    if font_path.exists():
        try:
            return pygame.font.Font(str(font_path), size)
        except Exception as e:
            print(f"Failed to load Japanese font {jp_font_filename}: {e}")

    # Fallback to standard font
    return get_theme_font(size, font_type)


# =============================================================================
# Text Rendering (Mixed Fonts for Japanese)
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
    from .text_renderer import TextRendererFactory

    # Create appropriate renderer for the language
    renderer = TextRendererFactory.create_renderer(
        language=language,
        localized_font_loader=get_localized_font,
        english_font_loader=get_theme_font,
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
        font_type: 'primary', 'secondary', or 'label'
        color: Text color tuple
        antialias: Whether to use antialiasing

    Returns:
        pygame.Surface with the rendered text
    """
    from core.localization import get_language

    # Get current language for cache key
    language = get_language()

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


def evict_all_font_caches():
    """Clear all font and text rendering caches.

    This should be called during scene cleanup to prevent memory leaks.
    Clears:
    - get_font LRU cache (maxsize=64)
    - get_theme_font LRU cache (maxsize=64)
    - _render_mixed_text_cached LRU cache (maxsize=256)
    """
    get_font.cache_clear()
    get_theme_font.cache_clear()
    _render_mixed_text_cached.cache_clear()


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

    from .text_renderer import CharacterMixedFontTextRenderer, contains_japanese

    # Check if text contains Japanese characters
    has_japanese = contains_japanese(text)

    # If text contains Japanese characters, use character-level mixed font rendering
    # This works regardless of UI language setting and ensures:
    # - English/ASCII text uses the appropriate English font (IBM Plex Mono, etc.)
    # - Japanese text uses Noto Sans JP
    if has_japanese:
        # Create a Japanese font loader that returns Noto Sans JP
        def japanese_font_loader(size: int, font_type: str, text: str = None) -> pygame.font.Font:
            # Map to Noto Sans JP Regular for all Japanese text
            project_root = Path(__file__).parent.parent
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
            project_root = Path(__file__).parent.parent
            font_path = project_root / "assets" / "fonts" / font_filename
            if font_path.exists():
                try:
                    return pygame.font.Font(str(font_path), size)
                except Exception as e:
                    print(f"Failed to load English font {font_filename}: {e}")
            # Fallback to theme font
            return get_theme_font(size, font_type)

        # Use character-level mixed font renderer
        renderer = CharacterMixedFontTextRenderer(english_font_loader_wrapper, japanese_font_loader)
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
        project_root = Path(__file__).parent.parent
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
