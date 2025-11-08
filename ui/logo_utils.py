#!/usr/bin/env python3
"""
Logo sizing utilities for handling various aspect ratios.
"""

import pygame


def calculate_logo_size(
    surface: pygame.Surface,
    target_height: int = 70,
    min_height: int = 70,
    max_height: int = 130,
    min_width: int = 200,
    max_width: int = 600,
) -> tuple[int, int]:
    """
    Calculate optimal logo dimensions based on aspect ratio.

    Handles three common cases:
    1. Wide/skinny logos (high aspect ratio): Apply min_width constraint
    2. Square/tall logos (low aspect ratio): Apply max_height constraint
    3. Balanced logos (medium aspect ratio): Use target_height

    Args:
        surface: The logo surface to size
        target_height: Ideal height for balanced logos (default: 60)
        min_height: Minimum height for any logo (default: 45)
        max_height: Maximum height for square/tall logos (default: 85)
        min_width: Minimum width for wide/skinny logos (default: 180)
        max_width: Maximum width for any logo (default: 400)

    Returns:
        tuple[int, int]: (width, height) for the scaled logo
    """
    original_width = surface.get_width()
    original_height = surface.get_height()

    if original_height == 0:
        return (min_width, min_height)

    aspect_ratio = original_width / original_height

    # Case 1: Wide/skinny logo (aspect ratio > 4.0)
    # Example: "ASIAN KUNG-FU GENERATION" - very horizontal
    if aspect_ratio > 8.0:
        # Use target_height and let width expand naturally
        height = target_height
        width = int(height * aspect_ratio)
        # Only constrain if it exceeds max_width
        if width > max_width:
            width = max_width
            height = int(width / aspect_ratio)
        return (width, height)

    # Case 2: Square or tall logo (aspect ratio < 4.0)
    # Example: "eels" - more square/vertical
    elif aspect_ratio < 3.0:
        # Use max_height to allow square logos to be tall
        height = max_height
        width = int(height * aspect_ratio)
        width = min(width, max_width)  # Don't exceed max_width
        return (width, height)

    # Case 3: Balanced logo (2.0 <= aspect ratio <= 4.0)
    # Example: "weezer" - nice horizontal proportion
    else:
        # Use target_height as-is
        height = target_height
        width = int(height * aspect_ratio)
        width = min(width, max_width)  # Don't exceed max_width
        return (width, height)
