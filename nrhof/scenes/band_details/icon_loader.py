#!/usr/bin/env python3
"""Icon loader for band details scene."""
from pathlib import Path

import pygame

from nrhof.core.theme_loader import get_theme_loader
from nrhof.ui.icons import load_icon


class IconLoader:
    """Handles loading and colorizing icons from theme."""

    def __init__(self, logger):
        self.logger = logger

    def load_down_arrow_icon(self) -> pygame.Surface | None:
        """Load the down arrow icon for the more indicator."""
        try:
            # Go up from nrhof/scenes/band_details/icon_loader.py to project root
            project_root = Path(__file__).parent.parent.parent.parent
            icon_path = project_root / "assets/icons/icon_down_arrow.svg"
            if not icon_path.exists():
                self.logger.warning(f"Down arrow icon not found: {icon_path}")
                return None

            # Get disabled color from theme
            theme_loader = get_theme_loader()
            style = theme_loader.load_style("pipboy")
            colors = style.get("colors", {})
            disabled_color = colors.get("disabled", (116, 15, 49))

            # Convert to RGB tuple if it's a hex string
            if isinstance(disabled_color, str):
                disabled_rgb = tuple(
                    int(disabled_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)
                )
            else:
                disabled_rgb = tuple(disabled_color[:3])

            # Load icon with disabled color - 15px wide
            icon_size = 15
            icon = load_icon(icon_path, (icon_size, icon_size), fill_color=disabled_rgb)

            if icon:
                self.logger.info(f"Loaded down arrow icon with color {disabled_rgb}: {icon_path}")
            else:
                self.logger.warning(f"Failed to load down arrow icon: {icon_path}")

            return icon

        except Exception as e:
            self.logger.error(f"Error loading down arrow icon: {e}")
            return None

    def load_flame_icon(self) -> pygame.Surface | None:
        """Load the flame icon for high scores (>= 9.0)."""
        try:
            # Go up from nrhof/scenes/band_details/icon_loader.py to project root
            project_root = Path(__file__).parent.parent.parent.parent
            icon_path = project_root / "assets/icons/icon_flame.svg"
            if not icon_path.exists():
                self.logger.warning(f"Flame icon not found: {icon_path}")
                return None

            # Get primary color from theme
            theme_loader = get_theme_loader()
            style = theme_loader.load_style("pipboy")
            colors = style.get("colors", {})
            primary_color = colors.get("primary", (233, 30, 99))

            # Convert to RGB tuple if it's a hex string
            if isinstance(primary_color, str):
                primary_rgb = tuple(
                    int(primary_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)
                )
            else:
                primary_rgb = tuple(primary_color[:3])

            # Load icon with primary color - 20px wide
            icon_size = 20
            icon = load_icon(icon_path, (icon_size, icon_size), fill_color=primary_rgb)

            if icon:
                self.logger.info(f"Loaded flame icon with color {primary_rgb}: {icon_path}")
            else:
                self.logger.warning(f"Failed to load flame icon: {icon_path}")

            return icon

        except Exception as e:
            self.logger.error(f"Error loading flame icon: {e}")
            return None
