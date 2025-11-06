#!/usr/bin/env python3
import pygame
from scenes.scene_manager import Scene, register_scene
from utils import draw_scanlines, draw_footer, draw_back_arrow
from routing.intent_router import Intents
from visualizers import LissajousVisualizer


@register_scene("Experience1LissajousScene")
class Experience1LissajousScene(Scene):
    """Lissajous parametric curve visualizer scene."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        
        # Load theme colors
        from core.theme_loader import get_theme_loader
        theme_loader = get_theme_loader()
        style = theme_loader.load_style('pipboy')
        
        self.color = tuple(style['colors']['primary'])
        self.bg = tuple(style['colors']['background'])
        self.visualizer = None
        self.back_arrow_rect = None
    
    def on_enter(self):
        """Initialize Lissajous scene."""
        # Color already loaded from theme in __init__
        
        # Create visualizer with config
        self.visualizer = LissajousVisualizer(self.manager.config)
    
    def on_exit(self):
        """Clean up scene."""
        self.visualizer = None
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        # Check settings click first
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.settings_rect and self.settings_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intents.GO_TO_SETTINGS)
                return True
        return self.handle_common_events(event, Intents.GO_BACK, self.back_arrow_rect)
    
    def update(self, dt: float):
        """Update visualization."""
        if self.visualizer:
            # Get FFT data from audio system
            audio_data = {}
            if hasattr(self.ctx, 'audio') and self.ctx.audio:
                audio_data['fft'] = self.ctx.audio.get_fft_bins()
            
            self.visualizer.update(audio_data, dt)
    
    def draw(self, screen: pygame.Surface):
        """Draw the scene."""
        screen.fill(self.bg)
        
        # Draw visualizer
        if self.visualizer:
            self.visualizer.draw(screen)
        
        # Draw UI overlays
        self.back_arrow_rect = draw_back_arrow(screen, self.color)
        draw_scanlines(screen)
        self.settings_rect = draw_footer(screen, self.color)