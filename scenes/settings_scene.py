#!/usr/bin/env python3
import pygame
from scenes.scene_manager import Scene, register_scene
from utils import get_theme_font, draw_scanlines, draw_footer, MARGIN_TOP, MARGIN_LEFT
from routing.intent_router import Intents
from core.theme_loader import get_theme_loader


@register_scene("SettingsScene")
class SettingsScene(Scene):
    """Settings configuration scene."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        
        # Load theme
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme('settings', theme_name='pipboy')
        
        # Extract from theme
        self.color = tuple(self.theme['style']['colors']['primary'])
        self.bg = tuple(self.theme['style']['colors']['background'])
        
        # Layout vars
        self.nav_back_rect = None
    
    def on_enter(self):
        """Called when scene becomes active."""
        pass
    
    def on_exit(self):
        """Called when scene is about to be replaced."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle settings input."""
        # ESC or click nav_back to return to previous scene
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(Intents.GO_BACK)
                return True
            elif event.key == pygame.K_w:
                # Trigger wakeword for testing
                self.trigger_wakeword()
                return True
        
        # Click nav_back
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.nav_back_rect and self.nav_back_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intents.GO_BACK)
                return True
        
        return False
    
    def update(self, dt: float):
        """Update settings state."""
        pass
    
    def draw(self, screen: pygame.Surface):
        """Draw settings screen."""
        # Clear screen
        screen.fill(self.bg)
        w, h = screen.get_size()
        
        # Get style
        style = self.theme['style']
        
        # Draw nav_back component ("<esc" in top-left corner at margin boundary)
        # Use micro size (24px) from pipboy.yaml
        nav_back_font = get_theme_font(style['typography']['fonts']['micro'], 'primary')  # IBM Plex Mono 24px
        nav_back_text = "<esc"
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
        
        # TODO: Add settings content here
        
        # Draw scanlines and footer
        draw_scanlines(screen)
        draw_footer(screen, self.color, show_settings=False)  # Hide settings when in settings