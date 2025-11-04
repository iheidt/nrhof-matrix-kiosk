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


def get_matrix_green(config: dict) -> tuple:
    """Get the matrix green color from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        RGB tuple for matrix green color
    """
    return tuple(config.get("matrix_green", [140, 255, 140]))


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
    font = get_font(24)
    arrow_text = "< back"
    text_surface = font.render(arrow_text, True, arrow_color)
    
    # Position in top-left with margins
    x = MARGIN_LEFT
    y = MARGIN_TOP
    
    surface.blit(text_surface, (x, y))
    
    # Return clickable rect
    return pygame.Rect(x, y, text_surface.get_width(), text_surface.get_height())


def draw_footer(surface: Surface, color: tuple = (140, 255, 140)):
    """Draw a subtle technical footer at the bottom of the screen.
    
    Args:
        surface: Pygame surface to draw on
        color: RGB color tuple for the footer text
    """
    w, h = surface.get_size()
    
    # Dim the color for subtle appearance
    dim_color = tuple(c // 4 for c in color)
    
    # Draw horizontal line separator
    line_y = h - FOOTER_HEIGHT + 5
    pygame.draw.line(surface, dim_color, (20, line_y), (w - 20, line_y), 1)
    
    # Draw footer text
    font = get_font(16)  # Increased from 14
    footer_text = "big nerd industries inc. ©2025"
    text_surface = font.render(footer_text, True, dim_color)
    text_rect = text_surface.get_rect()
    text_rect.centerx = w // 2
    text_rect.bottom = h - 12
    surface.blit(text_surface, text_rect)


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
