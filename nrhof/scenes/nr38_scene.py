#!/usr/bin/env python3
import threading
from typing import Any

import pygame

from nrhof.core.localization import get_language
from nrhof.core.logging_utils import setup_logger
from nrhof.core.theme_loader import get_theme_loader
from nrhof.integrations.webflow_cache import WebflowCache, WebflowCacheManager
from nrhof.integrations.webflow_client import create_webflow_client
from nrhof.integrations.webflow_constants import NR38_LIST_UUID
from nrhof.routing.intent_router import Intent
from nrhof.scenes.scene_manager import Scene
from nrhof.ui.components import (
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    draw_footer,
    draw_hud,
    draw_scanlines,
    draw_status,
    draw_title_card_container,
)
from nrhof.ui.fonts import get_localized_font, get_theme_font, render_mixed_text


class NR38Scene(Scene):
    """NR-38 scene."""

    def __init__(self, ctx):
        super().__init__(ctx)

        # Logger
        self.logger = setup_logger(__name__)

        # Load theme
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme("nr38", theme_name="pipboy")

        # Extract from theme
        self.color = tuple(self.theme["style"]["colors"]["primary"])
        self.bg = tuple(self.theme["style"]["colors"]["background"])

        # Layout vars
        self.nav_back_rect = None
        self.settings_rect = None  # Store settings text rect for click detection
        self.band_rects = []  # Store band item rects for click detection

        # Cache rendered surfaces to prevent re-rendering every frame
        self._nav_back_surface = None
        self._title_surface = None
        self._title_overlap = None
        self._title_overlap_language = None  # Track language used for overlap calculation
        self._cached_language = None  # Track language for cache invalidation

        # Webflow data
        self._bands: list[dict[str, Any]] = []
        self._loading = False
        self._loaded = False
        self._cache_manager: WebflowCacheManager | None = None
        self._stop_loading = False  # Flag to cancel background thread

    def on_enter(self):
        """Called when scene becomes active."""
        super().on_enter()  # Take memory snapshot
        # Always reload bands to pick up fresh cache data
        if not self._loading:
            self._stop_loading = False  # Reset stop flag
            self._loading = True
            self._loaded = False  # Reset loaded flag to force refresh
            # Fetch bands in background thread
            thread = threading.Thread(
                target=self._fetch_bands,
                daemon=True,
                name="nr38_fetch_bands",
            )
            thread.start()

    def on_exit(self):
        """Called when scene is about to be replaced."""
        # Signal background thread to stop
        self._stop_loading = True
        super().on_exit()  # Call parent cleanup (event handlers, caches, GC)

    def handle_event(self, event: pygame.event.Event):
        """Handle NR-38 input."""
        # ESC key to return to previous scene
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True

        # Handle mouse clicks (ignore scroll wheel events)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 2, 3):
            # Check nav_back click
            if self.nav_back_rect and self.nav_back_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
            # Check settings click
            if self.settings_rect and self.settings_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_TO_SETTINGS)
                return True
            # Check band item clicks
            for band_rect, band_data in self.band_rects:
                if band_rect.collidepoint(event.pos):
                    # Pass minimal band data (already filtered to essential fields)
                    self.ctx.intent_router.emit(Intent.GO_TO_BAND_DETAILS, band_data=band_data)
                    return True

        return False

    def _fetch_bands(self):
        """Fetch NR-38 bands from cache (runs in background thread)."""
        import time

        try:
            # Initialize cache manager if not exists
            if self._cache_manager is None:
                # Get cache manager from app context if available
                if hasattr(self.ctx, "webflow_cache_manager"):
                    self._cache_manager = self.ctx.webflow_cache_manager
                else:
                    # Create new cache manager
                    webflow_client = create_webflow_client(self.ctx.config, self.logger)

                    if webflow_client is None:
                        self.logger.warning("Webflow client not available")
                        self._loading = False
                        return

                    cache = WebflowCache(logger=self.logger)
                    self._cache_manager = WebflowCacheManager(webflow_client, cache, self.logger)

            # Retry logic to wait for cache to be populated
            all_bands = None
            max_retries = 3
            retry_delay = 0.5  # seconds

            for attempt in range(max_retries):
                # Check if we should stop (scene exited)
                if self._stop_loading:
                    return

                # Get bands from cache (filtered for NR-38 UUID reference)
                # The nerd-rock-list field contains a UUID reference, not a string
                all_bands = self._cache_manager.get_bands(filter_list=NR38_LIST_UUID)

                if all_bands:
                    break

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

            if all_bands:
                # Extract and format band data
                nr38_bands = []
                for band in all_bands:
                    field_data = band.get("fieldData", {})
                    # Use display-name-2 if available, fallback to name
                    display_name = field_data.get("display-name-2") or field_data.get(
                        "name",
                        "Unknown",
                    )
                    rank = field_data.get("rank", 999)

                    # Extract only the fields actually used by band_details_scene
                    minimal_field_data = {
                        "name": field_data.get("name"),
                        "logo": field_data.get("logo"),
                        "card-pic-1": field_data.get("card-pic-1"),
                        "color": field_data.get("color"),
                        "complimentary-color---dark": field_data.get("complimentary-color---dark"),
                    }

                    # Store minimal data for list display and details
                    nr38_bands.append(
                        {
                            "name": display_name.lower(),  # Store display name as 'name' for rendering (lowercase)
                            "rank": rank,
                            "id": band.get("id"),  # Webflow item ID
                            "fieldData": minimal_field_data,  # Only essential fields
                        },
                    )

                # Sort by rank
                nr38_bands.sort(key=lambda x: x["rank"])

                # Store bands
                self._bands = nr38_bands
                self._loaded = True
                self.logger.info(f"Loaded {len(self._bands)} NR-38 bands from cache")
            else:
                self.logger.warning("No NR-38 bands in cache")

        except Exception as e:
            self.logger.error(f"Error loading NR-38 bands: {e}")
        finally:
            self._loading = False

    def update(self, dt: float):
        """Update NR-38 state."""
        pass

    def draw(self, screen: pygame.Surface):
        """Draw NR-38 screen."""
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
        # Cache to prevent re-rendering every frame
        from nrhof.core.localization import t

        current_language = get_language()
        if self._nav_back_surface is None or self._cached_language != current_language:
            nav_back_text = t("common.esc")
            self._nav_back_surface = render_mixed_text(
                nav_back_text,
                style["typography"]["fonts"]["micro"],
                "primary",
                self.color,
            )
        nav_back_x = MARGIN_LEFT
        nav_back_y = MARGIN_TOP
        screen.blit(self._nav_back_surface, (nav_back_x, nav_back_y))

        # Store rect for click detection
        self.nav_back_rect = pygame.Rect(
            nav_back_x,
            nav_back_y,
            self._nav_back_surface.get_width(),
            self._nav_back_surface.get_height(),
        )

        # Calculate title card position (20px below nav_back)
        title_card_y = nav_back_y + self._nav_back_surface.get_height() + 20
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

        # Get title font to calculate overlap (cached)
        if self._title_surface is None or self._cached_language != current_language:
            title_text = t("nr38.title")
            title_font_size = style["typography"]["fonts"].get("title", 76)
            self._title_surface = render_mixed_text(
                title_text,
                title_font_size,
                "secondary",
                (255, 255, 255),
            )
            self._title_overlap = self._title_surface.get_height() // 2
            self._title_overlap_language = current_language  # Store language used for overlap
            self._cached_language = (
                current_language  # Update cache after recalculating both surfaces
            )
        title_text = t("nr38.title")  # Still need text for draw_title_card_container
        title_overlap = self._title_overlap

        # Adjust y position so title overlaps card border
        title_card_y_adjusted = title_card_y + title_overlap

        # Language-specific adjustment for Japanese
        # Only apply offset if overlap was calculated in English but we're displaying in Japanese
        if current_language == "jp" and self._title_overlap_language == "en":
            title_card_y_adjusted += 18  # Additional offset for Japanese to match English position

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
            content_margin=0,  # Reduced margin between title and content
        )

        # Content area for NR-38 with custom horizontal margins
        content_horizontal_margin = 16  # Adjustable dial for left/right content margin
        content_y = layout_info["content_start_y"]
        content_x = margin_left + content_horizontal_margin  # Start with custom margin
        content_width = title_card_width - (
            content_horizontal_margin * 2
        )  # Subtract margins from both sides
        h - content_y - 130  # Subtract footer height

        # Calculate 3-column layout with adjustable dials
        # Layout configuration dials
        line_height = 50  # Spacing between numbers
        gutter1_width = 30  # Space between column 1 and 2
        gutter2_width = -10  # Space between column 2 and 3

        # Individual column width dials (as percentage of content_width)
        col1_width_pct = 0.33  # Column 1 width as % of content width
        col2_width_pct = 0.33  # Column 2 width as % of content width
        col3_width_pct = 0.33  # Column 3 width as % of content width

        # Calculate actual column widths
        col1_width = content_width * col1_width_pct
        col2_width = content_width * col2_width_pct
        content_width * col3_width_pct

        # Calculate column x positions
        col1_x = content_x
        col2_x = col1_x + col1_width + gutter1_width
        col3_x = col2_x + col2_width + gutter2_width

        # Font for numbers and band names (hardcoded 28 for NR38)
        # Numbers always use English font (IBM Plex)
        # Band names use English font (Webflow data always in English)
        font_size = 28
        japanese_suffix_size = 22  # Smaller size for 位 to match English height
        japanese_double_digit_spacing = 16  # Extra spacing for Japanese ranks >= 10
        english_font = get_theme_font(font_size, "primary")  # IBM Plex for numbers
        japanese_font = get_localized_font(japanese_suffix_size, "primary", "位")  # For 位 suffix
        band_font = get_theme_font(font_size, "primary")

        # Helper function to render rank number with mixed fonts
        def render_rank_number(rank: int, x: int, y: int):
            """Render rank number with mixed fonts: English for number, localized for suffix.

            Returns:
                Width of the rendered number (for positioning band name)
            """
            current_lang = get_language()

            # Render the number part (always English font)
            number_text = str(rank)
            number_surface = english_font.render(number_text, True, self.color)
            number_width = number_surface.get_width()

            # Render the suffix
            if current_lang == "jp":
                # Japanese: independent vertical offset dials
                japanese_number_offset = 2  # Dial to move number up/down
                japanese_suffix_offset = (
                    -2  # Dial to move 位 up/down (relative to baseline calculation)
                )
                screen.blit(number_surface, (x, y + japanese_number_offset))

                # Japanese: use 位 with Japanese font (smaller size, baseline aligned)
                suffix_surface = japanese_font.render("位", True, self.color)
                # Calculate vertical offset to align baseline
                # Japanese font is smaller, so offset down to align with English baseline
                suffix_height = suffix_surface.get_height()
                number_height = number_surface.get_height()
                y_offset = (
                    number_height - suffix_height + japanese_number_offset + japanese_suffix_offset
                )
                screen.blit(suffix_surface, (x + number_width, y + y_offset))
                return number_width + suffix_surface.get_width()
            else:
                # English: no offset for number
                screen.blit(number_surface, (x, y))

                # English: use . with English font
                suffix_surface = english_font.render(".", True, self.color)
                screen.blit(suffix_surface, (x + number_width, y))
                return number_width + suffix_surface.get_width()

        # Clear band rects for this frame
        self.band_rects = []

        # Show loading message if still fetching
        if self._loading:
            loading_text = "Loading bands from Webflow..."
            loading_surface = band_font.render(loading_text, True, self.color)
            screen.blit(loading_surface, (content_x, content_y + 20))
        elif not self._bands:
            # Show message if no bands loaded
            error_text = "No bands available. Check Webflow connection."
            error_surface = band_font.render(error_text, True, self.color)
            screen.blit(error_surface, (content_x, content_y + 20))
        else:
            # Draw three columns with ranked bands
            # Column 1: 1-13
            for i in range(min(13, len(self._bands))):
                band = self._bands[i]
                rank = i + 1
                band_name = band["name"]

                # Render number with mixed fonts
                y_pos = content_y + 20 + i * line_height
                render_rank_number(rank, col1_x, y_pos)

                # Render band name (offset to the right of number)
                # Add extra spacing for Japanese double-digit numbers
                current_lang = get_language()
                extra_spacing = (
                    japanese_double_digit_spacing if (current_lang == "jp" and rank >= 10) else 0
                )
                band_surface = band_font.render(band_name, True, self.color)
                band_x = col1_x + 50 + extra_spacing
                screen.blit(band_surface, (band_x, y_pos + 2))

                # Store clickable rect for this band (entire row)
                band_rect = pygame.Rect(col1_x, y_pos, col1_width, line_height)
                self.band_rects.append((band_rect, band))

            # Column 2: 14-26
            for i in range(13, min(26, len(self._bands))):
                band = self._bands[i]
                rank = i + 1
                band_name = band["name"]

                y_pos = content_y + 20 + (i - 13) * line_height
                render_rank_number(rank, col2_x, y_pos)

                # Add extra spacing for Japanese double-digit numbers
                current_lang = get_language()
                extra_spacing = (
                    japanese_double_digit_spacing if (current_lang == "jp" and rank >= 10) else 0
                )
                band_surface = band_font.render(band_name, True, self.color)
                band_x = col2_x + 50 + extra_spacing
                screen.blit(band_surface, (band_x, y_pos + 2))

                # Store clickable rect for this band (entire row)
                band_rect = pygame.Rect(col2_x, y_pos, col2_width, line_height)
                self.band_rects.append((band_rect, band))

            # Column 3: 27-38
            for i in range(26, min(38, len(self._bands))):
                band = self._bands[i]
                rank = i + 1
                band_name = band["name"]

                y_pos = content_y + 20 + (i - 26) * line_height
                render_rank_number(rank, col3_x, y_pos)

                # Add extra spacing for Japanese double-digit numbers
                current_lang = get_language()
                extra_spacing = (
                    japanese_double_digit_spacing if (current_lang == "jp" and rank >= 10) else 0
                )
                band_surface = band_font.render(band_name, True, self.color)
                band_x = col3_x + 50 + extra_spacing
                screen.blit(band_surface, (band_x, y_pos + 2))

                # Store clickable rect for this band (entire row)
                col3_width = content_width * col3_width_pct
                band_rect = pygame.Rect(col3_x, y_pos, col3_width, line_height)
                self.band_rects.append((band_rect, band))

        # Draw overlays, HUD, and footer
        draw_scanlines(screen)
        draw_hud(screen, self.color)
        draw_status(screen, self.color)
        self.settings_rect = draw_footer(screen, self.color, show_settings=True)
