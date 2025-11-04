#!/usr/bin/env python3
import os
import math
import subprocess
from pathlib import Path
from io import BytesIO
from functools import lru_cache

import numpy as np
import pygame
from pygame import Surface
from PIL import Image

try:
    import cairosvg  # type: ignore
    HAVE_CAIROSVG = True
except Exception:
    HAVE_CAIROSVG = False

ROOT = Path(__file__).resolve().parent

# Screen margin constants - safe zones where content should not be drawn
FOOTER_HEIGHT = 50  # pixels from bottom of screen
MARGIN_TOP = 20     # pixels from top of screen
MARGIN_LEFT = 20    # pixels from left edge
MARGIN_RIGHT = 20   # pixels from right edge
MARGIN_BOTTOM = FOOTER_HEIGHT + 20  # footer + spacing

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


def draw_back_arrow(surface: Surface, color: tuple = (140, 255, 140)) -> pygame.Rect:
    """Draw a back arrow in the top-left corner.
    
    Args:
        surface: Pygame surface to draw on
        color: RGB color tuple for the arrow
        
    Returns:
        pygame.Rect: Clickable area for the back arrow
    """
    # Dim the color slightly for subtle appearance
    arrow_color = tuple(int(c * 0.8) for c in color)
    
    # Draw back arrow text
    font = get_theme_font(24, 'primary')
    arrow_text = "< back"
    text_surface = font.render(arrow_text, True, arrow_color)
    
    # Position in top-left with margins
    x = MARGIN_LEFT
    y = MARGIN_TOP
    
    surface.blit(text_surface, (x, y))
    
    # Return clickable rect
    return pygame.Rect(x, y, text_surface.get_width(), text_surface.get_height())


def draw_card(surface: Surface, x: int, y: int, width: int, height: int, theme: dict = None,
             border_solid: str = None, border_fade_pct: float = None):
    """Draw a card using common card component styling with optional gradient fade.
    
    Args:
        surface: Pygame surface to draw on
        x: X position
        y: Y position
        width: Card width (or 'auto' to use container width)
        height: Card height
        theme: Theme dictionary with layout and style (optional)
        border_solid: Override for which side stays solid ('top' or 'bottom')
        border_fade_pct: Override for fade percentage (0.0-1.0)
    
    Returns:
        Rect of the card's content area (inside padding)
    """
    from theme_loader import get_theme_loader
    
    # Load theme if not provided
    if theme is None:
        theme_loader = get_theme_loader()
        layout = theme_loader.load_layout('menu')  # Use any layout to get base
        style = theme_loader.load_style('pipboy')
        theme = {'layout': layout, 'style': style}
    
    # Get card settings from layout
    card_settings = theme['layout'].get('card', {})
    border_width = card_settings.get('border', 6)
    padding = card_settings.get('padding', 24)
    
    # Use overrides if provided, otherwise use layout defaults
    if border_solid is None:
        border_solid = card_settings.get('border_solid', 'top')  # 'top' or 'bottom'
    if border_fade_pct is None:
        border_fade_pct = card_settings.get('border_fade_pct', 0.33)  # 0.0-1.0
    
    # Get border color from style
    border_color_name = card_settings.get('border_color', 'primary')
    border_color = tuple(theme['style']['colors'][border_color_name])
    
    # Draw card border with gradient fade
    if border_fade_pct > 0:
        _draw_card_border_with_fade(surface, x, y, width, height, border_width, 
                                   border_color, border_solid, border_fade_pct)
    else:
        # Simple solid border
        pygame.draw.rect(surface, border_color, (x, y, width, height), border_width)
    
    # Return content area (inside padding)
    content_x = x + padding
    content_y = y + padding
    content_width = width - (padding * 2)
    content_height = height - (padding * 2)
    
    return pygame.Rect(content_x, content_y, content_width, content_height)


def _draw_card_border_with_fade(surface: Surface, x: int, y: int, width: int, height: int,
                                border_width: int, color: tuple, solid_side: str, fade_pct: float):
    """Draw a card border with gradient fade to transparent using surfarray for per-pixel alpha.
    
    Args:
        surface: Pygame surface to draw on
        x, y: Card position
        width, height: Card dimensions
        border_width: Border thickness
        color: RGB color tuple
        solid_side: 'top' or 'bottom' - which side stays solid
        fade_pct: Percentage of border that fades (0.0-1.0)
    """
    # Ensure color is a valid RGB tuple with integers
    if len(color) >= 3:
        base_color = (int(color[0]), int(color[1]), int(color[2]))
    else:
        base_color = (255, 255, 255)
    
    # Create a surface with alpha channel for transparency
    border_surface = pygame.Surface((width + border_width * 2, height + border_width * 2), pygame.SRCALPHA)
    border_surface.fill((0, 0, 0, 0))  # Start fully transparent
    
    # Use surfarray for direct pixel manipulation
    import pygame.surfarray as surfarray
    import numpy as np
    
    # Get pixel arrays for RGB and alpha
    pixels_rgb = surfarray.pixels3d(border_surface)
    pixels_alpha = surfarray.pixels_alpha(border_surface)
    
    if solid_side == 'bottom':
        # Bottom is solid, top fades to transparent
        # fade_pct is the percentage that fades (e.g., 0.9 = top 90% fades, bottom 10% solid)
        fade_start = int(height * fade_pct)
        
        # Draw each horizontal line with appropriate alpha
        for i in range(height + border_width):
            if i < fade_start:
                # Fading portion at top (transparent at i=0, solid at fade_start)
                progress = i / fade_start if fade_start > 0 else 0
                alpha = int(255 * progress)
            else:
                # Solid portion at bottom
                alpha = 255
            
            # Set RGB and alpha for this row
            # Top border
            if i < border_width:
                pixels_rgb[:, i] = base_color
                pixels_alpha[:, i] = alpha
            else:
                # Left border
                pixels_rgb[0:border_width, i] = base_color
                pixels_alpha[0:border_width, i] = alpha
                # Right border
                pixels_rgb[width + border_width:width + border_width * 2, i] = base_color
                pixels_alpha[width + border_width:width + border_width * 2, i] = alpha
                # Bottom border
                if i >= height:
                    pixels_rgb[:, i] = base_color
                    pixels_alpha[:, i] = alpha
    else:
        # Top is solid, bottom fades to transparent
        fade_end = int(height * (1 - fade_pct))
        
        # Set alpha channel using surfarray
        for i in range(height + border_width):
            if i <= fade_end:
                # Solid portion at top
                alpha = 255
            else:
                # Fading portion at bottom
                progress = (i - fade_end) / (height - fade_end) if (height - fade_end) > 0 else 0
                alpha = int(255 * (1.0 - progress))
            
            # Set RGB and alpha for this row
            # Top border
            if i < border_width:
                pixels_rgb[:, i] = base_color
                pixels_alpha[:, i] = alpha
            else:
                # Left border
                pixels_rgb[0:border_width, i] = base_color
                pixels_alpha[0:border_width, i] = alpha
                # Right border
                pixels_rgb[width + border_width:width + border_width * 2, i] = base_color
                pixels_alpha[width + border_width:width + border_width * 2, i] = alpha
                # Bottom border
                if i >= height:
                    pixels_rgb[:, i] = base_color
                    pixels_alpha[:, i] = alpha
    
    # Release the pixel array locks
    del pixels_rgb
    del pixels_alpha
    
    # Blit the border surface onto the main surface
    surface.blit(border_surface, (x - border_width, y - border_width))


def draw_footer(surface: Surface, color: tuple = (140, 255, 140)):
    """Draw footer with settings card and company name div.
    
    Footer structure:
    - Card (80px): "settings" (left) | version (right)
    - Div (50px): "BIG NERD INDUSTRIES INC. 2025" (centered)
    
    Args:
        surface: Pygame surface to draw on
        color: RGB color tuple (not used, colors from theme)
    """
    from theme_loader import get_theme_loader
    from __version__ import __version__
    
    w, h = surface.get_size()
    
    # Load theme
    theme_loader = get_theme_loader()
    layout = theme_loader.load_layout('menu')  # Get base layout
    style = theme_loader.load_style('pipboy')
    
    # Get margins and footer settings
    margins = layout.get('margins', {})
    margin_left = margins.get('left', 50)
    margin_right = margins.get('right', 50)
    footer_settings = layout.get('footer', {})
    footer_height = footer_settings.get('height', 130)
    footer_fade_pct = footer_settings.get('border_fade_pct', 0.33)
    
    # Calculate positions
    footer_top = h - footer_height
    card_height = 80
    div_height = 50
    
    # Draw settings card
    card_x = margin_left
    card_y = footer_top
    card_width = w - margin_left - margin_right
    
    content_rect = draw_card(surface, card_x, card_y, card_width, card_height, 
                            theme={'layout': layout, 'style': style},
                            border_solid='bottom',
                            border_fade_pct=footer_fade_pct)
    
    # Draw "settings" text (left aligned in card)
    primary_color = tuple(style['colors']['primary'])
    micro_size = style['typography']['fonts']['micro']
    settings_font = get_theme_font(micro_size, 'primary')
    settings_text = settings_font.render("settings", True, primary_color)
    surface.blit(settings_text, (content_rect.x, content_rect.y + (content_rect.height - settings_text.get_height()) // 2))
    
    # Draw version number (right aligned in card)
    secondary_color = tuple(style['colors']['secondary'])
    pico_size = style['typography']['fonts']['pico']
    version_font = get_theme_font(pico_size, 'primary')
    version_text = version_font.render(f"v{__version__}", True, secondary_color)
    version_x = content_rect.x + content_rect.width - version_text.get_width()
    surface.blit(version_text, (version_x, content_rect.y + (content_rect.height - version_text.get_height()) // 2))
    
    # Draw company name div (50px tall, below card)
    div_y = card_y + card_height
    footer_size = style['typography']['fonts']['footer']
    company_font = get_theme_font(footer_size, 'label')
    company_text = company_font.render("BIG NERD INDUSTRIES INC. 2025", True, primary_color)
    company_x = (w - company_text.get_width()) // 2
    company_y = div_y + (div_height - company_text.get_height()) // 2
    surface.blit(company_text, (company_x, company_y))


def vignette(surface: Surface, strength: float = 0.6):
    w, h = surface.get_size()
    vg = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy)
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy) / maxd
            a = int(255 * max(0, min(1, (d ** 2) * strength)))
            vg.set_at((x, y), (0, 0, 0, a))
    surface.blit(vg, (0, 0))


def load_icon(path: Path, size: tuple[int, int]) -> Surface | None:
    try:
        if path.suffix.lower() == ".svg" and HAVE_CAIROSVG:
            png_bytes = cairosvg.svg2png(url=str(path), output_width=size[0], output_height=size[1])
            pil_img = Image.open(BytesIO(png_bytes)).convert("RGBA")
        else:
            pil_img = Image.open(path).convert("RGBA")
        pil_img = pil_img.resize(size, Image.LANCZOS)
        mode = pil_img.mode
        data = pil_img.tobytes()
        return pygame.image.fromstring(data, pil_img.size, mode)
    except Exception:
        return None


def launch_command(cmd: str):
    try:
        # Use shell so simple strings work; you can switch to list if needed
        subprocess.Popen(cmd, shell=True)
    except Exception as e:
        print(f"Failed to launch '{cmd}': {e}")


# ---------------- Font helpers (centralized) ----------------

from pathlib import Path

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
    _FONTS_DIR = Path(__file__).parent / _FONT_CONFIG.get('directory', 'assets/fonts')
    
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
        # Try to load custom font
        font_path = Path(__file__).parent / "assets" / "fonts" / font_filename
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

def measure_text(text: str, size: int = 24, *, mono: bool = True, prefer: str | None = None) -> tuple[int, int]:
    """Return (width, height) for a string at a given size."""
    font = get_font(size, mono=mono, prefer=prefer)
    return font.size(text)


# ---------------- Audio helpers (dev fallback) ----------------

def dev_sine_frame(length: int = 2048, sample_rate: int = 48000, freq: float = 220.0) -> np.ndarray:
    """
    Generate a mono sine wave frame for development when a live mic buffer isn't wired.
    Returns float32 in [-1,1].
    
    Args:
        length: Number of samples to generate
        sample_rate: Sample rate in Hz
        freq: Frequency of sine wave in Hz
        
    Returns:
        numpy array of float32 audio samples
    """
    t = np.arange(length, dtype=np.float32) / float(sample_rate)
    return np.sin(2.0 * math.pi * freq * t).astype(np.float32)
