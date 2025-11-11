#!/usr/bin/env python3
"""Icon and SVG loading utilities."""

from io import BytesIO
from pathlib import Path

import pygame
from PIL import Image
from pygame import Surface

try:
    import cairosvg  # type: ignore

    HAVE_CAIROSVG = True
except Exception:
    HAVE_CAIROSVG = False


def load_icon(path: Path, size: tuple[int, int], fill_color: tuple = None) -> Surface | None:
    """Load an icon from SVG or image file.

    Args:
        path: Path to icon file
        size: Desired size as (width, height) tuple
        fill_color: Optional RGB tuple to replace SVG fill color

    Returns:
        Pygame Surface with the icon, or None if loading failed
    """
    try:
        if path.suffix.lower() == ".svg" and HAVE_CAIROSVG:
            # Read SVG and optionally replace fill color
            svg_content = path.read_text()
            if fill_color:
                # Convert RGB tuple to hex
                hex_color = f"#{fill_color[0]:02x}{fill_color[1]:02x}{fill_color[2]:02x}"
                # Replace ALL fill attributes (including fill="none", fill="black", etc.)
                import re

                # Replace existing fill="anything"
                svg_content = re.sub(r'fill="[^"]*"', f'fill="{hex_color}"', svg_content)
                # Replace existing fill='anything'
                svg_content = re.sub(r"fill='[^']*'", f'fill="{hex_color}"', svg_content)

                # Add fill attribute to <path> elements that don't have one
                svg_content = re.sub(
                    r"<path(?![^>]*fill=)([^>]*)>", f'<path fill="{hex_color}"\\1>', svg_content
                )
            png_bytes = cairosvg.svg2png(
                bytestring=svg_content.encode(),
                output_width=size[0],
                output_height=size[1],
            )
            pil_img = Image.open(BytesIO(png_bytes)).convert("RGBA")
        else:
            pil_img = Image.open(path).convert("RGBA")
        pil_img = pil_img.resize(size, Image.LANCZOS)
        mode = pil_img.mode
        data = pil_img.tobytes()
        return pygame.image.fromstring(data, pil_img.size, mode)
    except Exception as e:
        # Suppress cairo write errors (only happen on Ctrl+C interrupt)
        if "CAIRO_STATUS_WRITE_ERROR" not in str(e):
            print(f"Error loading icon: {e}")
        return None
