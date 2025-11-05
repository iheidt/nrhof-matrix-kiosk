#!/usr/bin/env python3
"""Widget components - timeclock, d20, now playing."""
import pygame
from pygame import Surface
from pathlib import Path

# Import from parent ui modules
from ..fonts import get_theme_font
from ..icons import load_icon
from ..components.cards import draw_card


def draw_timeclock(surface: Surface, x: int, y: int, width: int, height: int, theme: dict = None) -> pygame.Rect:
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
    style = theme.get('style', {})
    layout = theme.get('layout', {})
    
    # Get colors
    primary_color = tuple(style.get('colors', {}).get('primary', (255, 20, 147)))
    dim_color_hex = style['colors'].get('dim', '#2C405B')
    if isinstance(dim_color_hex, str) and dim_color_hex.startswith('#'):
        dim_color = tuple(int(dim_color_hex[i:i+2], 16) for i in (1, 3, 5))
    else:
        dim_color = tuple(dim_color_hex) if isinstance(dim_color_hex, (list, tuple)) else (44, 64, 91)
    
    # Get timeclock settings from layout
    timeclock_settings = layout.get('timeclock', {})
    border_fade_pct = timeclock_settings.get('border_fade_pct', 0.9)
    
    # Draw card border with fade (top solid, bottom/sides fade)
    draw_card(surface, x, y, width, height, theme=theme, 
              border_solid='top', border_fade_pct=border_fade_pct)
    
    # Get current time and date
    from datetime import datetime
    now = datetime.now()
    
    # Format time
    ampm = now.strftime("%p")  # AM or PM
    time_str = now.strftime("%I:%M")  # 05:30 (with leading zero)
    
    # Load fonts
    # AM/PM: Miland 30px
    ampm_font_path = Path(__file__).parent.parent.parent / "assets" / "fonts" / "miland.otf"
    ampm_font = pygame.font.Font(str(ampm_font_path), 30)
    
    # Time: IBM Plex Semibold Italic 124px (display size)
    time_font_path = Path(__file__).parent.parent.parent / "assets" / "fonts" / "IBMPlexMono-SemiBoldItalic.ttf"
    time_font = pygame.font.Font(str(time_font_path), 124)
    
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


def draw_d20(surface: Surface, x: int, y: int, width: int, height: int = 300, theme: dict = None) -> pygame.Rect:
    """Draw d20 SVG component with speech_synthesizer below it.
    
    Args:
        surface: Surface to draw on
        x: X position
        y: Y position  
        width: Container width
        height: Container height (default 300px)
        theme: Theme dict with style
    
    Returns:
        Rect of the component
    """
    if theme is None:
        theme = {}
    style = theme.get('style', {})
    
    # Get primary color for d20 SVG fill
    primary_color = tuple(style.get('colors', {}).get('primary', (255, 20, 147)))
    
    # Get dim color for speech synthesizer
    dim_hex = style['colors'].get('dim', '#2C405B')
    if isinstance(dim_hex, str) and dim_hex.startswith('#'):
        dim_color = tuple(int(dim_hex[i:i+2], 16) for i in (1, 3, 5))
    else:
        dim_color = tuple(dim_hex) if isinstance(dim_hex, (list, tuple)) else (44, 64, 91)
    
    # Calculate space for d20 (leaving room for speech synth + margin)
    speech_height = 40
    margin = 20
    d20_available_height = height - speech_height - margin
    
    # Load d20 SVG
    d20_path = Path(__file__).parent.parent.parent / "assets" / "images" / "d20.svg"
    if d20_path.exists():
        d20_surface = load_icon(d20_path, (width, d20_available_height), fill_color=primary_color)
        if d20_surface:
            # Center the d20 horizontally at top of container
            d20_rect = d20_surface.get_rect()
            d20_x = x + (width - d20_rect.width) // 2
            d20_y = y
            surface.blit(d20_surface, (d20_x, d20_y))
            
            # Draw speech_synthesizer below d20 with 30px margin
            speech_y = d20_y + d20_rect.height + margin
            speech_path = Path(__file__).parent.parent.parent / "assets" / "images" / "speech_synthesizer.svg"
            if speech_path.exists():
                speech_surface = load_icon(speech_path, (width, speech_height), fill_color=dim_color)
                if speech_surface:
                    speech_rect = speech_surface.get_rect()
                    speech_x = x + (width - speech_rect.width) // 2
                    surface.blit(speech_surface, (speech_x, speech_y))
        else:
            print(f"Warning: Failed to load d20 from {d20_path}")
    else:
        print(f"Warning: d20 not found at {d20_path}")
    
    return pygame.Rect(x, y, width, height)


def draw_now_playing(surface: Surface, x: int, y: int, width: int,
                     title: str = "NOW PLAYING",
                     line1: str = "",
                     line2: str = "",
                     theme: dict = None,
                     border_y: int = None) -> pygame.Rect:
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
    
    Returns:
        pygame.Rect of the entire component
    """
    from theme_loader import get_theme_loader
    
    # Load theme if not provided
    if theme is None:
        theme_loader = get_theme_loader()
        style = theme_loader.load_style('pipboy')
    else:
        style = theme.get('style', theme)
    
    # Colors
    title_color = tuple(style['colors'].get('primary', (233, 30, 99)))
    bg_color_hex = "#1797CD"
    # Convert hex to RGB with 33% alpha
    bg_r = int(bg_color_hex[1:3], 16)
    bg_g = int(bg_color_hex[3:5], 16)
    bg_b = int(bg_color_hex[5:7], 16)
    bg_alpha = int(255 * 0.33)
    
    # Border
    border_width = 6
    border_color = title_color
    
    # Fonts
    # Title: Compadre Extended (label_font), label size (16)
    title_font_path = Path(__file__).parent.parent.parent / "assets" / "fonts" / "Compadre-Extended.otf"
    title_font_size = style['typography']['fonts'].get('label', 16)
    title_font = pygame.font.Font(str(title_font_path), title_font_size)
    
    # Line 1: IBM Plex Mono Italic, body size (48)
    line1_font_path = Path(__file__).parent.parent.parent / "assets" / "fonts" / "IBMPlexMono-Italic.ttf"
    line1_font_size = style['typography']['fonts'].get('body', 48)
    line1_font = pygame.font.Font(str(line1_font_path), line1_font_size)
    
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
    
    # Truncate text if needed to fit within max width
    def truncate_text(font, text, max_width):
        if not text:
            return text
        rendered = font.render(text, True, title_color)
        if rendered.get_width() <= max_width:
            return text
        # Truncate with ellipsis
        while text and font.render(text + "...", True, title_color).get_width() > max_width:
            text = text[:-1]
        return text + "..."
    
    line1_text = truncate_text(line1_font, line1, max_text_width) if line1 else ""
    
    # Render body line
    line1_surface = line1_font.render(line1_text, True, title_color) if line1_text else None
    
    # Calculate content height
    content_height = padding  # Top padding
    if line1_surface:
        content_height += line1_surface.get_height()
    content_height += padding - 28  # Bottom padding (reduced by 28px)
    
    # Total component height
    total_height = (calculated_border_y - title_y) + border_width + content_height
    
    # Draw background box (with alpha) - 40px narrower from right
    bg_surface = pygame.Surface((bg_width, content_height), pygame.SRCALPHA)
    bg_surface.fill((bg_r, bg_g, bg_b, bg_alpha))
    surface.blit(bg_surface, (x, content_y))
    
    # Draw border (solid line)
    pygame.draw.rect(surface, border_color, (x, calculated_border_y, width, border_width), 0)
    
    # Draw title
    surface.blit(title_surface, (x, title_y))
    
    # Draw body lines (add 10px extra padding at top)
    text_x = x + padding
    text_y = content_y + 10
    
    if line1_surface:
        surface.blit(line1_surface, (text_x, text_y))
    
    # Draw circle element (80x80px) aligned with border
    circle_size = 80
    circle_border = 6
    circle_x = x + width - (circle_size // 2)  # Right edge, half overlapping
    circle_y = calculated_border_y - (circle_size // 2) + (border_width // 2) + 40  # Centered on border, moved down 40px
    
    # Draw outer circle (border)
    pygame.draw.circle(surface, border_color, (circle_x, circle_y), circle_size // 2, 0)
    
    # Draw inner circle (background fill)
    bg_color_solid = tuple(style['colors'].get('background', (0, 0, 0)))
    inner_radius = (circle_size // 2) - circle_border
    pygame.draw.circle(surface, bg_color_solid, (circle_x, circle_y), inner_radius, 0)
    
    # Load and draw SVG icon (40x40px)
    icon_path = Path(__file__).parent.parent.parent / "assets" / "images" / "icon_happysad.svg"
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