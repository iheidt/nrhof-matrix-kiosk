#!/usr/bin/env python3
import numpy as np
import pygame
from scene_manager import BaseAudioScene, register_scene
from utils import draw_scanlines, draw_footer, draw_back_arrow, get_matrix_green
from intent_router import Intents
from visualizers import WaveformVisualizer


@register_scene("Experience1WaveformScene")
class Experience1WaveformScene(BaseAudioScene):
    """Waveform visualizer scene."""
    
    def __init__(self, ctx):
        # Initialize with default audio settings
        super().__init__(ctx, sample_rate=44100, fft_size=1024)
        
        self.color = (140, 255, 140)
        self.bg = (0, 0, 0)
        self.visualizer = None
    
    def on_enter(self):
        """Start audio capture."""
        self.color = get_matrix_green(self.manager.config)
        
        # Create visualizer
        self.visualizer = WaveformVisualizer(self.manager.config)
        
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
        
        if self.visualizer:
            audio_data = {}
            
            if len(self.audio_buffer) >= self.fft_size:
                # Check if there's actual audio signal (not just noise)
                rms = np.sqrt(np.mean(self.audio_buffer ** 2))
                
                if rms > 0.001:  # Noise threshold
                    # Perform FFT for frequency bands
                    fft_data = np.fft.rfft(self.audio_buffer)
                    magnitudes = np.abs(fft_data)
                    
                    # Normalize
                    magnitudes = np.maximum(magnitudes, 1e-10)
                    normalized = magnitudes / np.max(magnitudes) if np.max(magnitudes) > 0 else magnitudes
                    
                    audio_data['fft'] = normalized
            
            # Update visualizer (with or without FFT data)
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
