#!/usr/bin/env python3
import pygame
import numpy as np
from .base import Visualizer
from utils import MARGIN_TOP, MARGIN_LEFT, MARGIN_RIGHT, MARGIN_BOTTOM


class SpectrumBarsVisualizer(Visualizer):
    """FFT spectrum bars visualizer."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Read from config with defaults
        self.num_bins = config.get('spectrum_bars', 128)
        self.decay_rate = config.get('spectrum_decay', 0.85)
        self.bar_heights = [0] * self.num_bins
        self.bar_width = 10
        self.bar_spacing = 2
    
    def reset(self):
        """Reset visualizer state."""
        self.bar_heights = [0] * self.num_bins
    
    def update(self, audio_data: dict, dt: float):
        """Update spectrum bars based on FFT data."""
        fft_bins = audio_data.get('fft')
        
        if fft_bins is not None and len(fft_bins) > 0:
            # Resample FFT to match number of bars
            if len(fft_bins) != self.num_bins:
                indices = np.linspace(0, len(fft_bins) - 1, self.num_bins).astype(int)
                fft_bins = fft_bins[indices]
            
            # Apply smoothing with configurable decay
            for i in range(self.num_bins):
                target = fft_bins[i]
                self.bar_heights[i] += (target - self.bar_heights[i]) * (1.0 - self.decay_rate)
    
    def draw(self, surface: pygame.Surface):
        """Draw spectrum bars."""
        w, h = surface.get_size()
        
        # Calculate usable area
        usable_height = h - MARGIN_TOP - MARGIN_BOTTOM
        
        # Calculate bar dimensions
        total_width = w - MARGIN_LEFT - MARGIN_RIGHT
        self.bar_width = max(2, total_width // self.num_bins - self.bar_spacing)
        
        # Draw bars
        for i, height in enumerate(self.bar_heights):
            bar_height = int(height * usable_height * 0.8)
            x = MARGIN_LEFT + i * (self.bar_width + self.bar_spacing)
            y = h - MARGIN_BOTTOM - bar_height
            
            pygame.draw.rect(surface, self.color, 
                           (x, y, self.bar_width, bar_height))