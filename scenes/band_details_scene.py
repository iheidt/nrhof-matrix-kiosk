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
    draw_title_card_container,
)
from ui.fonts import render_mixed_text


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

        # Band data (will be set via set_band_data method)
        self.band_name = "Band Name"  # Default placeholder
        self.band_data = None
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
        self.band_data = band_data
        # Extract band name from the data
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
            surface = self.image_cache.get_image(
                self._logo_url,
                max_size=(300, 300),
                fill_color=self.color,  # Recolor to primary theme color
            )
            if surface:
                self.logo_surface = surface
                self.logger.info(f"Logo loaded for {self.band_name}")
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
        # Use band name as the title
        title_text = self.band_name
        title_font_size = style["typography"]["fonts"].get("title", 76)
        title_surface = render_mixed_text(title_text, title_font_size, "secondary", (255, 255, 255))
        title_overlap = title_surface.get_height() // 2

        # Adjust y position so title overlaps card border
        title_card_y_adjusted = title_card_y + title_overlap

        # Draw the full-width title card container
        layout_info = draw_title_card_container(
            surface=screen,
            x=margin_left,
            y=title_card_y_adjusted,
            width=title_card_width,
            height=title_card_height,
            title=title_text,
            theme={"layout": layout, "style": style},
            border_fade_pct=border_fade_pct,
            border_height_pct=border_height_pct,
        )

        # Content area for band details
        content_y = layout_info["content_start_y"]
        content_x = margin_left + 40  # Add some padding

        # Display logo if loaded
        if self.logo_surface:
            logo_x = content_x
            logo_y = content_y + 20
            screen.blit(self.logo_surface, (logo_x, logo_y))
        elif self._loading_logo:
            # Show loading message
            loading_font = style["typography"]["fonts"].get("body", 24)
            loading_surface = render_mixed_text(
                "Loading logo...",
                loading_font,
                "primary",
                self.color,
            )
            screen.blit(loading_surface, (content_x, content_y + 20))

        # Draw scanlines and footer
        draw_scanlines(screen)
        self.settings_rect = draw_footer(
            screen,
            self.color,
            show_settings=True,
        )
