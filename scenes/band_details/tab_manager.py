#!/usr/bin/env python3
"""Tab manager for band details scene.

Manages:
- Tab creation based on available album types
- Tab state (active index, labels, type mapping)
- Language-aware tab recreation
- Tab rendering and click handling
"""

import logging

import pygame

from core.localization import get_language, t
from ui.tabs import Tabs


class TabManager:
    """Manages tabs for the band details scene."""

    def __init__(self, color: tuple, logger: logging.Logger = None):
        """Initialize tab manager.

        Args:
            color: Primary color for tabs
            logger: Optional logger instance
        """
        self.color = color
        self.logger = logger or logging.getLogger(__name__)

        # Tab state
        self.tabs = None
        self._cached_language = None
        self._last_loaded_tab_index = None
        self.tab_type_map = []

    def reset_for_new_band(self):
        """Reset tabs when switching to a new band."""
        if self.tabs:
            self.tabs.active_index = 0
        self._last_loaded_tab_index = None
        self._cached_language = None

    def should_reload_tab(self) -> bool:
        """Check if the current tab needs to be reloaded.

        Returns:
            True if tab content should be reloaded
        """
        if not self.tabs:
            return False
        return self._last_loaded_tab_index != self.tabs.active_index

    def get_active_album_type(self) -> str | None:
        """Get the album type for the currently active tab.

        Returns:
            Album type string ('album', 'ep', 'live', 'etc') or None
        """
        if not self.tabs or not self.tab_type_map:
            return None
        if self.tabs.active_index >= len(self.tab_type_map):
            return None
        return self.tab_type_map[self.tabs.active_index]

    def mark_tab_loaded(self):
        """Mark the current tab as loaded."""
        if self.tabs:
            self._last_loaded_tab_index = self.tabs.active_index

    def update_tabs(self, album_data_manager, band_id: str, webflow_cache_manager) -> bool:
        """Update tabs based on available album types and current language.

        Args:
            album_data_manager: AlbumDataManager instance
            band_id: Current band ID
            webflow_cache_manager: Webflow cache manager

        Returns:
            True if tabs were recreated
        """
        current_language = get_language()

        # Only recreate tabs if language changed or tabs don't exist
        if self.tabs is not None and self._cached_language == current_language:
            return False

        # Fetch all album types to determine which tabs to show
        album_types = ["album", "ep", "live", "etc"]
        for album_type in album_types:
            album_data_manager.fetch_albums_for_band(band_id, album_type, webflow_cache_manager)

        # Build tab labels and type map based on which types have albums
        tab_labels = []
        self.tab_type_map = []

        for album_type in album_types:
            albums = album_data_manager.albums_by_type.get(album_type, [])
            if albums:  # Only show tab if there are albums of this type
                # Get localized label
                label_key = f"band_details.{album_type}"
                label = t(label_key)
                tab_labels.append(label)
                self.tab_type_map.append(album_type)

        # Only create tabs if we have at least one type with albums
        if tab_labels:
            # Preserve active tab index when recreating
            active_index = self.tabs.active_index if self.tabs else 0
            active_index = min(active_index, len(tab_labels) - 1)
            self.tabs = Tabs(tab_labels, self.color)
            self.tabs.active_index = active_index
            # Don't reset _last_loaded_tab_index - preserve it so we don't reload album covers
            # when only the language changes (tabs are just being relabeled)
        else:
            self.tabs = None

        self._cached_language = current_language
        return True

    def handle_click(self, mouse_pos: tuple) -> bool:
        """Handle mouse click on tabs.

        Args:
            mouse_pos: Mouse position tuple (x, y)

        Returns:
            True if click was handled
        """
        if self.tabs:
            return self.tabs.handle_click(mouse_pos)
        return False

    def draw(self, screen: pygame.Surface, x: int, y: int):
        """Draw tabs.

        Args:
            screen: Surface to draw on
            x: X position
            y: Y position
        """
        if self.tabs:
            self.tabs.draw(screen, x, y)

    def has_tabs(self) -> bool:
        """Check if tabs exist.

        Returns:
            True if tabs are initialized
        """
        return self.tabs is not None
