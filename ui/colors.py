#!/usr/bin/env python3
"""Color utilities for UI rendering."""


def dim_color(color: tuple, factor: float = 0.5) -> tuple:
    """Dim a color by a given factor.
    
    Args:
        color: RGB color tuple (r, g, b)
        factor: Dimming factor (0.0 = black, 1.0 = original)
        
    Returns:
        Dimmed RGB color tuple
        
    Example:
        >>> dim_color((255, 255, 255), 0.5)
        (127, 127, 127)
    """
    return tuple(int(c * factor) for c in color)


__all__ = ['dim_color']