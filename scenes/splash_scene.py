#!/usr/bin/env python3
import time
import pygame
from scene_manager import Scene, register_scene
from utils import get_font, get_matrix_green


@register_scene("SplashScene")
class SplashScene(Scene):
    """Splash screen with loading progress."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        self.screen = ctx.scene_manager.screen if hasattr(ctx, 'scene_manager') else None
        self.progress = 0.0
        self._start = 0.0
        self._min_secs = ctx.config.get('splash_min_seconds', 1.0) if hasattr(ctx, 'config') else 1.0
        self.color = (140, 255, 140)
    
    def on_enter(self):
        """Initialize splash screen."""
        self._start = time.time()
        self.progress = 0.0
        self.color = get_matrix_green(self.manager.config)
    
    def on_exit(self):
        """Clean up splash screen."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        # No interaction during splash
        return False
    
    def update(self, dt: float):
        """Update splash screen progress."""
        # Read preload progress from app context
        if hasattr(self.ctx, 'preload_progress'):
            self.progress = self.ctx.preload_progress
        else:
            # Fallback: simulate progress
            self.progress = min(1.0, self.progress + dt * 0.5)
        
        # Check if loading is done and minimum time has elapsed
        elapsed = time.time() - self._start
        preload_done = getattr(self.ctx, 'preload_done', False)
        
        if (preload_done or self.progress >= 1.0) and elapsed >= self._min_secs:
            self.manager.switch_to('IntroScene')
    
    def draw(self, screen: pygame.Surface):
        """Draw splash screen."""
        # Black background
        screen.fill((0, 0, 0))
        
        w, h = screen.get_size()
        center_x = w // 2
        center_y = h // 2
        
        # Draw title
        title = self.manager.config.get('title', 'NRHOF kiosk')
        title_font = get_font(48, mono=True)
        title_surface = title_font.render(title, True, self.color)
        title_rect = title_surface.get_rect(center=(center_x, center_y - 60))
        screen.blit(title_surface, title_rect)
        
        # Draw "loading..." text
        loading_font = get_font(24, mono=True)
        loading_surface = loading_font.render('loading...', True, self.color)
        loading_rect = loading_surface.get_rect(center=(center_x, center_y + 20))
        screen.blit(loading_surface, loading_rect)
        
        # Draw progress bar
        bar_width = 400
        bar_height = 20
        bar_x = center_x - bar_width // 2
        bar_y = center_y + 60
        
        # Draw border
        border_color = tuple(int(c * 0.5) for c in self.color)
        pygame.draw.rect(screen, border_color, (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Draw filled progress
        fill_width = int(bar_width * self.progress)
        if fill_width > 0:
            pygame.draw.rect(screen, self.color, (bar_x + 2, bar_y + 2, fill_width - 4, bar_height - 4))