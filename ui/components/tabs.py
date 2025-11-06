#!/usr/bin/env python3
"""Tab navigation component."""

import pygame
from typing import List, Tuple, Optional
from ui.fonts import get_theme_font


def draw_tabs(
    surface: pygame.Surface,
    x: int,
    y: int,
    width: int,
    tabs: List[str],
    active_index: int = 0,
    color: Tuple[int, int, int] = (140, 255, 140),
    inactive_alpha: float = 0.5,
    font_size: int = 48  # Body size from pipboy.yaml
) -> List[pygame.Rect]:
    """Draw horizontal tab navigation.
    
    Args:
        surface: Surface to draw on
        x: X position
        y: Y position
        width: Total width available for tabs
        tabs: List of tab labels
        active_index: Index of the active tab
        color: Tab text color
        inactive_alpha: Alpha multiplier for inactive tabs (0.0-1.0)
        font_size: Font size for tabs (default 48 = body size from pipboy.yaml)
        
    Returns:
        List of pygame.Rect for each tab (for click detection)
    """
    TAB_HEIGHT = 37  # Line height for tabs
    TAB_SPACING = 50  # Space between tabs
    
    # Use IBM Plex Mono Italic for tabs at body size (48px)
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    italic_font_path = project_root / "assets" / "fonts" / "IBMPlexMono-Italic.ttf"
    
    if italic_font_path.exists():
        font = pygame.font.Font(str(italic_font_path), font_size)
    else:
        # Fallback to regular mono font
        from ui.fonts import get_font
        font = get_font(font_size, mono=True, bold=False)
    
    tab_rects = []
    current_x = x
    
    for i, tab_text in enumerate(tabs):
        # Determine color based on active state
        if i == active_index:
            tab_color = color
        else:
            # Dim inactive tabs
            tab_color = tuple(int(c * inactive_alpha) for c in color)
        
        # Render tab text
        # Use line height of 37px to allow font to extend naturally
        text_surface = font.render(tab_text, True, tab_color)
        
        # Draw text
        surface.blit(text_surface, (current_x, y))
        
        # Store rect for click detection
        tab_rect = pygame.Rect(
            current_x,
            y,
            text_surface.get_width(),
            TAB_HEIGHT
        )
        tab_rects.append(tab_rect)
        
        # Move to next tab position
        current_x += text_surface.get_width() + TAB_SPACING
    
    return tab_rects


__all__ = ['draw_tabs']