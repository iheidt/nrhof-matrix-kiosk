#!/usr/bin/env python3
import json
import logging
import threading
import time
from pathlib import Path

import pygame

from core.theme_loader import get_theme_loader
from integrations.image_cache import ImageCache
from integrations.webflow_constants import ALBUM_TYPE_UUIDS
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
from ui.image_transformer import transform_to_matrix
from ui.logo_utils import calculate_logo_size
from ui.tabs import Tabs


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
        self.logo_vertical_offset = 0  # Vertical offset for square/tall logos
        self._loading_logo = False
        self._logo_url = None

        # Tabs
        self.tabs = None
        self._cached_language = None  # Track language for cache invalidation

        # Matrix image (legacy - now using albums)
        self.matrix_src_path = None
        self.matrix_image = None
        self._matrix_image_loaded = False

        # Band and album data
        self.band_id = None  # Webflow band ID for fetching albums
        self.albums_by_type = {}  # Cache albums by type
        self.matrix_src_paths = []  # Album cover paths for current tab
        self.matrix_images_cache = []  # Cached transformed images

        # Logger
        self.logger = logging.getLogger(__name__)

        # Image cache
        self.image_cache = ImageCache(logger=self.logger)

        # Albums cache file
        self.albums_cache_file = Path(__file__).parent.parent / "cache" / "albums_cache.json"
        self.albums_cache_ttl_hours = 24  # Refresh daily

        # Transformed images cache directory
        self.images_cache_dir = Path(__file__).parent.parent / "cache" / "album_images"
        self.images_cache_dir.mkdir(parents=True, exist_ok=True)

        # Track last loaded tab to avoid reloading every frame
        self._last_loaded_tab_index = None

    def set_band_data(self, band_data: dict):
        """Set the band data to display.

        Args:
            band_data: Dictionary containing band information from Webflow
        """
        # Extract only what we need - don't store full band_data to save memory
        if band_data:
            self.band_name = band_data.get("name", "Band Name")
            new_band_id = band_data.get("id")

            # Clear albums cache when band changes
            if self.band_id != new_band_id:
                print(f"[DEBUG] Band changed from {self.band_id} to {new_band_id}, clearing cache")
                self.albums_by_type = {}
                self._last_loaded_tab_index = None  # Reset tab tracking
                self.matrix_src_paths = []
                self.matrix_images_cache = []

            self.band_id = new_band_id  # Store band ID for album fetching

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
                width, height, vertical_offset = calculate_logo_size(surface)
                self.logo_vertical_offset = vertical_offset

                # Scale to calculated size
                self.logo_surface = pygame.transform.smoothscale(surface, (width, height))
                self.logger.info(
                    f"Logo loaded for {self.band_name} ({width}x{height}, offset={vertical_offset})"
                )
            else:
                self.logger.warning(f"Failed to load logo for {self.band_name}")
        except Exception as e:
            self.logger.error(f"Error loading logo: {e}")
        finally:
            self._loading_logo = False

    def _load_albums_from_cache_file(self):
        """Load all albums from disk cache if available and not expired."""
        try:
            if not self.albums_cache_file.exists():
                print("[DEBUG] No albums cache file found")
                return None

            with open(self.albums_cache_file) as f:
                cache_data = json.load(f)

            # Check expiration
            cache_timestamp = cache_data.get("timestamp", 0)
            cache_age_hours = (time.time() - cache_timestamp) / 3600

            if cache_age_hours > self.albums_cache_ttl_hours:
                print(f"[DEBUG] Albums cache expired ({cache_age_hours:.1f} hours old)")
                return None

            albums = cache_data.get("albums", [])
            print(
                f"[DEBUG] Loaded {len(albums)} albums from cache file ({cache_age_hours:.1f} hours old)"
            )
            return albums

        except Exception as e:
            self.logger.error(f"Error loading albums cache: {e}")
            return None

    def _save_albums_to_cache_file(self, albums):
        """Save all albums to disk cache."""
        try:
            # Ensure cache directory exists
            self.albums_cache_file.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                "timestamp": time.time(),
                "ttl_hours": self.albums_cache_ttl_hours,
                "albums": albums,
            }

            with open(self.albums_cache_file, "w") as f:
                json.dump(cache_data, f)

            print(f"[DEBUG] Saved {len(albums)} albums to cache file")

        except Exception as e:
            self.logger.error(f"Error saving albums cache: {e}")

    def _fetch_albums_for_band(self, album_type: str):
        """Fetch albums from Webflow for the current band and type.

        Args:
            album_type: One of 'album', 'ep', 'live', or 'etc'
        """
        print(
            f"[DEBUG] _fetch_albums_for_band called with album_type={album_type}, band_id={self.band_id}"
        )
        if not self.band_id:
            print("[DEBUG] No band_id, returning early")
            self.logger.warning("No band ID set, cannot fetch albums")
            return

        print(f"[DEBUG] Fetching albums for band_id={self.band_id}, type={album_type}")
        self.logger.info(f"Fetching albums for band_id={self.band_id}, type={album_type}")

        # Check cache first - only use cache if it has albums
        if album_type in self.albums_by_type and len(self.albums_by_type[album_type]) > 0:
            print(f"[DEBUG] Using cached albums: {len(self.albums_by_type[album_type])} albums")
            self.logger.info(
                f"Using cached albums for type: {album_type} ({len(self.albums_by_type[album_type])} albums)"
            )
            return
        elif album_type in self.albums_by_type:
            print(
                f"[DEBUG] Cache exists but empty ({len(self.albums_by_type[album_type])} albums), re-fetching..."
            )

        print("[DEBUG] Not in cache, checking disk cache...")

        # Try to load from disk cache first
        cached_albums = self._load_albums_from_cache_file()
        if cached_albums:
            albums = cached_albums
            print(f"[DEBUG] Using {len(albums)} albums from disk cache, skipping Webflow fetch")
        else:
            print("[DEBUG] No valid disk cache, fetching from Webflow...")

            try:
                # Get webflow client from cache manager
                print("[DEBUG] Checking for webflow_cache_manager...")
                if (
                    not hasattr(self.ctx, "webflow_cache_manager")
                    or self.ctx.webflow_cache_manager is None
                ):
                    print("[DEBUG] Webflow cache manager NOT available")
                    self.logger.warning("Webflow cache manager not available")
                    return

                print("[DEBUG] Webflow cache manager found")

                webflow_client = self.ctx.webflow_cache_manager.client
                if not webflow_client:
                    print("[DEBUG] Webflow client is None")
                    self.logger.warning("Webflow client not available")
                    return

                print(
                    f"[DEBUG] Webflow client OK, fetching albums from collection {webflow_client.config.collection_id_albums}"
                )

                # Fetch all albums with pagination (Webflow limit is 100 per request)
                # Total albums: 487, so we need 5 requests
                all_albums = []
                offset = 0
                limit = 100

                while True:
                    print(f"[DEBUG] Fetching albums offset={offset}, limit={limit}")
                    albums_batch = webflow_client.get_collection_items(
                        webflow_client.config.collection_id_albums, limit=limit, offset=offset
                    )

                    if not albums_batch:
                        break

                    all_albums.extend(albums_batch)
                    print(
                        f"[DEBUG] Got {len(albums_batch)} albums, total so far: {len(all_albums)}"
                    )

                    # If we got fewer than limit, we've reached the end
                    if len(albums_batch) < limit:
                        break

                    offset += limit

                print(f"[DEBUG] Webflow returned: {len(all_albums)} total albums")

                if not all_albums:
                    print("[DEBUG] No albums returned from Webflow")
                    self.logger.warning("No albums fetched from Webflow")
                    return

                albums = all_albums
                self.logger.info(f"Fetched {len(albums)} total albums from Webflow")

                # Save to disk cache
                self._save_albums_to_cache_file(albums)

            except Exception as e:
                self.logger.error(f"Error fetching albums: {e}")
                return

        # Filter albums for this band and type
        filtered_albums = []
        print(
            f"[DEBUG] Filtering {len(albums)} albums for band_id={self.band_id}, type={album_type}"
        )

        # Debug: show first album's all fields and collect unique type values
        unique_types = set()
        if albums:
            first_album = albums[0]
            field_data = first_album.get("fieldData", {})
            print(f"[DEBUG] First album fieldData keys: {list(field_data.keys())}")
            print(
                f"[DEBUG] Sample album 0: name={field_data.get('name')}, band={field_data.get('band')}, type={field_data.get('type')}"
            )

            # Collect all unique type values to understand the data
            type_examples = {}  # Map type UUID to example album names
            for album in albums:
                album_type_val = album.get("fieldData", {}).get("type")
                album_name = album.get("fieldData", {}).get("name", "Unknown")
                if album_type_val:
                    unique_types.add(str(album_type_val))
                    # Store first 3 examples for each type
                    if album_type_val not in type_examples:
                        type_examples[album_type_val] = []
                    if len(type_examples[album_type_val]) < 3:
                        type_examples[album_type_val].append(album_name)

            print(f"[DEBUG] Found {len(unique_types)} unique type values: {sorted(unique_types)}")
            print("[DEBUG] Type UUID examples:")
            for type_uuid, examples in sorted(type_examples.items()):
                print(f"  {type_uuid}: {', '.join(examples)}")

        # Count matches
        band_match_count = 0
        type_match_count = 0

        for album in albums:
            field_data = album.get("fieldData", {})

            # Check if album belongs to this band
            album_band_id = field_data.get("band")
            album_name = field_data.get("name", "Unknown")
            album_type_value = field_data.get("type", "")

            self.logger.debug(
                f"Album: {album_name}, band_id={album_band_id}, type={album_type_value}"
            )

            if album_band_id != self.band_id:
                continue

            band_match_count += 1

            # Filter by type using UUID mapping
            album_type_uuid = field_data.get("type", "")

            # Map UUID to type name
            mapped_type = ALBUM_TYPE_UUIDS.get(
                album_type_uuid, "etc"
            )  # Default to "etc" for unknown types

            # Check if this album's type matches the requested tab type
            if mapped_type == album_type:
                filtered_albums.append(album)
                type_match_count += 1

        # Cache the filtered albums
        print(
            f"[DEBUG] Band matches: {band_match_count}/{len(albums)}, Type matches: {type_match_count}, Caching {len(filtered_albums)} albums for type={album_type}"
        )
        self.albums_by_type[album_type] = filtered_albums
        self.logger.info(f"Fetched {len(filtered_albums)} albums for type: {album_type}")

    def _get_image_cache_path(self, url: str) -> Path:
        """Get the cache file path for a transformed image."""
        import hashlib

        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.images_cache_dir / f"{url_hash}.png"

    def _load_album_covers_for_tab(self, tab_index: int):
        """Load album cover images for the selected tab.

        Args:
            tab_index: 0=ALBUM, 1=EP, 2=LIVE, 3=ETC
        """
        print(f"[DEBUG] _load_album_covers_for_tab called with tab_index={tab_index}")
        self.logger.info(f"_load_album_covers_for_tab called with tab_index={tab_index}")

        # Map tab index to album type
        type_map = {0: "album", 1: "ep", 2: "live", 3: "etc"}
        album_type = type_map.get(tab_index, "album")

        self.logger.info(f"Mapped tab_index {tab_index} to album_type '{album_type}'")

        # Fetch albums for this type
        print(f"[DEBUG] Calling _fetch_albums_for_band for type={album_type}")
        self._fetch_albums_for_band(album_type)

        # Get albums for this type
        albums = self.albums_by_type.get(album_type, [])
        print(f"[DEBUG] Got {len(albums)} albums from cache for type={album_type}")

        # Extract cover image URLs
        self.matrix_src_paths = []
        # Load and transform images (limit to 15 for grid)
        for album in albums[:15]:
            field_data = album.get("fieldData", {})

            # Try thumbnail first, fall back to cover
            cover_url = None
            if "thumbnail-200-x-200" in field_data and field_data["thumbnail-200-x-200"]:
                cover_url = field_data["thumbnail-200-x-200"].get("url")
            elif "cover" in field_data and field_data["cover"]:
                cover_url = field_data["cover"].get("url")

            if cover_url:
                # Check if we have a cached transformed image
                cache_path = self._get_image_cache_path(cover_url)
                if cache_path.exists():
                    # Use cached transformed image
                    self.matrix_src_paths.append(str(cache_path))
                else:
                    # Will need to download and transform
                    self.matrix_src_paths.append(cover_url)
                self.logger.info(
                    f"Added album cover: {album.get('fieldData', {}).get('name', 'Unknown')} -> {cover_url}"
                )
            else:
                self.logger.warning(
                    f"No cover URL for album: {album.get('fieldData', {}).get('name', 'Unknown')}"
                )

        # Clear cache when tab changes
        self.matrix_images_cache = []

        self.logger.info(f"Loaded {len(self.matrix_src_paths)} album covers for {album_type}")

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
            # Handle tabs click
        if self.tabs and event.type == pygame.MOUSEBUTTONDOWN:
            if self.tabs.handle_click(event.pos):
                return True

        return False

    def update(self, dt: float):
        """Update band details state."""
        pass

    def draw(self, screen: pygame.Surface):
        """Draw band details screen."""
        # Clear screen
        screen.fill(self.bg)

        # Debug: confirm draw is being called
        if not hasattr(self, "_draw_called"):
            print("[DEBUG] BandDetailsScene.draw() called for the first time")
            self.logger.info("BandDetailsScene.draw() called for the first time")
            self._draw_called = True
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
        if self.logo_surface:
            # Calculate logo position - centered vertically with border line
            logo_x = margin_left + 35 + logo_padding  # 35px to border edge + padding
            # The logo should be centered on the border line
            # border_y is the Y coordinate where the border is drawn (center of the 6px line)
            # Apply vertical offset for square/tall logos (shifts them up)
            logo_y = border_y - (self.logo_surface.get_height() // 2) + self.logo_vertical_offset

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

        # Create/update tabs based on language
        from core.localization import get_language, t

        current_language = get_language()
        if self.tabs is None or self._cached_language != current_language:
            tab_labels = [
                t("band_details.albums"),
                t("band_details.ep"),
                t("band_details.live"),
                t("band_details.etc"),
            ]
            # Preserve active tab index when recreating
            active_index = self.tabs.active_index if self.tabs else 0
            self.tabs = Tabs(tab_labels, self.color)
            self.tabs.active_index = active_index
            self._cached_language = current_language

        # Draw tabs
        content_y = layout_info["content_start_y"]
        tabs_x = margin_left + 35 + 24  # Match title card padding
        tabs_y = content_y + 20  # Same offset as visualizers scene
        self.tabs.draw(screen, tabs_x, tabs_y)

        # Draw content based on active tab
        content_text_y = tabs_y + 60

        # Load album covers for the active tab (only when tab changes)
        if self._last_loaded_tab_index != self.tabs.active_index:
            print(f"[DEBUG] Tab changed to {self.tabs.active_index}, loading album covers")
            self._load_album_covers_for_tab(self.tabs.active_index)
            self._last_loaded_tab_index = self.tabs.active_index
            print(
                f"[DEBUG] After _load_album_covers_for_tab, matrix_src_paths has {len(self.matrix_src_paths)} items"
            )

        # Display album covers if available
        if self.matrix_src_paths:
            # Use exact primary color from theme for bright highlights to match UI
            style = self.theme.get("style", {})
            colors = style.get("colors", {})

            # Primary color (#E91E63) - matches the hot pink in UI
            primary_rgb = tuple(colors.get("primary", (233, 30, 99)))
            # Pink 700 (#C2185B) for shadows - deeper but still vibrant
            dim_rgb = (194, 24, 91)
            # Dark background
            bg_rgb = tuple(colors.get("background", (8, 6, 16)))

            # Display images in a 3x5 grid layout
            img_size = 180
            cols = 5
            rows = 3
            top_margin = 30
            side_margin = 30  # 30px from container edges

            # Calculate container width from actual screen margins
            # The container spans from margin_left to (w - margin_right)
            container_width = w - margin_left - margin_right
            available_height = h - content_text_y - 100

            # Calculate spacing: leftmost at 30px from margin_left, rightmost at 30px from right edge
            # Available space for images and gaps: container_width - (2 * side_margin)
            available_width = container_width - (2 * side_margin)
            total_img_width = cols * img_size
            # Spacing between images (not at edges)
            horizontal_spacing = (available_width - total_img_width) / (cols - 1) if cols > 1 else 0
            vertical_spacing = (
                (available_height - (rows * img_size)) / (rows - 1) if rows > 1 else 0
            )

            # Generate cached images only once
            if not self.matrix_images_cache:
                self.logger.info("Generating matrix transformations (one-time)...")
                for src_path in self.matrix_src_paths:
                    # Check if this is a cached file path or URL
                    if src_path.startswith("http"):
                        # It's a URL - need to download and transform
                        cache_path = self._get_image_cache_path(src_path)

                        matrix_image = transform_to_matrix(
                            src_path,
                            enable_flicker=False,
                            color_bright=primary_rgb,
                            color_dim=dim_rgb,
                            color_bg=bg_rgb,
                        )

                        if matrix_image:
                            # Scale to 180x180
                            scaled_image = pygame.transform.smoothscale(
                                matrix_image, (img_size, img_size)
                            )

                            # Save to disk cache
                            try:
                                pygame.image.save(scaled_image, str(cache_path))
                                print(
                                    f"[DEBUG] Saved transformed image to cache: {cache_path.name}"
                                )
                            except Exception as e:
                                self.logger.error(f"Error saving image cache: {e}")

                            self.matrix_images_cache.append(scaled_image)
                        else:
                            self.matrix_images_cache.append(None)
                    else:
                        # It's a cached file path - load from disk
                        try:
                            cached_image = pygame.image.load(src_path)
                            print(
                                f"[DEBUG] Loaded transformed image from cache: {Path(src_path).name}"
                            )
                            self.matrix_images_cache.append(cached_image)
                        except Exception as e:
                            self.logger.error(f"Error loading cached image: {e}")
                            self.matrix_images_cache.append(None)

                self.logger.info(f"Cached {len(self.matrix_images_cache)} matrix images")

            # Draw cached images in 3x5 grid with borders
            # Start 30px from the actual left margin (not tabs_x)
            start_x = margin_left + side_margin
            start_y = content_text_y + top_margin
            border_width = 3

            img_index = 0
            for row in range(rows):
                for col in range(cols):
                    if img_index < len(self.matrix_images_cache):
                        cached_image = self.matrix_images_cache[img_index]
                        if cached_image:
                            # Calculate position
                            x_pos = start_x + col * (img_size + horizontal_spacing)
                            y_pos = start_y + row * (img_size + vertical_spacing)

                            # Draw border rectangle
                            border_rect = pygame.Rect(
                                int(x_pos) - border_width,
                                int(y_pos) - border_width,
                                img_size + (border_width * 2),
                                img_size + (border_width * 2),
                            )
                            pygame.draw.rect(screen, primary_rgb, border_rect, border_width)
                            # Draw image
                            screen.blit(cached_image, (int(x_pos), int(y_pos)))
                        img_index += 1
        else:
            # No albums available - show message
            no_albums_surface = render_mixed_text("No albums available", 36, "primary", self.color)
            screen.blit(no_albums_surface, (tabs_x, content_text_y))

        # Draw scanlines and footer
        draw_scanlines(screen)
        self.settings_rect = draw_footer(
            screen,
            self.color,
            show_settings=True,
        )
