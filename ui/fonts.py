#!/usr/bin/env python3
"""Font loading and management utilities."""
from pathlib import Path
from functools import lru_cache
import pygame

# Custom fonts cache
_CUSTOM_FONTS = {}
_FONTS_DIR = None
_FONT_CONFIG = None

# Preferred fonts (mono first for "matrix" look, then common mac/win fallbacks)
_MONO_FONT_CANDIDATES = [
    "DejaVu Sans Mono",  # present on Raspberry Pi via fonts-dejavu-core
    "Menlo",             # macOS default mono
    "Courier New",       # Windows common mono
    "Liberation Mono",   # Linux common
]

_SANS_FONT_CANDIDATES = [
    "DejaVu Sans",
    "Arial",
    "Liberation Sans",
]


def init_custom_fonts(config: dict):
    """Initialize custom fonts from config.
    
    Args:
        config: Full config dictionary with 'fonts' section
    """
    global _FONTS_DIR, _FONT_CONFIG
    _FONT_CONFIG = config.get('fonts', {})
    # Get parent directory (project root) since this is now in ui/ subfolder
    project_root = Path(__file__).parent.parent
    _FONTS_DIR = project_root / _FONT_CONFIG.get('directory', 'assets/fonts')
    
    # Preload Japanese fonts to prevent first-use hang
    preload_japanese_fonts()


def preload_japanese_fonts():
    """Preload Japanese fonts to avoid lag on first use."""
    if not _FONTS_DIR:
        return
    
    # Common font sizes used in the app
    common_sizes = [18, 24, 30, 32, 76, 124]
    japanese_fonts = [
        'NotoSansJP-Regular.ttf',
        'NotoSansJP-SemiBold.ttf',
        'DelaGothicOne-Regular.ttf'
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


@lru_cache(maxsize=64)
def get_font(size: int = 24, *, mono: bool = True, prefer: str | None = None, bold: bool = False) -> pygame.font.Font:
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
            custom_font_key = 'mono_bold' if mono else 'sans_bold'
        else:
            custom_font_key = 'mono' if mono else 'sans'
        
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
def get_theme_font(size: int = 24, font_type: str = 'primary') -> pygame.font.Font:
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
    style = theme_loader.load_style('pipboy')
    
    # Get font filename from theme
    font_key = f"{font_type}_font"
    font_filename = style.get('typography', {}).get(font_key)
    
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


def get_localized_font(size: int = 24, font_type: str = 'primary', text: str = None) -> pygame.font.Font:
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
    if text and text == 'NRHOF':
        return get_theme_font(size, font_type)
    
    # Special rule: Version strings (e.g., "v0.2.0") always use IBM Plex Mono
    if text and text.startswith('v') and any(c.isdigit() for c in text):
        return get_theme_font(size, font_type)
    
    # Labels always use English fonts (Compadre)
    if font_type == 'label':
        return get_theme_font(size, font_type)
    
    # For non-Japanese, use standard fonts
    if current_lang != 'jp':
        return get_theme_font(size, font_type)
    
    # Japanese font mapping
    theme_loader = get_theme_loader()
    style = theme_loader.load_style('pipboy')
    font_key = f"{font_type}_font"
    font_filename = style.get('typography', {}).get(font_key, '')
    
    # Map to Japanese fonts
    jp_font_map = {
        'IBMPlexMono-Regular.ttf': 'NotoSansJP-Regular.ttf',
        'IBMPlexMono-Italic.ttf': 'NotoSansJP-Regular.ttf',
        'IBMPlexMono-SemiBoldItalic.ttf': 'NotoSansJP-SemiBold.ttf',
        'miland.otf': 'DelaGothicOne-Regular.ttf',
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


def render_mixed_text(text: str, size: int, font_type: str, color: tuple, antialias: bool = True) -> pygame.Surface:
    """Render text with mixed fonts: numbers use English font, other characters use localized font.
    
    Uses the TextRenderer strategy pattern to handle different rendering requirements.
    
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
    from .text_renderer import TextRendererFactory
    
    # Get current language
    language = get_language()
    
    # Create appropriate renderer for the language
    renderer = TextRendererFactory.create_renderer(
        language=language,
        localized_font_loader=get_localized_font,
        english_font_loader=get_theme_font
    )
    
    # Render using the strategy
    return renderer.render(text, size, font_type, color, antialias)


def render_text(text: str, size: int = 24, *, mono: bool = True, color=(0, 255, 0), antialias=True, prefer: str | None = None) -> pygame.Surface:
    """Convenience: get a font and render one line of text to a surface."""
    font = get_font(size, mono=mono, prefer=prefer)
    return font.render(text, antialias, color)


def render_localized_text(text: str, size: int, font_type: str, color: tuple, antialias: bool = True, english_font: pygame.font.Font = None) -> pygame.Surface:
    """Render text with automatic localization support.
    
    This is a convenience wrapper that automatically uses mixed-font rendering
    for Japanese text (numbers in English font, other characters in Japanese font)
    and standard rendering for English text.
    
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
        
        # With custom English font (e.g., IBM Plex Mono Italic)
        custom_font = pygame.font.Font('path/to/font.ttf', 48)
        surface = render_localized_text('listening', 48, 'primary', (233, 30, 99), english_font=custom_font)
    """
    from core.localization import get_language
    
    # Get current language
    language = get_language()
    
    # For Japanese, use mixed text rendering
    if language == 'jp':
        return render_mixed_text(text, size, font_type, color, antialias)
    else:
        # For English, use custom font if provided, otherwise use theme font
        if english_font:
            return english_font.render(text, antialias, color)
        else:
            font = get_theme_font(size, font_type)
            return font.render(text, antialias, color)