#!/usr/bin/env python3
"""
Renderer abstraction layer.

Decouples scene logic from rendering implementation, enabling:
- Future Metal/Swift renderer for GPU acceleration
- Headless renderer for testing
- Remote rendering over network
- Multiple rendering backends without changing scene code

Renderer Interface Contract:
    Required methods:
        - initialize(): Set up rendering context
        - get_surface(): Return surface for direct rendering
        - shutdown(): Clean up resources

    Optional methods:
        - render(frame_state): Declarative rendering (recommended)
        - present(): Present frame (if not auto-presented)

Usage:
    # Create renderer from config
    renderer = create_renderer(config)
    renderer.initialize()

    # Option 1: Direct rendering (backward compatible)
    surface = renderer.get_surface()
    scene.render(surface)
    renderer.present()

    # Option 2: Declarative rendering (recommended)
    frame_state = FrameState()
    scene.build_frame(frame_state)
    renderer.render(frame_state)
    renderer.present()

    # Cleanup
    renderer.shutdown()
"""

from .base import RenderCommand, RendererBase
from .frame_state import FrameState, Image, Shape, Text, Video
from .pygame_renderer import PygameRenderer


def create_renderer(config: dict) -> RendererBase:
    """Factory function to create renderer based on config.

    Args:
        config: Configuration dictionary

    Returns:
        Renderer instance

    Raises:
        ValueError: If backend is not supported
    """
    backend = config.get("render", {}).get("backend", "pygame")

    if backend == "pygame":
        return PygameRenderer(config)
    elif backend == "swift":
        # Future: from .swift_renderer import SwiftRenderer
        # return SwiftRenderer(config)
        raise NotImplementedError("Swift renderer not yet implemented")
    else:
        raise ValueError(f"Unknown renderer backend: {backend}")


__all__ = [
    "RendererBase",
    "RenderCommand",
    "FrameState",
    "Shape",
    "Text",
    "Image",
    "Video",
    "PygameRenderer",
    "create_renderer",
]
