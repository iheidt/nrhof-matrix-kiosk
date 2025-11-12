#!/usr/bin/env python3
"""Album grid renderer for band details scene."""
from pathlib import Path

import pygame

from nrhof.core.localization import t
from nrhof.core.theme_loader import get_theme_loader
from nrhof.ui.fonts import render_localized_text, render_mixed_text
from nrhof.ui.image_transformer import transform_to_matrix


class AlbumGridRenderer:
    """Handles rendering of album grid with scrolling and metadata overlays."""

    def __init__(self, logger):
        self.logger = logger

    def render_grid(
        self,
        screen: pygame.Surface,
        matrix_src_paths: list,
        matrix_images_cache: list,
        album_metadata: list,
        scroll_offset: int,
        flame_icon: pygame.Surface,
        down_arrow_icon: pygame.Surface,
        theme: dict,
        margin_left: int,
        margin_right: int,
        content_text_y: int,
        get_image_cache_path_func,
    ) -> tuple[list, int]:
        """Render the album grid with scrolling.

        Returns:
            Tuple of (updated_matrix_images_cache, max_scroll)
        """
        w, h = screen.get_size()
        style = theme.get("style", {})
        colors = style.get("colors", {})

        primary_rgb = tuple(colors.get("primary", (233, 30, 99)))
        dim_rgb = (194, 24, 91)
        bg_rgb = tuple(colors.get("background", (8, 6, 16)))

        # Grid layout constants
        img_size = 180
        cols = 5
        top_margin = 30
        side_margin = 30

        # Calculate dimensions
        container_width = w - margin_left - margin_right
        available_height = h - content_text_y - 150
        available_width = container_width - (2 * side_margin)
        total_img_width = cols * img_size
        horizontal_spacing = (available_width - total_img_width) / (cols - 1) if cols > 1 else 0
        vertical_spacing = 30

        total_albums = len(matrix_images_cache)
        total_rows = (total_albums + cols - 1) // cols
        total_content_height = (
            (total_rows * img_size) + ((total_rows - 1) * vertical_spacing) + (top_margin * 2)
        )

        viewport_height = available_height
        max_scroll = max(0, total_content_height - viewport_height)

        # Generate cached images once
        if not matrix_images_cache:
            matrix_images_cache = self._generate_cached_images(
                matrix_src_paths, get_image_cache_path_func, img_size, primary_rgb, dim_rgb, bg_rgb
            )

        # Create content surface and render albums
        border_width = 3
        viewport_rect = pygame.Rect(
            margin_left + side_margin - border_width,
            content_text_y + top_margin - border_width,
            int(available_width) + (border_width * 2),
            int(viewport_height) + border_width,
        )

        content_width = int(available_width) + (border_width * 2)
        content_height_with_borders = int(total_content_height) + border_width
        content_surface = pygame.Surface(
            (content_width, content_height_with_borders), pygame.SRCALPHA
        )
        content_surface.fill((0, 0, 0, 0))

        # Draw all albums
        self._draw_albums(
            content_surface,
            matrix_images_cache,
            album_metadata,
            total_rows,
            cols,
            img_size,
            horizontal_spacing,
            vertical_spacing,
            border_width,
            primary_rgb,
            flame_icon,
        )

        # Blit scrolled content
        screen.set_clip(viewport_rect)
        screen.blit(
            content_surface,
            (viewport_rect.x, viewport_rect.y),
            area=pygame.Rect(0, int(scroll_offset), content_width, int(viewport_height)),
        )
        screen.set_clip(None)

        # Draw more indicator
        if max_scroll > 0 and down_arrow_icon:
            self._render_more_indicator(
                screen,
                down_arrow_icon,
                scroll_offset,
                total_rows,
                img_size,
                vertical_spacing,
                viewport_height,
                w,
                h,
            )

        return matrix_images_cache, max_scroll

    def _generate_cached_images(
        self, matrix_src_paths, get_image_cache_path_func, img_size, primary_rgb, dim_rgb, bg_rgb
    ):
        """Generate and cache transformed album images."""
        self.logger.info("Generating matrix transformations (one-time)...")
        cached_images = []

        for src_path in matrix_src_paths:
            if src_path.startswith("http"):
                cache_path = get_image_cache_path_func(src_path)
                matrix_image = transform_to_matrix(
                    src_path,
                    enable_flicker=False,
                    color_bright=primary_rgb,
                    color_dim=dim_rgb,
                    color_bg=bg_rgb,
                )
                if matrix_image:
                    scaled_image = pygame.transform.smoothscale(matrix_image, (img_size, img_size))
                    try:
                        pygame.image.save(scaled_image, str(cache_path))
                    except Exception as e:
                        self.logger.error(f"Error saving image cache: {e}")
                    cached_images.append(scaled_image)
                else:
                    cached_images.append(None)
            else:
                try:
                    cached_image = pygame.image.load(src_path)
                    cached_images.append(cached_image)
                except Exception as e:
                    self.logger.error(f"Error loading cached image: {e}")
                    cached_images.append(None)

        self.logger.info(f"Cached {len(cached_images)} matrix images")
        return cached_images

    def _draw_albums(
        self,
        surface,
        matrix_images_cache,
        album_metadata,
        total_rows,
        cols,
        img_size,
        horizontal_spacing,
        vertical_spacing,
        border_width,
        primary_rgb,
        flame_icon,
    ):
        """Draw all album covers with borders and metadata."""
        img_index = 0
        for row in range(total_rows):
            for col in range(cols):
                if img_index < len(matrix_images_cache):
                    cached_image = matrix_images_cache[img_index]
                    if cached_image:
                        x_pos = border_width + (col * (img_size + horizontal_spacing))
                        y_pos = border_width + (row * (img_size + vertical_spacing))

                        # Border
                        border_rect = pygame.Rect(
                            int(x_pos) - border_width,
                            int(y_pos) - border_width,
                            img_size + (border_width * 2),
                            img_size + (border_width * 2),
                        )
                        pygame.draw.rect(surface, primary_rgb, border_rect, border_width)

                        # Image
                        surface.blit(cached_image, (int(x_pos), int(y_pos)))

                        # Metadata overlay
                        if img_index < len(album_metadata):
                            self._render_album_metadata(
                                surface,
                                album_metadata[img_index],
                                x_pos,
                                y_pos,
                                img_size,
                                primary_rgb,
                                flame_icon,
                            )

                    img_index += 1

    def _render_album_metadata(
        self, surface, metadata, x_pos, y_pos, img_size, primary_rgb, flame_icon
    ):
        """Render album name and score overlay on album cover."""
        album_name = metadata.get("name", "")
        score = metadata.get("score")

        # Album name (bottom-left)
        # Use render_localized_text for consistent font treatment with marquee scroller
        # English text uses IBM Plex Mono Italic, Japanese text uses Noto Sans JP
        if album_name:
            # Lowercase for English text (matching marquee scroller behavior)
            display_name = album_name.lower()
            max_width = img_size - 20
            truncated_name = display_name
            name_surface = render_localized_text(
                truncated_name,
                18,
                "primary",  # Uses IBM Plex Mono Italic for English
                primary_rgb,
            )
            # Truncate if too wide
            while name_surface.get_width() > max_width and len(truncated_name) > 0:
                truncated_name = truncated_name[:-1]
                name_surface = render_localized_text(
                    truncated_name,
                    18,
                    "primary",
                    primary_rgb,
                )
            name_x = int(x_pos) + 10
            name_y = int(y_pos) + img_size - name_surface.get_height() - 10
            surface.blit(name_surface, (name_x, name_y))

        # Score (top-right) + flame if >= 9.0
        if score is not None:
            # Go up from nrhof/scenes/band_details/album_grid_renderer.py to project root
            project_root = Path(__file__).parent.parent.parent.parent
            score_font_path = project_root / "assets/fonts/IBMPlexMono-SemiBoldItalic.ttf"
            score_font = pygame.font.Font(str(score_font_path), 30)
            score_text = f"{score:.1f}"
            score_surface = score_font.render(score_text, True, primary_rgb)
            flame_width = flame_icon.get_width() + 5 if score >= 9.0 and flame_icon else 0
            score_x = int(x_pos) + img_size - score_surface.get_width() - flame_width - 15
            score_y = int(y_pos) + 10
            surface.blit(score_surface, (score_x, score_y))

            if score >= 9.0 and flame_icon:
                flame_x = score_x + score_surface.get_width() + 5
                flame_y = score_y + (score_surface.get_height() - flame_icon.get_height()) // 2
                surface.blit(flame_icon, (flame_x, flame_y))

    def _render_more_indicator(
        self,
        screen,
        down_arrow_icon,
        scroll_offset,
        total_rows,
        img_size,
        vertical_spacing,
        viewport_height,
        screen_width,
        screen_height,
    ):
        """Render the 'more' indicator at the bottom of the screen."""
        last_row_top = (total_rows - 1) * (img_size + vertical_spacing)
        last_row_visible_at_scroll = max(0, last_row_top - viewport_height + img_size)

        if scroll_offset >= last_row_visible_at_scroll:
            opacity = 0
        else:
            fade_range = last_row_visible_at_scroll
            opacity = int(255 * (1 - (scroll_offset / fade_range))) if fade_range > 0 else 255

        opacity = max(0, min(255, opacity))

        if opacity > 0:
            more_text = t("band_details.more")
            theme_loader = get_theme_loader()
            style = theme_loader.load_style("pipboy")
            colors = style.get("colors", {})
            disabled_color = colors.get("disabled", (116, 15, 49))

            more_surface = render_mixed_text(more_text, 18, "primary", disabled_color)
            more_surface.set_alpha(opacity)

            icon_with_alpha = down_arrow_icon.copy()
            icon_with_alpha.set_alpha(opacity)

            text_width = more_surface.get_width()
            text_height = more_surface.get_height()
            icon_width = icon_with_alpha.get_width()
            icon_height = icon_with_alpha.get_height()
            icon_spacing = 10

            total_width = icon_width + icon_spacing + text_width + icon_spacing + icon_width
            center_x = screen_width // 2
            start_x = center_x - (total_width // 2)

            base_y = screen_height - 110
            icon_y = base_y
            text_y = base_y - (text_height - icon_height)

            screen.blit(icon_with_alpha, (start_x, icon_y))
            screen.blit(more_surface, (start_x + icon_width + icon_spacing, text_y))
            screen.blit(
                icon_with_alpha,
                (start_x + icon_width + icon_spacing + text_width + icon_spacing, icon_y),
            )
