#!/usr/bin/env python3
"""Layout components - navigation and footer."""
import pygame
from pygame import Surface
from pathlib import Path

# Import from parent ui modules
from ..fonts import get_theme_font


def draw_back_arrow(surface: Surface, color: tuple = (140, 255, 140)) -> pygame.Rect:
    """Draw a back arrow in the top-left corner.
    
    Args:
        surface: Pygame surface to draw on
        color: RGB color tuple for the arrow
        
    Returns:
        pygame.Rect: Clickable area for the back arrow
    """
    from utils import MARGIN_LEFT, MARGIN_TOP
    
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
    from ..components.cards import draw_card
    
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
    from localization import t
    primary_color = tuple(style['colors']['primary'])
    micro_size = style['typography']['fonts']['micro']
    settings_font = get_theme_font(micro_size, 'primary')
    settings_text = settings_font.render(t('footer.settings'), True, primary_color)
    surface.blit(settings_text, (content_rect.x, content_rect.y + (content_rect.height - settings_text.get_height()) // 2))
    
    # Draw version number (right aligned in card)
    dim_color_hex = style['colors'].get('dim', '#2C405B')
    if isinstance(dim_color_hex, str) and dim_color_hex.startswith('#'):
        dim_color = tuple(int(dim_color_hex[i:i+2], 16) for i in (1, 3, 5))
    else:
        dim_color = tuple(dim_color_hex) if isinstance(dim_color_hex, (list, tuple)) else (44, 64, 91)
    pico_size = style['typography']['fonts']['pico']
    version_font = get_theme_font(pico_size, 'primary')
    version_text = version_font.render(f"v{__version__}", True, dim_color)
    version_x = content_rect.x + content_rect.width - version_text.get_width()
    surface.blit(version_text, (version_x, content_rect.y + (content_rect.height - version_text.get_height()) // 2))
    
    # Draw company name div (50px tall, below card)
    div_y = card_y + card_height
    label_size = style['typography']['fonts']['label']
    company_font = get_theme_font(label_size, 'label')
    company_text = company_font.render(t('footer.company'), True, primary_color)
    company_x = (w - company_text.get_width()) // 2
    company_y = div_y + (div_height - company_text.get_height()) // 2
    surface.blit(company_text, (company_x, company_y))