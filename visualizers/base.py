#!/usr/bin/env python3
import pygame
from abc import ABC, abstractmethod


class Visualizer(ABC):
    """Base class for audio visualizers."""
    
    def __init__(self, config: dict):
        """Initialize visualizer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Load theme color
        from core.theme_loader import get_theme_loader
        theme_loader = get_theme_loader()
        style = theme_loader.load_style('pipboy')
        self.color = tuple(style['colors']['primary'])
    
    @abstractmethod
    def update(self, audio_data: dict, dt: float):
        """Update visualizer state based on audio data.
        
        Args:
            audio_data: Dictionary containing audio analysis data
                - 'fft': FFT frequency bins
                - 'amplitude': Overall amplitude
                - 'waveform': Time-domain waveform
            dt: Delta time in seconds
        """
        pass
    
    @abstractmethod
    def draw(self, surface: pygame.Surface):
        """Draw the visualizer.
        
        Args:
            surface: Pygame surface to draw on
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Reset visualizer state."""
        pass