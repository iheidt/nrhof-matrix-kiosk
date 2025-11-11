#!/usr/bin/env python3
"""Layout components - navigation and footer."""

import pygame
from pygame import Surface

# Import from parent ui modules
from ..fonts import get_localized_font, get_theme_font


def draw_scanlines(surface: pygame.Surface, strength: float = 0.15):
    """Draw CRT-style scanlines over the surface.

    Args:
        surface: Surface to draw scanlines on
        strength: Darkness of scanlines (0.0-1.0)
    """
    w, h = surface.get_size()
    scan = pygame.Surface((w, h), pygame.SRCALPHA)
    dark = int(255 * strength)
    for y in range(0, h, 2):
        pygame.draw.line(scan, (0, 0, 0, dark), (0, y), (w, y))
    surface.blit(scan, (0, 0), special_flags=pygame.BLEND_SUB)


def draw_back_arrow(surface: Surface, color: tuple = (140, 255, 140)) -> pygame.Rect:
    """Draw a back arrow in the top-left corner.

    Args:
        surface: Pygame surface to draw on
        color: RGB color tuple for the arrow

    Returns:
        pygame.Rect: Clickable area for the back arrow
    """
    from ui.components import MARGIN_LEFT, MARGIN_TOP

    # Dim the color slightly for subtle appearance
    arrow_color = tuple(int(c * 0.8) for c in color)

    # Draw back arrow text
    font = get_localized_font(24, "primary", "< back")
    arrow_text = "< back"
    text_surface = font.render(arrow_text, True, arrow_color)

    # Position in top-left with margins
    x = MARGIN_LEFT
    y = MARGIN_TOP

    surface.blit(text_surface, (x, y))

    # Return clickable rect
    return pygame.Rect(x, y, text_surface.get_width(), text_surface.get_height())


def draw_footer(
    surface: Surface,
    color: tuple = (140, 255, 140),
    show_settings: bool = True,
    custom_text: str = None,
):
    """Draw footer with settings card and company name div.

    Footer structure:
    - Card (80px): "settings" (left) | version (right)
    - Div (50px): "BIG NERD INDUSTRIES INC. 2025" (centered)

    Args:
        surface: Pygame surface to draw on
        color: RGB color tuple (not used, colors from theme)
        show_settings: Whether to show the settings text (default: True)
        custom_text: Optional custom text to display instead of settings (overrides show_settings)

    Returns:
        pygame.Rect: Rectangle for the settings text (for click detection), or None if hidden
    """
    from __version__ import __version__
    from core.theme_loader import get_theme_loader

    from ..components.primary_card import draw_card

    w, h = surface.get_size()

    # Load theme
    theme_loader = get_theme_loader()
    layout = theme_loader.load_layout("menu")  # Get base layout
    style = theme_loader.load_style("pipboy")

    # Get margins and footer settings
    margins = layout.get("margins", {})
    margin_left = margins.get("left", 50)
    margin_right = margins.get("right", 50)
    footer_settings = layout.get("footer", {})
    footer_height = footer_settings.get("height", 130)
    footer_fade_pct = footer_settings.get("border_fade_pct", 0.33)

    # Calculate positions
    footer_top = h - footer_height
    card_height = 80
    div_height = 50

    # Draw settings card
    card_x = margin_left
    card_y = footer_top
    card_width = w - margin_left - margin_right

    content_rect = draw_card(
        surface,
        card_x,
        card_y,
        card_width,
        card_height,
        theme={"layout": layout, "style": style},
        border_solid="bottom",
        border_fade_pct=footer_fade_pct,
    )

    # Draw "settings" text (left aligned in card) - only if show_settings is True or custom_text provided
    from core.localization import t

    primary_color = tuple(style["colors"]["primary"])
    settings_rect = None
    if custom_text or show_settings:
        micro_size = style["typography"]["fonts"]["micro"]
        # Use custom text if provided, otherwise use settings text
        settings_content = custom_text if custom_text else t("footer.settings")
        settings_font = get_localized_font(micro_size, "primary", settings_content)
        settings_text = settings_font.render(settings_content, True, primary_color)
        settings_x = content_rect.x
        settings_y = content_rect.y + (content_rect.height - settings_text.get_height()) // 2
        surface.blit(settings_text, (settings_x, settings_y))

        # Create rect for click detection
        settings_rect = pygame.Rect(
            settings_x,
            settings_y,
            settings_text.get_width(),
            settings_text.get_height(),
        )

    # Draw version number (right aligned in card)
    dim_color_hex = style["colors"].get("dim", "#2C405B")
    if isinstance(dim_color_hex, str) and dim_color_hex.startswith("#"):
        dim_color = tuple(int(dim_color_hex[i : i + 2], 16) for i in (1, 3, 5))
    else:
        dim_color = (
            tuple(dim_color_hex) if isinstance(dim_color_hex, list | tuple) else (44, 64, 91)
        )
    pico_size = style["typography"]["fonts"]["pico"]
    version_content = f"v{__version__}"
    # Version always uses IBM Plex Mono (primary font), never Japanese font
    version_font = get_theme_font(pico_size, "primary")
    version_text = version_font.render(version_content, True, dim_color)
    version_x = content_rect.x + content_rect.width - version_text.get_width()
    surface.blit(
        version_text,
        (version_x, content_rect.y + (content_rect.height - version_text.get_height()) // 2),
    )

    # Draw company name div (50px tall, below card)
    div_y = card_y + card_height
    label_size = style["typography"]["fonts"]["label"]
    company_content = t("footer.company")
    # Company name uses label font which never translates
    company_font = get_theme_font(label_size, "label")
    company_text = company_font.render(company_content, True, primary_color)
    company_x = (w - company_text.get_width()) // 2
    company_y = div_y + (div_height - company_text.get_height()) // 2
    surface.blit(company_text, (company_x, company_y))

    return settings_rect


def draw_status(surface: Surface, color: tuple = (140, 255, 140)):
    """Draw status message in top-right margin if present.

    Args:
        surface: Pygame surface to draw on
        color: RGB color tuple for status text
    """
    from core.app_state import get_app_state
    from core.theme_loader import get_theme_loader
    from ui.fonts import get_localized_font

    app_state = get_app_state()
    status_message = app_state.get_status()

    if not status_message:
        return

    w, h = surface.get_size()

    # Load theme
    theme_loader = get_theme_loader()
    layout = theme_loader.load_layout("menu")
    style = theme_loader.load_style("pipboy")

    # Get margins
    margins = layout.get("margins", {})
    margin_right = margins.get("right", 50)
    margin_top = margins.get("top", 50)

    # Render status text
    micro_size = style["typography"]["fonts"]["micro"]
    primary_color = tuple(style["colors"]["primary"])
    status_font = get_localized_font(micro_size, "primary", status_message)
    status_text = status_font.render(status_message, True, primary_color)

    # Position in top-right with margins
    status_x = w - margin_right - status_text.get_width()
    status_y = margin_top // 2 - status_text.get_height() // 2

    surface.blit(status_text, (status_x, status_y))


def draw_hud(surface: Surface, color: tuple = (0, 255, 0)):
    """Draw performance HUD in top-left margin if enabled.

    Args:
        surface: Pygame surface to draw on
        color: RGB color tuple for HUD text (default: green)
    """
    from core.observability import get_performance_hud
    from core.theme_loader import get_theme_loader
    from ui.fonts import get_theme_font

    hud = get_performance_hud()

    if not hud.enabled:
        return

    w, h = surface.get_size()

    # Load theme
    theme_loader = get_theme_loader()
    layout = theme_loader.load_layout("menu")
    style = theme_loader.load_style("pipboy")

    # Get margins
    margins = layout.get("margins", {})
    margin_left = margins.get("left", 50)
    margin_top = margins.get("top", 50)

    # Get font
    pico_size = style["typography"]["fonts"]["pico"]
    hud_font = get_theme_font(pico_size, "primary")

    # Position in top-left with margins
    hud_x = margin_left
    hud_y = margin_top // 2 - hud_font.get_height() // 2

    # Render HUD
    hud.render(surface, hud_font, hud_x, hud_y, color)
