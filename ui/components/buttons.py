#!/usr/bin/env python3
"""Button components."""
import pygame
from pygame import Surface

# Import from parent ui modules
from ..fonts import get_localized_font, render_mixed_text


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
    
    # Font - use localized font for Japanese support
    font_size_key = overrides.get('font_size', button_config.get('font_size', 'body'))
    # If font_size_key is already an integer, use it directly; otherwise look it up
    if isinstance(font_size_key, int):
        font_size = font_size_key
    else:
        font_size = style['typography']['fonts'].get(font_size_key, 24)
    
    # Calculate button height based on ENGLISH font height for consistent sizing
    from ..fonts import get_theme_font
    english_font = get_theme_font(font_size, 'primary')
    english_text_surface = english_font.render('A', True, font_color)  # Use 'A' as reference
    button_height = english_text_surface.get_height() + (padding * 2)
    
    # Render actual text with mixed fonts (numbers use English, Japanese uses localized)
    text_surface = render_mixed_text(text, font_size, 'primary', font_color)
    
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
    text_y = y + (button_height - text_surface.get_height()) // 2
    surface.blit(text_surface, (text_x, text_y))
    
    # Return content rect (for click detection, etc.)
    return pygame.Rect(x, y, button_width, button_height)


def draw_toggle_button(surface: Surface, x: int, y: int, width: int, 
                       left_text: str, right_text: str, selected: str,
                       theme: dict = None, **overrides) -> tuple:
    """Draw a two-state toggle button.
    
    Args:
        surface: Pygame surface to draw on
        x, y: Button position (top-left)
        width: Total width of toggle button
        left_text: Text for left option
        right_text: Text for right option
        selected: Which side is selected ('left' or 'right')
        theme: Dict with 'layout' and 'style' keys
        **overrides: Override any button settings
    
    Returns:
        tuple: (left_rect, right_rect) for click detection
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
    
    # Dimensions
    border_width = overrides.get('border', button_config.get('border', 6))
    padding = overrides.get('padding', button_config.get('padding', 24))
    
    # Colors
    primary_color = tuple(style['colors']['primary'])
    bg_color = tuple(style['colors']['background'])
    
    # Font - use localized font for Japanese support
    from ui.fonts import get_localized_font, get_theme_font, render_mixed_text
    font_size_key = overrides.get('font_size', button_config.get('font_size', 'body'))
    if isinstance(font_size_key, int):
        font_size = font_size_key
    else:
        font_size = style['typography']['fonts'].get(font_size_key, 24)
    
    # Calculate height based on ENGLISH font height for consistent sizing
    english_font = get_theme_font(font_size, 'primary')
    english_text_surface = english_font.render('A', True, primary_color)
    button_height = english_text_surface.get_height() + (padding * 2)
    
    # Each half is 50% of total width
    half_width = width // 2
    
    # Draw left side
    left_rect = pygame.Rect(x, y, half_width, button_height)
    if selected == 'left':
        # Selected: pink fill, black text
        pygame.draw.rect(surface, primary_color, left_rect)
        pygame.draw.rect(surface, primary_color, left_rect, border_width)
        text_color = bg_color
    else:
        # Unselected: black background, pink border and text
        pygame.draw.rect(surface, bg_color, left_rect)
        pygame.draw.rect(surface, primary_color, left_rect, border_width)
        text_color = primary_color
    
    # Draw left text (centered) with mixed fonts
    left_text_surf = render_mixed_text(left_text, font_size, 'primary', text_color)
    left_text_x = left_rect.centerx - left_text_surf.get_width() // 2
    left_text_y = left_rect.centery - left_text_surf.get_height() // 2
    surface.blit(left_text_surf, (left_text_x, left_text_y))
    
    # Draw right side
    right_rect = pygame.Rect(x + half_width, y, half_width, button_height)
    if selected == 'right':
        # Selected: pink fill, black text
        pygame.draw.rect(surface, primary_color, right_rect)
        pygame.draw.rect(surface, primary_color, right_rect, border_width)
        text_color = bg_color
    else:
        # Unselected: black background, pink border and text
        pygame.draw.rect(surface, bg_color, right_rect)
        pygame.draw.rect(surface, primary_color, right_rect, border_width)
        text_color = primary_color
    
    # Draw right text (centered) with mixed fonts
    right_text_surf = render_mixed_text(right_text, font_size, 'primary', text_color)
    right_text_x = right_rect.centerx - right_text_surf.get_width() // 2
    right_text_y = right_rect.centery - right_text_surf.get_height() // 2
    surface.blit(right_text_surf, (right_text_x, right_text_y))
    
    return (left_rect, right_rect)