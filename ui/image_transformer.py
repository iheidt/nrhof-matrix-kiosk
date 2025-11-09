#!/usr/bin/env python3
"""
Image transformation utilities for creating matrix-style effects.
"""

from pathlib import Path

import numpy as np
import pygame
from PIL import Image, ImageDraw, ImageFont

# Matrix green color and dark background
GREEN = (140, 255, 140)
BG = (15, 20, 15)


def transform_to_matrix(
    src_path: Path,
    cell: int = 8,
    font_name: str = "IBMPlexMono-Regular.ttf",
) -> pygame.Surface | None:
    """Transform an image into a matrix-style ASCII mosaic using '0' and '1' characters.

    Args:
        src_path: Path to source image
        cell: Size of each character cell in pixels (default: 8)
        font_name: Font file name for rendering characters (default: IBMPlexMono-Regular.ttf)

    Returns:
        pygame.Surface with the matrix-transformed image, or None if transformation failed
    """
    try:
        # Load and convert to grayscale
        im = Image.open(src_path).convert("L")
        w, h = im.size
        gw, gh = w // cell, h // cell

        # Average luminance per cell
        arr = np.array(im)
        arr = arr[: gh * cell, : gw * cell]
        blocks = arr.reshape(gh, cell, gw, cell).mean(axis=(1, 3))

        # Threshold into 0/1 based on mean luminance
        mask = (blocks > blocks.mean()).astype(np.uint8)

        # Create output image with dark background
        out = Image.new("RGB", (gw * cell, gh * cell), BG)
        draw = ImageDraw.Draw(out)

        # Load font
        project_root = Path(__file__).parent.parent
        font_path = project_root / "assets" / "fonts" / font_name
        try:
            font = ImageFont.truetype(str(font_path), cell + 2)
        except Exception:
            font = ImageFont.load_default()

        # Draw ASCII characters
        for y in range(gh):
            for x in range(gw):
                ch = "1" if mask[y, x] else "0"
                draw.text((x * cell, y * cell), ch, fill=GREEN, font=font)

        # Resize back to original dimensions using nearest neighbor
        out = out.resize((w, h), Image.NEAREST)

        # Convert PIL image to pygame surface
        mode = out.mode
        size = out.size
        data = out.tobytes()
        return pygame.image.fromstring(data, size, mode)

    except Exception as e:
        print(f"Error transforming image to matrix style: {e}")
        return None
