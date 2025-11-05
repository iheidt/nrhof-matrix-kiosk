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
    from theme_loader import get_theme_loader
    
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


def render_text(text: str, size: int = 24, *, mono: bool = True, color=(0, 255, 0), antialias=True, prefer: str | None = None) -> pygame.Surface:
    """Convenience: get a font and render one line of text to a surface."""
    font = get_font(size, mono=mono, prefer=prefer)
    return font.render(text, antialias, color)