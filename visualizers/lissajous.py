#!/usr/bin/env python3
import pygame
import numpy as np
import math
from .base import Visualizer
from utils import MARGIN_TOP, MARGIN_LEFT, MARGIN_RIGHT, MARGIN_BOTTOM


class LissajousVisualizer(Visualizer):
    """Lissajous parametric curve visualizer."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Parametric curve settings from config
        self.num_points = config.get('lissajous_trail', 2000)
        self.param_a = config.get('lissajous_a', 3.0)
        self.param_b = config.get('lissajous_b', 2.0)
        self.phase = 0.0
        self.spin_speed = 0.02
        
        # Audio reactivity
        self.warp_amount = 0.0
        self.spin_multiplier = 1.0
        
        # Persistent phosphor fade
        self.phosphor_surface = None
        self.fade_alpha = 15
    
    def reset(self):
        """Reset visualizer state."""
        self.phase = 0.0
        self.warp_amount = 0.0
        self.spin_multiplier = 1.0
        if self.phosphor_surface:
            self.phosphor_surface.fill((0, 0, 0))
    
    def update(self, audio_data: dict, dt: float):
        """Update parametric curve animation."""
        fft_bins = audio_data.get('fft')
        
        if fft_bins is not None and len(fft_bins) > 0:
            # Calculate overall amplitude
            overall_amplitude = np.sqrt(np.mean(fft_bins ** 2))
            
            # Get low-mid frequency band energy
            band_size = len(fft_bins) // 8
            low_mid_energy = np.mean(fft_bins[band_size:band_size*3])
            
            # Update warp and spin
            self.warp_amount = low_mid_energy * 0.5
            self.spin_multiplier = 1.0 + overall_amplitude * 2.0
        else:
            self.warp_amount = 0.0
            self.spin_multiplier = 1.0
        
        # Update phase
        self.phase += self.spin_speed * self.spin_multiplier * dt * 60
    
    def draw(self, surface: pygame.Surface):
        """Draw the Lissajous curve."""
        w, h = surface.get_size()
        
        # Initialize phosphor surface if needed
        if self.phosphor_surface is None:
            self.phosphor_surface = pygame.Surface((w, h))
            self.phosphor_surface.fill((0, 0, 0))
        
        # Apply phosphor fade
        fade_surface = pygame.Surface((w, h))
        fade_surface.fill((0, 0, 0))
        fade_surface.set_alpha(self.fade_alpha)
        self.phosphor_surface.blit(fade_surface, (0, 0))
        
        # Calculate center and scale
        center_x = w // 2
        center_y = int(h * 0.4)
        usable_width = w - MARGIN_LEFT - MARGIN_RIGHT
        usable_height = h - MARGIN_TOP - MARGIN_BOTTOM
        scale = min(usable_width, usable_height) * 0.35
        
        # Generate parametric points
        points = []
        for i in range(self.num_points):
            t = (i / self.num_points) * 2 * math.pi
            
            # Spherical harmonic equations
            x_base = math.sin(self.param_a * t + self.phase)
            y_base = math.sin(self.param_b * t + self.phase * 1.3)
            
            # Apply audio-reactive warp
            warp_factor = 1.0 + self.warp_amount * math.sin(t * 2)
            x = x_base * warp_factor
            y = y_base * warp_factor
            
            # Scale to screen coordinates
            screen_x = int(center_x + x * scale)
            screen_y = int(center_y + y * scale)
            points.append((screen_x, screen_y))
        
        # Draw polyline on phosphor surface
        if len(points) > 1:
            try:
                pygame.draw.lines(self.phosphor_surface, self.color, False, points, 1)
            except Exception:
                pass
        
        # Blit to main surface
        surface.blit(self.phosphor_surface, (0, 0))