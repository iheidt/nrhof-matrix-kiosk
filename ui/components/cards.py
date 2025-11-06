#!/usr/bin/env python3
"""Card components - basic cards and title cards."""
import pygame
from pygame import Surface

# Import from parent ui modules  
from ..fonts import get_localized_font


def draw_card(surface: Surface, x: int, y: int, width: int, height: int, theme: dict = None,
             border_solid: str = None, border_fade_pct: float = None, border_height_pct: float = None):
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
        border_height_pct: Override for left/right border height as percentage of card height (0.0-1.0)
    
    Returns:
        Rect of the card's content area (inside padding)
    """
    from core.theme_loader import get_theme_loader
    
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
    if border_height_pct is None:
        border_height_pct = card_settings.get('border_height_pct', 1.0)  # 0.0-1.0, default full height
    
    # Get border color from style
    border_color_name = card_settings.get('border_color', 'primary')
    border_color = tuple(theme['style']['colors'][border_color_name])
    
    # Draw card border with gradient fade
    if border_fade_pct > 0:
        _draw_card_border_with_fade(surface, x, y, width, height, border_width, 
                                   border_color, border_solid, border_fade_pct, border_height_pct)
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
                                border_width: int, color: tuple, solid_side: str, fade_pct: float,
                                border_height_pct: float = 1.0):
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
    
    # Calculate effective height for left/right borders
    effective_height = int(height * border_height_pct)
    
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
        fade_start = int(height * fade_pct)
        
        # Draw each horizontal line with appropriate alpha
        for i in range(height + border_width):
            if i < fade_start:
                # Fading portion at top
                progress = i / fade_start if fade_start > 0 else 0
                alpha = int(255 * progress)
            else:
                # Solid portion at bottom
                alpha = 255
            
            # Skip top border entirely (it would be transparent anyway)
            if i < border_width:
                pass
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
        # Top is solid, left/right fade down starting at (1.0 - fade_pct) of effective height
        # For example, with fade_pct=0.1, solid until 90% of effective height, then fade over last 10%
        fade_start = int(effective_height * (1.0 - fade_pct))  # Start fading at this height
        fade_distance = effective_height - fade_start  # Distance over which to fade
        
        # Set alpha channel using surfarray
        for i in range(effective_height + border_width):
            # Calculate alpha based on position
            if i < fade_start:
                # Solid portion (top to fade_start)
                alpha = 255
            elif i < effective_height:
                # Fading portion (fade_start to effective_height)
                progress = (i - fade_start) / fade_distance if fade_distance > 0 else 1
                alpha = max(0, int(255 * (1.0 - progress)))
            else:
                # Below effective height - transparent
                alpha = 0
            
            # Top border (always solid)
            if i < border_width:
                pixels_rgb[:, i] = base_color
                pixels_alpha[:, i] = 255
            else:
                # Left border (with fade)
                if alpha > 0:
                    pixels_rgb[0:border_width, i] = base_color
                    pixels_alpha[0:border_width, i] = alpha
                # Right border (with fade)
                if alpha > 0:
                    pixels_rgb[width + border_width:width + border_width * 2, i] = base_color
                    pixels_alpha[width + border_width:width + border_width * 2, i] = alpha
                # No bottom border - removed entirely
    
    # Release the pixel array locks
    del pixels_rgb
    del pixels_alpha
    
    # Blit the border surface onto the main surface
    surface.blit(border_surface, (x - border_width, y - border_width))


def draw_title_card(surface: Surface, x: int, y: int, width: int, height: int, title: str,
                    theme: dict = None, **overrides) -> pygame.Rect:
    """Draw a card with title overlaying the top border.
    
    Args:
        surface: Pygame surface to draw on
        x, y: Card position (top-left)
        width, height: Card dimensions
        title: Title text to display
        theme: Dict with 'layout' and 'style' keys
        **overrides: Override any card settings
    
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
    
    # Get card config
    card_config = layout.get('card', {})
    border_width = overrides.get('border', card_config.get('border', 6))
    padding = overrides.get('padding', card_config.get('padding', 24))
    border_fade_pct = overrides.get('border_fade_pct', card_config.get('border_fade_pct', 0.33))
    
    # Colors
    border_color_key = overrides.get('border_color', card_config.get('border_color', 'primary'))
    border_color = tuple(style['colors'].get(border_color_key, style['colors']['primary']))
    
    # Title font - always uses 'title' size and 'miland' (secondary) font
    # Use localized font for Japanese support
    from ..fonts import get_theme_font, render_mixed_text
    from core.localization import get_language
    
    title_font_size = style['typography']['fonts'].get('title', 76)
    
    # Render title with mixed fonts (numbers use English, Japanese uses localized)
    title_surface = render_mixed_text(title, title_font_size, 'secondary', border_color)
    title_width = title_surface.get_width()
    title_height = title_surface.get_height()
    
    # Always use ENGLISH font height for consistent border positioning
    english_font = get_theme_font(title_font_size, 'secondary')
    english_surface = english_font.render('A', True, border_color)
    english_height = english_surface.get_height()
    
    # Calculate overlap based on English font height (keeps border position fixed)
    title_overlap = english_height // 2
    
    # For Japanese, adjust Y position upward to compensate for taller font
    current_lang = get_language()
    if current_lang == 'jp':
        # Move Japanese title up by the difference in heights to align better
        height_diff = title_height - english_height
        title_y_offset = -(height_diff // 2 + 13)  # Extra 26px adjustment for better alignment
    else:
        title_y_offset = 0
    
    # Adjust card top padding to accommodate title overlap
    adjusted_top_padding = padding + title_overlap
    
    # Draw card border with fade (top solid, bottom/sides fade)
    draw_card(surface, x, y, width, height, theme=theme, 
              border_solid='top', border_fade_pct=border_fade_pct)
    
    # Calculate title position
    title_x = x + 35 + 24  # 35px border + 24px gap from left edge
    title_y = y - title_overlap + title_y_offset  # Centered on top border, adjusted for Japanese
    
    # Draw background behind title to create gaps (erase the border)
    bg_color = tuple(style['colors']['background'])
    gap_rect = pygame.Rect(x + 35, y - border_width, title_width + 48, border_width * 2)
    pygame.draw.rect(surface, bg_color, gap_rect, 0)
    
    # Draw the title
    surface.blit(title_surface, (title_x, title_y))
    
    # Return content rect (accounting for adjusted top padding)
    content_x = x + border_width + padding
    content_y = y + border_width + adjusted_top_padding
    content_width = width - (border_width + padding) * 2
    content_height = height - border_width - adjusted_top_padding - padding - border_width
    
    return pygame.Rect(content_x, content_y, content_width, content_height)


def draw_title_card_container(surface: Surface, x: int, y: int, width: int, height: int, title: str,
                              theme: dict = None, **overrides) -> dict:
    """Draw a full-width title card container for 1-column layouts.
    
    This is designed for the new full-width layout pattern with:
    - Title overlapping top border
    - 50px margin below title
    - Content area for tabs and other elements
    - 30px spacing between elements inside
    
    Args:
        surface: Pygame surface to draw on
        x, y: Card position (top-left)
        width, height: Card dimensions
        title: Title text to display
        theme: Dict with 'layout' and 'style' keys
        **overrides: Override any card settings
    
    Returns:
        dict with layout information:
            - 'card_rect': pygame.Rect of the full card
            - 'content_rect': pygame.Rect of content area (after title + 50px margin)
            - 'title_bottom_y': Y position where title ends
            - 'tabs_y': Y position where tabs should be drawn (title_bottom + 50px)
            - 'content_start_y': Y position where main content starts (tabs + 37px + 50px)
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
    
    # Move entire card up 21px when in Japanese mode (card-level adjustment)
    from core.localization import get_language
    if get_language() == 'jp':
        y -= 21
    
    # Get card config
    card_config = layout.get('card', {})
    border_width = overrides.get('border', card_config.get('border', 6))
    padding = overrides.get('padding', card_config.get('padding', 24))
    border_fade_pct = overrides.get('border_fade_pct', card_config.get('border_fade_pct', 0.33))
    border_height_pct = overrides.get('border_height_pct', card_config.get('border_height_pct', 1.0))
    
    # Colors
    border_color_key = overrides.get('border_color', card_config.get('border_color', 'primary'))
    border_color = tuple(style['colors'].get(border_color_key, style['colors']['primary']))
    
    # Title font
    from ..fonts import get_theme_font, render_mixed_text
    from core.localization import get_language
    
    title_font_size = style['typography']['fonts'].get('title', 76)
    
    # Render title with mixed fonts
    title_surface = render_mixed_text(title, title_font_size, 'secondary', border_color)
    title_width = title_surface.get_width()
    title_height = title_surface.get_height()
    
    # Always use ENGLISH font height for consistent border positioning
    english_font = get_theme_font(title_font_size, 'secondary')
    english_surface = english_font.render('A', True, border_color)
    english_height = english_surface.get_height()
    
    # Calculate overlap based on English font height
    title_overlap = english_height // 2
    
    # For Japanese, adjust title Y position based on height difference
    current_lang = get_language()
    if current_lang == 'jp':
        height_diff = title_height - english_height
        title_y_offset = -(height_diff // 2 + 13)
    else:
        title_y_offset = 0
    
    # Draw card border with fade
    draw_card(surface, x, y, width, height, theme=theme, 
              border_solid='top', border_fade_pct=border_fade_pct, border_height_pct=border_height_pct)
    
    # Calculate title position
    title_x = x + 35 + 24  # 35px border + 24px gap from left edge
    title_y = y - title_overlap + title_y_offset
    
    # Draw background behind title to create gaps
    bg_color = tuple(style['colors']['background'])
    gap_rect = pygame.Rect(x + 35, y - border_width, title_width + 48, border_width * 2)
    pygame.draw.rect(surface, bg_color, gap_rect, 0)
    
    # Draw the title
    surface.blit(title_surface, (title_x, title_y))
    
    # Calculate layout positions
    # Use ENGLISH font height and base position (before title_y_offset) for consistent spacing
    # This prevents the content from shifting when switching to Japanese
    title_visual_bottom_y = (y - title_overlap) + english_height
    
    # Tabs should be exactly 50px from the visual bottom of the title text
    # Subtract 28px to correct for the excess space identified in feedback
    tabs_y = title_visual_bottom_y + 50 - 28  # 50px margin minus 28px excess
    
    # Content starts after tabs + 50px margin
    # Tabs use 48px font (body size) but have 37px line height
    # We need to measure from the visual bottom of the tab text (48px) + 50px margin
    tab_font_size = 48  # Body size from pipboy.yaml
    content_start_y = tabs_y + tab_font_size + 50  # 48px tab font + 50px margin
    
    # Content area inside the card (with padding)
    content_x = x + border_width + padding
    content_y = y + border_width + padding
    content_width = width - (border_width + padding) * 2
    content_height = height - (border_width + padding) * 2
    
    return {
        'card_rect': pygame.Rect(x, y, width, height),
        'content_rect': pygame.Rect(content_x, content_y, content_width, content_height),
        'title_bottom_y': title_visual_bottom_y,
        'tabs_y': tabs_y,
        'content_start_y': content_start_y,
        'padding': padding,
        'border_width': border_width,
    }