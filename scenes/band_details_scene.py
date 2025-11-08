#!/usr/bin/env python3
import logging
import threading

import pygame

from core.theme_loader import get_theme_loader
from integrations.image_cache import ImageCache
from routing.intent_router import Intent
from scenes.scene_manager import Scene, register_scene
from ui.components import (
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    draw_footer,
    draw_scanlines,
    draw_secondary_card,
    draw_title_card_container,
)
from ui.fonts import render_mixed_text
from ui.logo_utils import calculate_logo_size


@register_scene("BandDetailsScene")
class BandDetailsScene(Scene):
    """Band details scene - displays information about a selected band from NR-38."""

    def __init__(self, ctx):
        super().__init__(ctx)

        # Load theme
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme("band_details", theme_name="pipboy")

        # Extract from theme
        self.color = tuple(self.theme["style"]["colors"]["primary"])
        self.bg = tuple(self.theme["style"]["colors"]["background"])

        # Layout vars
        self.nav_back_rect = None
        self.settings_rect = None  # Store settings text rect for click detection

        # Band data (extracted fields only - don't store full fieldData)
        self.band_name = "Band Name"  # Default placeholder
        self.logo_surface = None  # Cached logo surface
        self._loading_logo = False
        self._logo_url = None

        # Logger
        self.logger = logging.getLogger(__name__)

        # Image cache
        self.image_cache = ImageCache(logger=self.logger)

    def set_band_data(self, band_data: dict):
        """Set the band data to display.

        Args:
            band_data: Dictionary containing band information from Webflow
        """
        # Extract only what we need - don't store full band_data to save memory
        if band_data:
            self.band_name = band_data.get("name", "Band Name")

            # Extract logo URL from fieldData
            field_data = band_data.get("fieldData", {})
            logo_data = field_data.get("logo", {})

            # Logo can be a dict with 'url' key or a string URL
            if isinstance(logo_data, dict):
                self._logo_url = logo_data.get("url")
            elif isinstance(logo_data, str):
                self._logo_url = logo_data
            else:
                self._logo_url = None

            # Start loading logo in background if URL exists
            if self._logo_url and not self._loading_logo:
                self._loading_logo = True
                self.logo_surface = None  # Reset logo
                thread = threading.Thread(target=self._load_logo, daemon=True)
                thread.start()

    def on_enter(self):
        """Called when scene becomes active."""
        super().on_enter()  # Take memory snapshot

    def on_exit(self):
        """Called when scene is about to be replaced."""
        self._loading_logo = False  # Stop any ongoing logo loading
        super().on_exit()  # Call parent cleanup (event handlers, caches, GC)

    def _load_logo(self):
        """Load logo from cache or download it (runs in background thread)."""
        if not self._logo_url:
            return

        try:
            # Use ImageCache to get the logo (handles caching and scaling)
            # Recolor SVGs to primary theme color
            # Load at high resolution first, then we'll scale intelligently
            surface = self.image_cache.get_image(
                self._logo_url,
                max_size=(600, 150),  # Load at very high-res to get full SVG dimensions
                fill_color=self.color,  # Recolor to primary theme color
            )
            if surface:
                # Apply smart sizing based on aspect ratio (uses defaults from logo_utils)
                width, height = calculate_logo_size(surface)

                # Scale to calculated size
                self.logo_surface = pygame.transform.smoothscale(surface, (width, height))
                self.logger.info(f"Logo loaded for {self.band_name} ({width}x{height})")
            else:
                self.logger.warning(f"Failed to load logo for {self.band_name}")
        except Exception as e:
            self.logger.error(f"Error loading logo: {e}")
        finally:
            self._loading_logo = False

    def handle_event(self, event: pygame.event.Event):
        """Handle band details input."""
        # ESC or click nav_back to return to previous scene
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True

        # Click nav_back
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.nav_back_rect and self.nav_back_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
            # Check settings click
            if self.settings_rect and self.settings_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_TO_SETTINGS)
                return True

        return False

    def update(self, dt: float):
        """Update band details state."""
        pass

    def draw(self, screen: pygame.Surface):
        """Draw band details screen."""
        # Clear screen
        screen.fill(self.bg)
        w, h = screen.get_size()

        # Get style and layout
        style = self.theme["style"]
        layout = self.theme_loader.load_layout("menu")  # Use menu layout for margins

        # Get margins
        margins = layout.get("margins", {})
        margin_left = margins.get("left", MARGIN_LEFT)
        margin_right = margins.get("right", MARGIN_RIGHT)

        # Draw nav_back component ("<esc" in top-left corner at margin boundary)
        from core.localization import t

        nav_back_text = t("common.esc")
        nav_back_surface = render_mixed_text(
            nav_back_text,
            style["typography"]["fonts"]["micro"],
            "primary",
            self.color,
        )
        nav_back_x = MARGIN_LEFT
        nav_back_y = MARGIN_TOP
        screen.blit(nav_back_surface, (nav_back_x, nav_back_y))

        # Store rect for click detection
        self.nav_back_rect = pygame.Rect(
            nav_back_x,
            nav_back_y,
            nav_back_surface.get_width(),
            nav_back_surface.get_height(),
        )

        # Calculate title card position (20px below nav_back)
        title_card_y = nav_back_y + nav_back_surface.get_height() + 20
        title_card_width = w - margin_left - margin_right

        # Calculate card height to fill remaining space (minus footer)
        footer_height = 130
        title_card_height = (
            h - title_card_y - margin_left - footer_height
        )  # Use margin_left as bottom margin (50px)

        # Get title card border settings from layout
        title_card_config = layout.get("title_card", {})
        border_fade_pct = title_card_config.get("border_fade_pct", 0.9)
        border_height_pct = title_card_config.get("border_height_pct", 0.15)

        # Get title font to calculate overlap
        # Use a placeholder space to maintain layout but we'll draw logo instead
        title_text = " "  # Empty space to maintain layout
        title_font_size = style["typography"]["fonts"].get("title", 76)
        title_surface = render_mixed_text(title_text, title_font_size, "secondary", (255, 255, 255))
        title_overlap = title_surface.get_height() // 2

        # Adjust y position so title overlaps card border, then move up 4px to align with now playing widget
        title_card_y_adjusted = title_card_y + title_overlap - 4

        # In Japanese mode, add 21px to compensate for the global adjustment we're skipping
        from core.localization import get_language

        if get_language() == "jp":
            title_card_y_adjusted += -21

        # Draw the full-width title card container (with empty title, no top border)
        draw_title_card_container(
            surface=screen,
            x=margin_left,
            y=title_card_y_adjusted,
            width=title_card_width,
            height=title_card_height,
            title=title_text,
            theme={"layout": layout, "style": style},
            border_fade_pct=border_fade_pct,
            border_height_pct=border_height_pct,
            skip_top_border=True,  # We'll draw custom border with logo gap
            skip_japanese_adjustment=True,  # Logo positioning is same for all languages
        )

        # Draw custom borders with fade effect (left, right, bottom only - no top)
        border_width = 6
        border_y = title_card_y_adjusted  # This is where the top border line is drawn
        border_color = self.color
        logo_padding = 24  # Padding on each side of logo

        # Manually draw left, right, and bottom borders with fade (skip top)
        # Calculate effective height for left/right borders
        effective_height = int(title_card_height * border_height_pct)
        fade_start = int(effective_height * (1.0 - border_fade_pct))
        fade_distance = effective_height - fade_start

        # Create surface for borders with alpha
        border_surface = pygame.Surface(
            (title_card_width + border_width * 2, title_card_height + border_width * 2),
            pygame.SRCALPHA,
        )
        border_surface.fill((0, 0, 0, 0))

        import pygame.surfarray as surfarray

        pixels_rgb = surfarray.pixels3d(border_surface)
        pixels_alpha = surfarray.pixels_alpha(border_surface)

        base_color = (int(border_color[0]), int(border_color[1]), int(border_color[2]))

        # Draw left and right borders with fade (starting 2px above border_width to align with top)
        for i in range(border_width - 2, effective_height + border_width):
            # Calculate alpha based on position
            adjusted_i = i - (border_width - 2)

            if adjusted_i < fade_start:
                alpha = 255
            elif adjusted_i < effective_height:
                progress = (adjusted_i - fade_start) / fade_distance if fade_distance > 0 else 1
                alpha = max(0, int(255 * (1.0 - progress)))
            else:
                alpha = 0

            if alpha > 0:
                # Left border
                pixels_rgb[0:border_width, i] = base_color
                pixels_alpha[0:border_width, i] = alpha
                # Right border
                pixels_rgb[
                    title_card_width + border_width : title_card_width + border_width * 2, i
                ] = base_color
                pixels_alpha[
                    title_card_width + border_width : title_card_width + border_width * 2, i
                ] = alpha

        del pixels_rgb
        del pixels_alpha

        # Blit border surface
        screen.blit(border_surface, (margin_left - border_width, border_y - border_width))

        # Draw top border with gap for logo
        if self.logo_surface:
            # Calculate logo position - centered vertically with border line
            logo_x = margin_left + 35 + logo_padding  # 35px to border edge + padding
            # The logo should be centered on the border line
            # border_y is the Y coordinate where the border is drawn (center of the 6px line)
            logo_y = border_y - (self.logo_surface.get_height() // 2)

            # Calculate gap boundaries
            gap_start_x = margin_left + 35  # Start of gap (at border edge)
            gap_end_x = (
                gap_start_x + (logo_padding * 2) + self.logo_surface.get_width()
            )  # End of gap

            # Draw left segment of border (from left edge to gap start)
            pygame.draw.line(
                screen, border_color, (margin_left, border_y), (gap_start_x, border_y), border_width
            )

            # Draw right segment of border (from gap end to right edge)
            pygame.draw.line(
                screen,
                border_color,
                (gap_end_x, border_y),
                (margin_left + title_card_width, border_y),
                border_width,
            )

            # Draw the logo (no background, pure transparency)
            screen.blit(self.logo_surface, (logo_x, logo_y))
        else:
            # No logo loaded - draw full border
            pygame.draw.line(
                screen,
                border_color,
                (margin_left, border_y),
                (margin_left + title_card_width, border_y),
                border_width,
            )

        # Show loading message if logo is still loading
        if self._loading_logo and not self.logo_surface:
            loading_font = style["typography"]["fonts"].get("body", 24)
            loading_surface = render_mixed_text(
                "Loading logo...",
                loading_font,
                "primary",
                self.color,
            )
            # Position where title would be
            logo_x = margin_left + 35 + 24
            border_y = title_card_y_adjusted
            screen.blit(loading_surface, (logo_x, border_y - loading_surface.get_height() // 2))

        # Draw Albums secondary card
        albums_card_x = margin_left + 35  # Align with content inside title card
        albums_card_y = border_y + 100  # Below the logo area
        albums_card_width = title_card_width - 70  # Account for card padding
        albums_card_height = 300  # Fixed height for now

        from core.localization import t

        draw_secondary_card(
            surface=screen,
            x=albums_card_x,
            y=albums_card_y,
            width=albums_card_width,
            height=albums_card_height,
            title=t("band_details.albums"),
            theme={"style": style, "color": self.color},
            content_callback=None,  # Empty content for now
        )

        # Draw scanlines and footer
        draw_scanlines(screen)
        self.settings_rect = draw_footer(
            screen,
            self.color,
            show_settings=True,
        )
