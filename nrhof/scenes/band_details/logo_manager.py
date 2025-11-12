#!/usr/bin/env python3
"""Logo manager for band details scene."""
import threading

import pygame

from nrhof.integrations.image_cache import ImageCache
from nrhof.ui.logo_utils import calculate_logo_size


class LogoManager:
    """Handles loading and sizing band logos."""

    def __init__(self, logger, image_cache: ImageCache, color: tuple):
        self.logger = logger
        self.image_cache = image_cache
        self.color = color
        self.logo_surface = None
        self.logo_vertical_offset = 0
        self._loading_logo = False
        self._logo_url = None

    def load_logo_async(self, logo_url: str, band_name: str):
        """Start loading logo in background thread.

        Args:
            logo_url: URL to the logo image
            band_name: Name of the band (for logging)
        """
        if not logo_url or self._loading_logo:
            return

        self._logo_url = logo_url
        self._loading_logo = True
        self.logo_surface = None
        thread = threading.Thread(
            target=self._load_logo,
            args=(band_name,),
            daemon=True,
            name=f"logo_load_{band_name}",
        )
        thread.start()

    def stop_loading(self):
        """Stop any ongoing logo loading."""
        self._loading_logo = False

    def _load_logo(self, band_name: str):
        """Load logo from cache or download it (runs in background thread)."""
        if not self._logo_url:
            return

        try:
            # Use ImageCache to get the logo (handles caching and scaling)
            surface = self.image_cache.get_image(
                self._logo_url,
                max_size=(600, 150),
                fill_color=self.color,
            )

            if surface:
                # Apply smart sizing based on aspect ratio
                width, height, vertical_offset = calculate_logo_size(surface)
                self.logo_vertical_offset = vertical_offset

                # Scale to calculated size
                self.logo_surface = pygame.transform.smoothscale(surface, (width, height))
                self.logger.info(
                    f"Logo loaded for {band_name} ({width}x{height}, offset={vertical_offset})"
                )
            else:
                self.logger.warning(f"Failed to load logo for {band_name}")

        except Exception as e:
            self.logger.error(f"Error loading logo: {e}")
        finally:
            self._loading_logo = False
