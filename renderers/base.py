#!/usr/bin/env python3
"""
Base renderer interface.

Defines the minimal contract that all renderers must implement.
Renderers can be pygame-based, Metal-based, headless (for testing), etc.

Required Methods:
    - initialize(): Set up rendering context
    - get_surface(): Return the rendering surface
    - shutdown(): Clean up resources

Optional Methods:
    - render(frame_state): Render declarative frame state (recommended)
    - present(): Present frame to display (if not auto-presented)

Backward Compatibility:
    - Scenes can still render directly to get_surface() if needed
    - FrameState rendering is opt-in for gradual migration
"""

from abc import ABC, abstractmethod
from typing import Any

from .frame_state import FrameState

__all__ = ["RendererBase", "RenderCommand"]


class RenderCommand:
    """Base class for render commands (future use for command buffers)."""

    pass


class RendererBase(ABC):
    """Abstract base class for all renderers.

    Minimal required interface for rendering backends.
    Implementations: PygameRenderer, MetalRenderer (future), HeadlessRenderer (testing)
    """

    def __init__(self, config: dict):
        """Initialize renderer.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.resolution = config.get("render", {}).get("resolution", [1280, 1024])
        self.width, self.height = self.resolution

    @abstractmethod
    def initialize(self):
        """Initialize the renderer (create window, context, etc.).

        Required method. Must be called before rendering.
        Should set up display, window, graphics context, etc.
        """
        pass

    def render(self, frame_state: FrameState):  # noqa: B027
        """Render a complete frame from declarative state.

        Optional method. Provides declarative rendering API.
        If not implemented, scenes can render directly to get_surface().

        Args:
            frame_state: Frame state containing all rendering commands

        Raises:
            NotImplementedError: If renderer doesn't support FrameState rendering
        """
        pass

    def present(self):  # noqa: B027
        """Present the rendered frame to the display.

        Optional method. Some renderers auto-present (e.g., immediate mode).
        Others need explicit present() call (e.g., double-buffered).

        Default: No-op (for renderers that auto-present)
        """
        pass

    @abstractmethod
    def shutdown(self):
        """Clean up renderer resources.

        Required method. Must be called on app shutdown.
        Should release graphics context, close window, free resources.
        """
        pass

    @abstractmethod
    def get_surface(self) -> Any:
        """Get the underlying rendering surface.

        Required method. Returns the surface that scenes can render to directly.
        This provides backward compatibility for scenes that don't use FrameState.

        Returns:
            Rendering surface (pygame.Surface, Metal texture, numpy array, etc.)

        Examples:
            - PygameRenderer: Returns pygame.Surface
            - MetalRenderer: Returns Metal texture handle
            - HeadlessRenderer: Returns numpy array for testing
        """
        pass
