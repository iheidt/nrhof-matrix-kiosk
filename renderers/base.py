#!/usr/bin/env python3
"""
Base renderer interface.

All renderers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any
from .frame_state import FrameState


class RenderCommand:
    """Base class for render commands (future use)."""
    pass


class RendererBase(ABC):
    """Abstract base class for all renderers."""
    
    def __init__(self, config: dict):
        """Initialize renderer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.resolution = config.get('render', {}).get('resolution', [1280, 1024])
        self.width, self.height = self.resolution
    
    @abstractmethod
    def initialize(self):
        """Initialize the renderer (create window, context, etc.)."""
        pass
    
    @abstractmethod
    def render(self, frame_state: FrameState):
        """Render a complete frame.
        
        Args:
            frame_state: Frame state containing all rendering commands
        """
        pass
    
    @abstractmethod
    def present(self):
        """Present the rendered frame to the display."""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Clean up renderer resources."""
        pass
    
    @abstractmethod
    def get_surface(self) -> Any:
        """Get the underlying rendering surface (for compatibility).
        
        Returns:
            Rendering surface (pygame.Surface, Metal texture, etc.)
        """
        pass