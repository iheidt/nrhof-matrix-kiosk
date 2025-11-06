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


@register_scene("NR38Scene")
class NR38Scene(Scene):
    """NR-38 scene."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        
        # Load theme
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme('nr38', theme_name='pipboy')
        
        # Extract from theme
        self.color = tuple(self.theme['style']['colors']['primary'])
        self.bg = tuple(self.theme['style']['colors']['background'])
        
        # Layout vars
        self.nav_back_rect = None
        self.settings_rect = None  # Store settings text rect for click detection
        
        # Cache rendered surfaces to prevent re-rendering every frame
        self._nav_back_surface = None
        self._title_surface = None
        self._title_overlap = None
        self._cached_language = None  # Track language for cache invalidation
    
    def on_enter(self):
        """Called when scene becomes active."""
        pass
    
    def on_exit(self):
        """Called when scene is about to be replaced."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle NR-38 input."""
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
        """Update NR-38 state."""
        pass
    
    def draw(self, screen: pygame.Surface):
        """Draw NR-38 screen."""
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
        # Cache to prevent re-rendering every frame
        from core.localization import t, get_language
        current_language = get_language()
        if self._nav_back_surface is None or self._cached_language != current_language:
            nav_back_text = t('common.esc')
            nav_back_font = get_localized_font(style['typography']['fonts']['micro'], 'primary', nav_back_text)
            self._nav_back_surface = nav_back_font.render(nav_back_text, True, self.color)
            self._cached_language = current_language
        nav_back_x = MARGIN_LEFT
        nav_back_y = MARGIN_TOP
        screen.blit(self._nav_back_surface, (nav_back_x, nav_back_y))
        
        # Store rect for click detection
        self.nav_back_rect = pygame.Rect(
            nav_back_x,
            nav_back_y,
            self._nav_back_surface.get_width(),
            self._nav_back_surface.get_height()
        )
        
        # Calculate title card position (20px below nav_back)
        title_card_y = nav_back_y + self._nav_back_surface.get_height() + 20
        title_card_width = w - margin_left - margin_right
        
        # Calculate card height to fill remaining space (minus footer)
        footer_height = 130
        title_card_height = h - title_card_y - margin_left - footer_height  # Use margin_left as bottom margin (50px)
        
        # Get title card border settings from layout
        title_card_config = layout.get('title_card', {})
        border_fade_pct = title_card_config.get('border_fade_pct', 0.9)
        border_height_pct = title_card_config.get('border_height_pct', 0.15)
        
        # Get title font to calculate overlap (cached)
        if self._title_surface is None or self._cached_language != current_language:
            title_text = t('nr38.title')
            title_font_size = style['typography']['fonts'].get('title', 76)
            title_font = get_localized_font(title_font_size, 'secondary', title_text)
            self._title_surface = title_font.render(title_text, True, (255, 255, 255))
            self._title_overlap = self._title_surface.get_height() // 2
        title_text = t('nr38.title')  # Still need text for draw_title_card_container
        title_overlap = self._title_overlap
        
        # Adjust y position so title overlaps card border
        title_card_y_adjusted = title_card_y + title_overlap
        
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
        
        # Content area for NR-38
        content_y = layout_info['content_start_y']
        content_x = margin_left + 35 + 24  # Match title card padding
        content_width = title_card_width
        content_height = h - content_y - 130  # Subtract footer height
        
        # Draw placeholder content
        content_font = get_localized_font(36, 'primary', 'NR-38')
        content_surface = content_font.render('NR-38 Content Area', True, self.color)
        screen.blit(content_surface, (content_x, content_y + 30))
        
        # Draw scanlines and footer
        draw_scanlines(screen)
        self.settings_rect = draw_footer(screen, self.color, show_settings=True)