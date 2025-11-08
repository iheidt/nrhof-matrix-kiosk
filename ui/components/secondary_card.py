#!/usr/bin/env python3
"""Secondary card component - simpler card with title above bordered content."""

import pygame
from pygame import Surface


def draw_secondary_card(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    theme: dict,
    content_callback=None,
) -> dict:
    """Draw a secondary card with title above and 3px border around content.

    Args:
        surface: Pygame surface to draw on
        x: X position
        y: Y position
        width: Card width
        height: Card height (includes title and content)
        title: Title text to display above the content
        theme: Theme dictionary with layout and style
        content_callback: Optional callback function(surface, content_rect) to draw content

    Returns:
        dict with card_rect, content_rect, and title_rect
    """
    from ui.fonts import render_mixed_text

    style = theme.get("style", {})
    # Use explicit color if provided, otherwise fall back to style primary
    color = theme.get("color", style.get("primary", (255, 255, 255)))
    border_width = 3  # Fixed 3px border for secondary cards
    title_margin = 12  # Space between title and content border

    # Get font size from theme (use body size - 48)
    title_font_size = style.get("typography", {}).get("fonts", {}).get("body", 48)

    # Render title using font pipeline (uses IBM Plex Mono Italic for EN, Noto Sans JP for JP)
    title_surface = render_mixed_text(
        title,
        title_font_size,
        "primary_italic",  # Uses primary_italic font type (IBM Plex Mono Italic)
        color,
    )
    title_height = title_surface.get_height()

    # Draw title
    title_y = y
    surface.blit(title_surface, (x, title_y))

    # Calculate content area (below title)
    content_y = title_y + title_height + title_margin
    content_height = height - (title_height + title_margin)

    # Draw border around content area
    border_rect = pygame.Rect(x, content_y, width, content_height)
    pygame.draw.rect(surface, color, border_rect, border_width)

    # Calculate inner content rect (inside border)
    inner_padding = 16  # Padding inside the border
    content_rect = pygame.Rect(
        x + border_width + inner_padding,
        content_y + border_width + inner_padding,
        width - (border_width + inner_padding) * 2,
        content_height - (border_width + inner_padding) * 2,
    )

    # Call content callback if provided
    if content_callback:
        content_callback(surface, content_rect)

    return {
        "card_rect": pygame.Rect(x, y, width, height),
        "content_rect": content_rect,
        "title_rect": pygame.Rect(x, title_y, title_surface.get_width(), title_height),
    }
