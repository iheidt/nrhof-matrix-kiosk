#!/usr/bin/env python3
from pathlib import Path

import pygame

from nrhof.core.logging_utils import setup_logger
from nrhof.core.theme_loader import get_theme_loader
from nrhof.integrations.image_cache import ImageCache
from nrhof.routing.intent_router import Intent
from nrhof.scenes.band_details import (
    AlbumDataManager,
    AlbumGridRenderer,
    IconLoader,
    LogoManager,
    ScrollHandler,
    TabManager,
)
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
from nrhof.ui.fonts import render_mixed_text


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

        # Logger
        self.logger = setup_logger(__name__)

        # Image cache
        self.image_cache = ImageCache(logger=self.logger)

        # Cache directories
        # Go up from nrhof/scenes/band_details_scene.py to project root
        cache_dir = Path(__file__).parent.parent.parent / "cache"
        albums_cache_file = cache_dir / "albums_cache.json"
        images_cache_dir = cache_dir / "album_images"
        images_cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize helper classes
        self.album_data_manager = AlbumDataManager(
            self.logger,
            albums_cache_file,
            albums_cache_ttl_hours=24,
            images_cache_dir=images_cache_dir,
        )
        self.album_grid_renderer = AlbumGridRenderer(self.logger)
        self.icon_loader = IconLoader(self.logger)
        self.logo_manager = LogoManager(self.logger, self.image_cache, self.color)

        # Initialize managers
        self.scroll_handler = ScrollHandler(scroll_speed=20)
        self.tab_manager = TabManager(self.color, self.logger)

        # Band data
        self.band_name = "Band Name"
        self.band_id = None

        # Album display state
        self.matrix_src_paths = []
        self.matrix_images_cache = []  # Current tab's cache
        self.album_metadata = []
        self._current_album_type = None  # Track currently loaded album type
        self._tab_caches = {}  # Cache per album type: {"album": [...], "ep": [...]}

        # Load icons
        self.down_arrow_icon = self.icon_loader.load_down_arrow_icon()
        self.flame_icon = self.icon_loader.load_flame_icon()

    def set_band_data(self, band_data: dict):
        """Set the band data to display.

        Args:
            band_data: Dictionary containing band information from Webflow
        """
        if band_data:
            self.band_name = band_data.get("name", "Band Name")
            new_band_id = band_data.get("id")

            # Clear albums cache when band changes
            if self.band_id != new_band_id:
                self.album_data_manager.albums_by_type = {}
                self.matrix_src_paths = []
                self.matrix_images_cache = []
                self._current_album_type = None  # Reset album type tracking
                self._tab_caches = {}  # Clear all tab caches
                # Reset tabs to first tab when switching bands
                self.tab_manager.reset_for_new_band()

            self.band_id = new_band_id

            # Extract and load logo
            field_data = band_data.get("fieldData", {})
            logo_data = field_data.get("logo", {})
            logo_url = logo_data.get("url") if isinstance(logo_data, dict) else logo_data

            if logo_url:
                self.logo_manager.load_logo_async(logo_url, self.band_name)

    def on_enter(self):
        """Called when scene becomes active."""
        super().on_enter()

    def on_exit(self):
        """Called when scene is about to be replaced."""
        self.logo_manager.stop_loading()
        super().on_exit()

    def _load_album_covers_for_tab_type(self, album_type: str):
        """Load album cover images for the selected album type.

        Args:
            album_type: One of 'album', 'ep', 'live', or 'etc'
        """
        # Skip reload if we're already showing this album type
        if self._current_album_type == album_type and self.matrix_images_cache:
            self.logger.info(
                f"Album type '{album_type}' already loaded (cache size: {len(self.matrix_images_cache)}), skipping reload"
            )
            return

        self.logger.info(
            f"Loading album covers for type: {album_type} (previous: {self._current_album_type}, cache size: {len(self.matrix_images_cache)})"
        )
        self._current_album_type = album_type

        # Fetch albums using data manager
        self.album_data_manager.fetch_albums_for_band(
            self.band_id, album_type, self.ctx.webflow_cache_manager
        )

        # Get albums for this type
        albums = self.album_data_manager.albums_by_type.get(album_type, [])

        # Extract cover image URLs and metadata
        self.matrix_src_paths = []
        self.album_metadata = []

        for album in albums:
            field_data = album.get("fieldData", {})

            # Try thumbnail first, fall back to cover
            cover_url = None
            if "thumbnail-200-x-200" in field_data and field_data["thumbnail-200-x-200"]:
                cover_url = field_data["thumbnail-200-x-200"].get("url")
            elif "cover" in field_data and field_data["cover"]:
                cover_url = field_data["cover"].get("url")

            if cover_url:
                # Check if we have a cached transformed image
                cache_path = self.album_data_manager.get_image_cache_path(cover_url)
                if cache_path.exists():
                    self.matrix_src_paths.append(str(cache_path))
                else:
                    self.matrix_src_paths.append(cover_url)

                # Store metadata
                album_name = field_data.get("name", "Unknown")
                score_num = field_data.get("score-num", None)
                self.album_metadata.append({"name": album_name, "score": score_num})

                self.logger.info(
                    f"Added album cover: {album_name} (score: {score_num}) -> {cover_url}"
                )
            else:
                self.logger.warning(
                    f"No cover URL for album: {album.get('fieldData', {}).get('name', 'Unknown')}"
                )

        # Load cached images for this tab if available
        self.matrix_images_cache = self._tab_caches.get(album_type, [])

        # Reset scroll position when tab changes
        self.scroll_handler.reset()

        self.logger.info(
            f"Loaded {len(self.matrix_src_paths)} album covers with metadata for {album_type}"
        )

    def handle_event(self, event: pygame.event.Event):
        """Handle band details input."""
        num_albums = len(self.matrix_src_paths)

        # Handle mouse wheel scrolling
        if self.scroll_handler.handle_wheel_scroll(event, num_albums):
            return True

        # Handle mouse button down events (ignore scroll wheel events)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 2, 3):
            # Check nav_back click
            if self.nav_back_rect and self.nav_back_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
            # Check settings click
            if self.settings_rect and self.settings_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_TO_SETTINGS)
                return True
            # Handle tabs click
            if self.tab_manager.handle_click(event.pos):
                return True

            # Handle touch drag scrolling (only if scroll enabled)
            if self.scroll_handler.is_scroll_enabled(num_albums):
                # Check if clicking in scrollable area (not on UI elements)
                if not (self.nav_back_rect and self.nav_back_rect.collidepoint(event.pos)):
                    if not (self.settings_rect and self.settings_rect.collidepoint(event.pos)):
                        if not self.tab_manager.handle_click(event.pos):
                            # Start drag
                            return self.scroll_handler.start_drag(event.pos[1])

        if event.type == pygame.MOUSEBUTTONUP:
            if self.scroll_handler.end_drag():
                return True

        if event.type == pygame.MOUSEMOTION:
            if self.scroll_handler.update_drag(event.pos[1], num_albums):
                return True

        # ESC to return to previous scene
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True

        return False

    def update(self, dt: float):
        """Update band details state."""
        pass

    def draw(self, screen: pygame.Surface):
        """Draw band details screen."""
        # Clear screen
        screen.fill(self.bg)

        # Track if draw has been called
        if not hasattr(self, "_draw_called"):
            self._draw_called = True
            self.logger.info("BandDetailsScene.draw() called for the first time")

        w, h = screen.get_size()

        # Get style and layout
        style = self.theme["style"]
        layout = self.theme_loader.load_layout("menu")  # Use menu layout for margins

        # Get margins
        margins = layout.get("margins", {})
        margin_left = margins.get("left", MARGIN_LEFT)
        margin_right = margins.get("right", MARGIN_RIGHT)

        # Draw nav_back component ("<esc" in top-left corner at margin boundary)
        from nrhof.core.localization import t

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
        from nrhof.core.localization import get_language

        if get_language() == "jp":
            title_card_y_adjusted += -21

        # Draw the full-width title card container (with empty title, no top border)
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
            skip_top_border=True,  # We'll draw custom border with logo gap
            skip_japanese_adjustment=True,  # Logo positioning is same for all languages
            content_margin=-26,  # Reduced margin between title and tabs
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
        if self.logo_manager.logo_surface:
            # Calculate logo position - centered vertically with border line
            logo_x = margin_left + 35 + logo_padding
            logo_y = (
                border_y
                - (self.logo_manager.logo_surface.get_height() // 2)
                + self.logo_manager.logo_vertical_offset
            )

            # Calculate gap boundaries
            gap_start_x = margin_left + 35
            gap_end_x = (
                gap_start_x + (logo_padding * 2) + self.logo_manager.logo_surface.get_width()
            )

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
            screen.blit(self.logo_manager.logo_surface, (logo_x, logo_y))
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
        if self.logo_manager._loading_logo and not self.logo_manager.logo_surface:
            loading_font = style["typography"]["fonts"].get("body", 24)
            loading_surface = render_mixed_text(
                "Loading logo...", loading_font, "primary", self.color
            )
            # Position where title would be
            logo_x = margin_left + 35 + 24
            screen.blit(loading_surface, (logo_x, border_y - loading_surface.get_height() // 2))

        # Create/update tabs based on language and available albums
        self.tab_manager.update_tabs(
            self.album_data_manager, self.band_id, self.ctx.webflow_cache_manager
        )

        # Draw tabs (if any exist)
        content_y = layout_info["content_start_y"]
        tabs_x = margin_left + 35 + 24  # Match title card padding
        tabs_y = content_y + 20  # Same offset as visualizers scene

        self.tab_manager.draw(screen, tabs_x, tabs_y)

        # Content area baseline
        content_text_y = tabs_y + 60

        # Load album covers for the active tab (only when tab changes)
        if self.tab_manager.should_reload_tab():
            album_type = self.tab_manager.get_active_album_type()
            if album_type:
                self._load_album_covers_for_tab_type(album_type)
                self.tab_manager.mark_tab_loaded()

        # Render album grid
        if self.matrix_src_paths:
            self.matrix_images_cache, max_scroll = self.album_grid_renderer.render_grid(
                screen,
                self.matrix_src_paths,
                self.matrix_images_cache,
                self.album_metadata,
                self.scroll_handler.get_scroll_offset(),
                self.flame_icon,
                self.down_arrow_icon,
                self.theme,
                margin_left,
                margin_right,
                content_text_y,
                self.album_data_manager.get_image_cache_path,
            )
            self.scroll_handler.set_max_scroll(max_scroll)

            # Save cache for this tab
            if self._current_album_type:
                self._tab_caches[self._current_album_type] = self.matrix_images_cache
        else:
            # No albums available - show message
            no_albums_surface = render_mixed_text("No albums available", 36, "primary", self.color)
            tabs_x = margin_left + 35 + 24
            screen.blit(no_albums_surface, (tabs_x, content_text_y))

        # Draw overlays, HUD, and footer
        draw_scanlines(screen)
        draw_hud(screen, self.color)
        draw_status(screen, self.color)
        self.settings_rect = draw_footer(screen, self.color, show_settings=True)
