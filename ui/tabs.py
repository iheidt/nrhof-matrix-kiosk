#!/usr/bin/env python3
"""Minimal tabs component."""

import pygame
from typing import List, Tuple
from pathlib import Path


class Tabs:
    """Simple tabs component that manages tab state and rendering."""
    
    def __init__(self, labels: List[str], color: Tuple[int, int, int]):
        """Initialize tabs.
        
        Args:
            labels: List of tab label strings
            color: RGB color tuple
        """
        self.labels = labels
        self.color = color
        self.active_index = 0
        
        # Get body font size from theme
        from core.theme_loader import get_theme_loader
        from core.localization import get_language
        theme_loader = get_theme_loader()
        style = theme_loader.load_style('pipboy')
        font_size = style['typography']['fonts'].get('body', 48)
        
        # Font substitution: use Japanese font for Japanese, IBM Plex Mono Italic for English
        project_root = Path(__file__).parent.parent
        current_lang = get_language()
        if current_lang == 'jp':
            # Use Noto Sans JP Regular for Japanese (maps from IBM Plex Mono Italic)
            font_path = project_root / "assets" / "fonts" / "NotoSansJP-Regular.ttf"
        else:
            # Use IBM Plex Mono Italic for English
            font_path = project_root / "assets" / "fonts" / "IBMPlexMono-Italic.ttf"
        self.font = pygame.font.Font(str(font_path), font_size)
        
        # Pre-render all tab surfaces once
        self.active_surfaces = []
        self.inactive_surfaces = []
        
        for label in labels:
            # Active tab: full color
            self.active_surfaces.append(self.font.render(label, True, color))
            # Inactive tab: 50% dimmed
            dim_color = tuple(int(c * 0.5) for c in color)
            self.inactive_surfaces.append(self.font.render(label, True, dim_color))
        
        # Calculate tab positions
        self.tab_rects = []
    
    def set_active(self, index: int):
        """Set the active tab index."""
        if 0 <= index < len(self.labels):
            self.active_index = index
    
    def draw(self, surface: pygame.Surface, x: int, y: int) -> List[pygame.Rect]:
        """Draw tabs and return clickable rects.
        
        Args:
            surface: Surface to draw on
            x: X position
            y: Y position
            
        Returns:
            List of pygame.Rect for click detection
        """
        self.tab_rects = []
        current_x = x
        spacing = 50
        
        for i in range(len(self.labels)):
            # Choose pre-rendered surface
            if i == self.active_index:
                tab_surface = self.active_surfaces[i]
            else:
                tab_surface = self.inactive_surfaces[i]
            
            # Draw
            surface.blit(tab_surface, (current_x, y))
            
            # Store rect
            rect = pygame.Rect(current_x, y, tab_surface.get_width(), tab_surface.get_height())
            self.tab_rects.append(rect)
            
            # Move to next position
            current_x += tab_surface.get_width() + spacing
        
        return self.tab_rects
    
    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """Check if click hit a tab and update active index.
        
        Args:
            pos: Mouse position (x, y)
            
        Returns:
            True if a tab was clicked
        """
        for i, rect in enumerate(self.tab_rects):
            if rect.collidepoint(pos):
                self.active_index = i
                return True
        return False


__all__ = ['Tabs']