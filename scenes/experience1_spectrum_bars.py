#!/usr/bin/env python3
import numpy as np
import pygame
from scene_manager import BaseAudioScene, register_scene
from utils import draw_scanlines, draw_footer, draw_back_arrow, get_matrix_green
from intent_router import Intents
from visualizers import SpectrumBarsVisualizer


@register_scene("Experience1SpectrumBarsScene")
class Experience1SpectrumBarsScene(BaseAudioScene):
    """Spectrum bars visualizer scene."""
    
    def __init__(self, ctx):
        # Initialize with smaller FFT size for spectrum bars
        super().__init__(ctx, sample_rate=44100, fft_size=256)
        
        self.color = (140, 255, 140)
        self.bg = (0, 0, 0)
        self.visualizer = None
    
    def on_enter(self):
        """Initialize audio visualization."""
        self.color = get_matrix_green(self.manager.config)
        
        # Create visualizer
        self.visualizer = SpectrumBarsVisualizer(self.manager.config)
        
        # Start audio stream (from BaseAudioScene)
        self.start_audio_stream()
    
    def on_exit(self):
        """Clean up scene."""
        self.stop_audio_stream()
        self.visualizer = None
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        return self.handle_common_events(event, Intents.GO_TO_EXPERIENCE1_HUB, self.back_arrow_rect)
    
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
        """Draw the scene."""
        screen.fill(self.bg)
        
        # Draw visualizer
        if self.visualizer:
            self.visualizer.draw(screen)
        
        # Draw UI overlays
        self.back_arrow_rect = draw_back_arrow(screen, self.color)
        draw_scanlines(screen)
        draw_footer(screen, self.color)
