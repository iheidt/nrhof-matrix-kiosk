#!/usr/bin/env python3
"""Button components."""
import pygame
from pygame import Surface

# Import from parent ui modules
from ..fonts import get_theme_font


def draw_button(surface: Surface, x: int, y: int, container_width: int, text: str, 
                theme: dict = None, **overrides) -> pygame.Rect:
    """Draw a button component with optional square adornment.
    
    Args:
        surface: Pygame surface to draw on
        x, y: Button position (top-left)
        container_width: Width of container (button width is % of this)
        text: Button text
        theme: Dict with 'layout' and 'style' keys
        **overrides: Override any button settings (width_pct, border, padding, etc.)
    
    Returns:
        pygame.Rect of the content area (inside border and padding)
    """
    from core.theme_loader import get_theme_loader
    
    # Load theme if not provided
    if theme is None:
        theme_loader = get_theme_loader()
        layout = theme_loader.load_layout('menu')
        style = theme_loader.load_style('pipboy')
        theme = {'layout': layout, 'style': style}
    else:
        layout = theme['layout']
        style = theme['style']
    
    # Get button config from layout
    button_config = layout.get('button', {})
    
    # Button dimensions
    width_pct = overrides.get('width_pct', button_config.get('width', '67%'))
    if isinstance(width_pct, str) and width_pct.endswith('%'):
        width_pct = float(width_pct.rstrip('%')) / 100.0
    button_width = int(container_width * width_pct)
    
    border_width = overrides.get('border', button_config.get('border', 6))
    padding = overrides.get('padding', button_config.get('padding', 24))
    
    # Colors
    border_color_key = overrides.get('border_color', button_config.get('border_color', 'primary'))
    border_color = tuple(style['colors'].get(border_color_key, style['colors']['primary']))
    
    font_color_key = overrides.get('font_color', button_config.get('font_color', 'primary'))
    font_color = tuple(style['colors'].get(font_color_key, style['colors']['primary']))
    
    bg_alpha = overrides.get('bg_alpha', button_config.get('bg_alpha', 0.33))
    
    # Adornment config
    adornment_config = button_config.get('adornment', {})
    adornment_type = overrides.get('adornment_type', adornment_config.get('type', 'square'))
    adornment_size = overrides.get('adornment_size', adornment_config.get('size', 25))
    adornment_margin = overrides.get('adornment_margin_left', adornment_config.get('margin_left', 18))
    adornment_color_key = overrides.get('adornment_color', adornment_config.get('color', 'primary'))
    adornment_color = tuple(style['colors'].get(adornment_color_key, style['colors']['primary']))
    
    # Font
    font_size_key = overrides.get('font_size', button_config.get('font_size', 'body'))
    # If font_size_key is already an integer, use it directly; otherwise look it up
    if isinstance(font_size_key, int):
        font_size = font_size_key
    else:
        font_size = style['typography']['fonts'].get(font_size_key, 24)
    font = get_theme_font(font_size, 'primary')
    
    # Calculate button height based on text + padding
    text_surface = font.render(text, True, font_color)
    button_height = text_surface.get_height() + (padding * 2)
    
    # Draw background with alpha
    bg_surface = pygame.Surface((button_width, button_height), pygame.SRCALPHA)
    bg_color = (0, 0, 0, int(255 * bg_alpha))
    bg_surface.fill(bg_color)
    surface.blit(bg_surface, (x, y))
    
    # Draw border
    pygame.draw.rect(surface, border_color, (x, y, button_width, button_height), border_width)
    
    # Draw square adornment (left side, outside button)
    if adornment_type == 'square':
        adornment_x = x - adornment_margin - adornment_size
        adornment_y = y + (button_height - adornment_size) // 2
        pygame.draw.rect(surface, adornment_color, 
                        (adornment_x, adornment_y, adornment_size, adornment_size), 0)
    
    # Draw text (centered vertically, left-aligned with padding)
    text_x = x + padding
    text_y = y + padding
    surface.blit(text_surface, (text_x, text_y))
    
    # Return content rect (for click detection, etc.)
    return pygame.Rect(x, y, button_width, button_height)