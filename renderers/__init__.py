#!/usr/bin/env python3
"""
Renderer abstraction layer.

Decouples scene logic from rendering implementation, enabling:
- Future Metal/Swift renderer
- GPU-accelerated rendering
- Remote rendering over network
"""

from .base import RendererBase, RenderCommand
from .frame_state import FrameState, Shape, Text, Image, Video
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
    backend = config.get('render', {}).get('backend', 'pygame')
    
    if backend == 'pygame':
        return PygameRenderer(config)
    elif backend == 'swift':
        # Future: from .swift_renderer import SwiftRenderer
        # return SwiftRenderer(config)
        raise NotImplementedError("Swift renderer not yet implemented")
    else:
        raise ValueError(f"Unknown renderer backend: {backend}")


__all__ = [
    'RendererBase',
    'RenderCommand',
    'FrameState',
    'Shape',
    'Text',
    'Image',
    'Video',
    'PygameRenderer',
    'create_renderer'
]