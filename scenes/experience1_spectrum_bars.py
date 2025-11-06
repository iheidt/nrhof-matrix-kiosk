#!/usr/bin/env python3
import numpy as np
import pygame
from scenes.scene_manager import BaseAudioScene, register_scene
from utils import draw_back_arrow, draw_scanlines, draw_footer
from routing.intent_router import Intent
from visualizers import SpectrumBarsVisualizer
from renderers import FrameState


@register_scene("Experience1SpectrumBarsScene")
class Experience1SpectrumBarsScene(BaseAudioScene):
    """Spectrum bars visualizer scene."""
    
    def __init__(self, ctx):
        # Initialize with smaller FFT size for spectrum bars
        super().__init__(ctx, sample_rate=44100, fft_size=256)
        
        # Load theme colors
        from core.theme_loader import get_theme_loader
        theme_loader = get_theme_loader()
        style = theme_loader.load_style('pipboy')
        
        self.color = tuple(style['colors']['primary'])
        self.bg = tuple(style['colors']['background'])
        self.visualizer = None
    
    def on_enter(self):
        """Initialize audio visualization."""
        # Color already loaded from theme in __init__
        
        # Create visualizer - pass visualizers config section
        viz_config = self.manager.config.get('visualizers', {}).get('spectrum_bars', {})
        self.visualizer = SpectrumBarsVisualizer(viz_config)
        
        # Start audio stream (from BaseAudioScene)
        self.start_audio_stream()
    
    def on_exit(self):
        """Clean up scene."""
        self.stop_audio_stream()
        self.visualizer = None
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        # Check settings click first
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.settings_rect and self.settings_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_TO_SETTINGS)
                return True
        return self.handle_common_events(event, Intent.GO_BACK, self.back_arrow_rect)
    
    def update(self, dt: float):
        """Update visualization."""
        # Update audio buffer from centralized source
        self.update_audio_buffer()
        
        if self.visualizer and len(self.audio_buffer) >= self.fft_size:
            # Perform FFT
            windowed = self.audio_buffer * np.hanning(self.fft_size)
            fft_data = np.fft.rfft(windowed)
            magnitudes = np.abs(fft_data[:self.fft_size // 2])
            
            # Normalize
            magnitudes = np.maximum(magnitudes, 1e-10)
            db_magnitudes = 20 * np.log10(magnitudes)
            normalized = np.clip((db_magnitudes + 60) / 60, 0, 1)
            
            # Update visualizer
            audio_data = {'fft': normalized}
            self.visualizer.update(audio_data, dt)
    
    def draw(self, screen: pygame.Surface):
        """Draw the scene using renderer abstraction."""
        # Always clear screen first
        screen.fill(self.bg)
        
        # Draw visualizer
        if self.visualizer:
            self.visualizer.draw(screen)
        
        # Draw UI overlays (still using utils for now)
        self.back_arrow_rect = draw_back_arrow(screen, self.color)
        draw_scanlines(screen)
        self.settings_rect = draw_footer(screen, self.color)
