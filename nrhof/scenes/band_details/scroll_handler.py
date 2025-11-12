#!/usr/bin/env python3
"""Scroll handler for band details scene.

Manages:
- Scroll state (offset, velocity, max scroll)
- Mouse wheel scrolling
- Touch drag scrolling
- Scroll clamping and bounds checking
"""

import pygame


class ScrollHandler:
    """Handles scrolling logic for the album grid."""

    def __init__(self, scroll_speed: int = 20):
        """Initialize scroll handler.

        Args:
            scroll_speed: Pixels to scroll per mouse wheel notch
        """
        self.scroll_speed = scroll_speed

        # Scroll state
        self.scroll_offset = 0
        self.scroll_velocity = 0
        self.max_scroll = 0

        # Drag state
        self.is_dragging = False
        self.drag_start_y = 0
        self.drag_start_scroll = 0

    def reset(self):
        """Reset scroll position (called when changing tabs)."""
        self.scroll_offset = 0
        self.scroll_velocity = 0
        self.is_dragging = False

    def is_scroll_enabled(self, num_items: int, threshold: int = 15) -> bool:
        """Check if scrolling should be enabled based on number of items.

        Args:
            num_items: Number of items in the grid
            threshold: Minimum items required to enable scrolling

        Returns:
            True if scrolling should be enabled
        """
        return num_items > threshold

    def handle_wheel_scroll(self, event: pygame.event.Event, num_items: int) -> bool:
        """Handle mouse wheel scrolling.

        Args:
            event: Pygame mouse wheel event
            num_items: Number of items in the grid

        Returns:
            True if event was handled
        """
        if not self.is_scroll_enabled(num_items):
            return False

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * self.scroll_speed
            self._clamp_scroll()
            return True

        return False

    def start_drag(self, mouse_y: int) -> bool:
        """Start a drag scroll operation.

        Args:
            mouse_y: Current mouse Y position

        Returns:
            True if drag was started
        """
        self.is_dragging = True
        self.drag_start_y = mouse_y
        self.drag_start_scroll = self.scroll_offset
        return True

    def update_drag(self, mouse_y: int, num_items: int) -> bool:
        """Update drag scroll position.

        Args:
            mouse_y: Current mouse Y position
            num_items: Number of items in the grid

        Returns:
            True if drag was updated
        """
        if not self.is_dragging:
            return False

        if not self.is_scroll_enabled(num_items):
            return False

        # Calculate drag distance
        drag_delta = mouse_y - self.drag_start_y
        # Update scroll (invert delta so dragging down scrolls up)
        self.scroll_offset = self.drag_start_scroll - drag_delta
        self._clamp_scroll()
        return True

    def end_drag(self) -> bool:
        """End a drag scroll operation.

        Returns:
            True if drag was ended
        """
        if self.is_dragging:
            self.is_dragging = False
            return True
        return False

    def set_max_scroll(self, max_scroll: int):
        """Set the maximum scroll offset.

        Args:
            max_scroll: Maximum scroll offset in pixels
        """
        self.max_scroll = max_scroll
        self._clamp_scroll()

    def _clamp_scroll(self):
        """Clamp scroll offset to valid range."""
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

    def get_scroll_offset(self) -> int:
        """Get current scroll offset.

        Returns:
            Current scroll offset in pixels
        """
        return self.scroll_offset
