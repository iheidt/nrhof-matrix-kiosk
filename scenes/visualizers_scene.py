#!/usr/bin/env python3
import pygame
from scenes.scene_manager import Scene, register_scene
from ui.components import (
    draw_scanlines, draw_footer, draw_title_card_container,
    MARGIN_TOP, MARGIN_LEFT, MARGIN_RIGHT
)
from ui.fonts import get_localized_font
from routing.intent_router import Intent
from core.theme_loader import get_theme_loader

# Visualizers will be added here later


@register_scene("VisualizersScene")
class VisualizersScene(Scene):
    """Visualizers hub scene."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        
        # Load theme
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme('visualizers', theme_name='pipboy')
        
        # Extract from theme
        self.color = tuple(self.theme['style']['colors']['primary'])
        self.bg = tuple(self.theme['style']['colors']['background'])
        
        # Layout vars
        self.nav_back_rect = None
        self.settings_rect = None  # Store settings text rect for click detection
    
    def on_enter(self):
        """Called when scene becomes active."""
        pass
    
    
    def on_exit(self):
        """Called when scene is about to be replaced."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle visualizers input."""
        # ESC key to return to previous scene
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
        
        # Handle mouse clicks
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check nav_back click
            if self.nav_back_rect and self.nav_back_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
            # Check settings click
            if self.settings_rect and self.settings_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_TO_SETTINGS)
                return True
        
        return False
    
    def update(self, dt: float):
        """Update visualizer state."""
        pass
    
    def draw(self, screen: pygame.Surface):
        """Draw visualizers screen."""
        # Clear screen
        screen.fill(self.bg)
        w, h = screen.get_size()
        
        # Get style and layout
        style = self.theme['style']
        layout = self.theme_loader.load_layout('menu')  # Use menu layout for margins
        
        # Get margins
        margins = layout.get('margins', {})
        margin_left = margins.get('left', MARGIN_LEFT)
        margin_right = margins.get('right', MARGIN_RIGHT)
        
        # Draw nav_back component ("<esc" in top-left corner at margin boundary)
        from core.localization import t
        nav_back_text = t('common.esc')
        nav_back_font = get_localized_font(style['typography']['fonts']['micro'], 'primary', nav_back_text)
        nav_back_surface = nav_back_font.render(nav_back_text, True, self.color)
        nav_back_x = MARGIN_LEFT
        nav_back_y = MARGIN_TOP
        screen.blit(nav_back_surface, (nav_back_x, nav_back_y))
        
        # Store rect for click detection
        self.nav_back_rect = pygame.Rect(
            nav_back_x,
            nav_back_y,
            nav_back_surface.get_width(),
            nav_back_surface.get_height()
        )
        
        # Calculate title card position (20px below nav_back)
        title_card_y = nav_back_y + nav_back_surface.get_height() + 20
        title_card_width = w - margin_left - margin_right
        
        # Calculate card height to fill remaining space (minus footer)
        footer_height = 130
        title_card_height = h - title_card_y - margin_left - footer_height  # Use margin_left as bottom margin (50px)
        
        # Get title card border settings from layout
        title_card_config = layout.get('title_card', {})
        border_fade_pct = title_card_config.get('border_fade_pct', 0.9)
        border_height_pct = title_card_config.get('border_height_pct', 0.15)
        
        # Get title font to calculate overlap
        title_text = t('visualizers.title')
        title_font_size = style['typography']['fonts'].get('title', 76)
        title_font = get_localized_font(title_font_size, 'secondary', title_text)
        title_surface = title_font.render(title_text, True, (255, 255, 255))
        title_overlap = title_surface.get_height() // 2
        
        # Adjust y position so title overlaps card border
        title_card_y_adjusted = title_card_y + title_overlap
        
        # Move entire card up 21px when in Japanese mode
        from core.localization import get_language
        if get_language() == 'jp':
            title_card_y_adjusted -= 21
        
        # Draw the full-width title card container
        layout_info = draw_title_card_container(
            surface=screen,
            x=margin_left,
            y=title_card_y_adjusted,
            width=title_card_width,
            height=title_card_height,
            title=title_text,
            theme={'layout': layout, 'style': style},
            border_fade_pct=border_fade_pct,
            border_height_pct=border_height_pct
        )
        
        # Content area for future visualizers
        content_y = layout_info['content_start_y']
        content_x = margin_left
        content_width = title_card_width
        content_height = h - content_y - 130  # Subtract footer height
        
        # Visualizers will be drawn here later
        
        # Draw scanlines and footer
        draw_scanlines(screen)
        self.settings_rect = draw_footer(screen, self.color, show_settings=True)