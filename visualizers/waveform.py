#!/usr/bin/env python3
import pygame
import numpy as np
import math
import random
from .base import Visualizer
from utils import MARGIN_TOP, MARGIN_LEFT, MARGIN_RIGHT, MARGIN_BOTTOM
from renderers import FrameState, Shape


class WaveformVisualizer(Visualizer):
    """Flowing waveform visualizer with glow effects and particles."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Read from config with defaults
        self.num_waves = config.get('waveform_num_waves', 5)
        self.wave_points = config.get('waveform_points', 300)
        self.time_offset = 0
        self.wave_speed = config.get('waveform_speed', 0.03)
        
        # Amplitude tracking - start at zero
        self.amplitude_history = [0.0] * 5
        self.history_size = 5
        self.current_amplitude = 0.0
        
        # Frequency bands - start at zero
        self.freq_bands = config.get('waveform_freq_bands', 8)
        self.band_amplitudes = [0.0] * self.freq_bands
        
        # Particles for extra flair
        self.particles = []
        self.max_particles = 30
        
        # Glow surface for bloom effect
        self.glow_surface = None
    
    def reset(self):
        """Reset visualizer state."""
        self.time_offset = 0
        self.amplitude_history = [0.0] * self.history_size
        self.current_amplitude = 0.0
        self.band_amplitudes = [0.0] * self.freq_bands
        self.particles = []
    
    def update(self, audio_data: dict, dt: float):
        """Update waveform animation."""
        fft_bins = audio_data.get('fft')
        
        if fft_bins is not None and len(fft_bins) > 0:
            # Calculate overall amplitude with higher sensitivity
            amplitude = np.sqrt(np.mean(fft_bins ** 2)) * 3.0  # 3x multiplier
            
            # Update amplitude history
            self.amplitude_history.append(amplitude)
            if len(self.amplitude_history) > self.history_size:
                self.amplitude_history.pop(0)
            
            # Calculate frequency bands with boost
            band_size = len(fft_bins) // self.freq_bands
            for i in range(self.freq_bands):
                start = i * band_size
                end = start + band_size
                self.band_amplitudes[i] = np.mean(fft_bins[start:end]) * 2.0  # 2x boost
        else:
            # No audio - decay to zero
            if self.amplitude_history:
                self.amplitude_history = [a * 0.9 for a in self.amplitude_history]
            self.band_amplitudes = [a * 0.9 for a in self.band_amplitudes]
        
        # Only update time offset if there's audio activity
        avg_amp = np.mean(self.amplitude_history) if self.amplitude_history else 0
        if avg_amp > 0.01:  # Threshold for animation
            self.time_offset += self.wave_speed * dt * 60
    
    def draw(self, surface: pygame.Surface):
        """Draw flowing waveforms with glow effects."""
        w, h = surface.get_size()
        
        # Calculate usable area
        usable_width = w - MARGIN_LEFT - MARGIN_RIGHT
        usable_height = h - MARGIN_TOP - MARGIN_BOTTOM
        center_y = MARGIN_TOP + usable_height // 2
        
        # Get smoothed amplitude
        avg_amp = np.mean(self.amplitude_history) if self.amplitude_history else 0
        
        # Draw flat baseline if silent
        if avg_amp < 0.005:
            self._draw_baseline(surface, w, h, center_y, usable_width)
            return
        
        # Initialize glow surface if needed
        if self.glow_surface is None or self.glow_surface.get_size() != (w, h):
            self.glow_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Clear glow surface
        self.glow_surface.fill((0, 0, 0, 0))
        
        # Draw multiple waves with glow
        for wave_idx in range(self.num_waves):
            points = []
            wave_offset = wave_idx * 0.5
            
            for i in range(self.wave_points):
                x_ratio = i / self.wave_points
                x = MARGIN_LEFT + int(x_ratio * usable_width)
                
                # Calculate wave with multiple frequency components
                y_offset = 0
                for band_idx in range(min(3, self.freq_bands)):
                    freq = (band_idx + 1) * 2
                    phase = self.time_offset + wave_offset + x_ratio * math.pi * 2
                    amplitude = self.band_amplitudes[band_idx] * usable_height * 0.25
                    y_offset += math.sin(freq * phase) * amplitude
                
                y = center_y + int(y_offset) + wave_idx * 15
                points.append((x, y))
            
            # Draw wave with glow effect
            if len(points) > 1:
                # Calculate opacity based on wave index
                opacity = int(200 * (1 - wave_idx / self.num_waves))
                
                # Draw thick glow layer
                glow_color = tuple(list(self.color) + [opacity // 4])
                try:
                    pygame.draw.lines(self.glow_surface, glow_color, False, points, 8)
                except Exception:
                    pass
                
                # Draw medium glow layer
                glow_color2 = tuple(list(self.color) + [opacity // 2])
                try:
                    pygame.draw.lines(self.glow_surface, glow_color2, False, points, 4)
                except Exception:
                    pass
                
                # Draw main line
                main_color = tuple(list(self.color) + [opacity])
                try:
                    pygame.draw.lines(self.glow_surface, main_color, False, points, 2)
                except Exception:
                    pass
        
        # Blit glow surface to main surface
        surface.blit(self.glow_surface, (0, 0))
        
        # Draw particles
        self._draw_particles(surface)
    
    def _spawn_particle(self):
        """Spawn a particle at a random position along the waves."""
        particle = {
            'x': MARGIN_LEFT + random.random() * (pygame.display.get_surface().get_width() - MARGIN_LEFT - MARGIN_RIGHT),
            'y': MARGIN_TOP + pygame.display.get_surface().get_height() // 2 + (random.random() - 0.5) * 100,
            'vx': (random.random() - 0.5) * 3,
            'vy': (random.random() - 0.5) * 3,
            'life': 1.0,
            'size': random.randint(2, 4)
        }
        self.particles.append(particle)
    
    def _update_particle(self, particle, dt):
        """Update particle. Returns False if particle should be removed."""
        particle['x'] += particle['vx']
        particle['y'] += particle['vy']
        particle['life'] -= 0.015
        return particle['life'] > 0
    
    def _draw_particles(self, surface):
        """Draw all particles with glow."""
        for particle in self.particles:
            alpha = int(particle['life'] * 200)
            size = particle['size']
            
            # Draw glow
            glow_surf = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
            glow_color = tuple(list(self.color) + [alpha // 3])
            pygame.draw.circle(glow_surf, glow_color, (size * 3, size * 3), size * 3)
            surface.blit(glow_surf, (int(particle['x'] - size * 3), int(particle['y'] - size * 3)))
            
            # Draw core
            core_color = tuple(list(self.color) + [alpha])
            core_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, core_color, (size, size), size)
            surface.blit(core_surf, (int(particle['x'] - size), int(particle['y'] - size)))
    
    def _draw_baseline(self, surface, w, h, center_y, usable_width):
        """Draw a subtle flat baseline when silent."""
        # Draw a dim flat line to show the visualizer is active but silent
        start_pos = (MARGIN_LEFT, center_y)
        end_pos = (MARGIN_LEFT + usable_width, center_y)
        
        # Draw glow layer (thicker, dimmer)
        glow_color = tuple(int(c * 0.15) for c in self.color)
        pygame.draw.line(surface, glow_color, start_pos, end_pos, 3)
        
        # Draw main line (thinner, brighter)
        line_color = tuple(int(c * 0.4) for c in self.color)  # 40% brightness
        pygame.draw.line(surface, line_color, start_pos, end_pos, 1)