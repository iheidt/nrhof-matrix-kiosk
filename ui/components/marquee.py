#!/usr/bin/env python3
"""Marquee text scrolling widget."""

import time


class MarqueeText:
    """Manages scrolling text animation for text that's too long to fit."""

    def __init__(self, text: str, max_width: int, scroll_speed: float = 50.0, gap: int = 100):
        """Initialize marquee text.

        Args:
            text: Text to scroll
            max_width: Maximum width before scrolling
            scroll_speed: Pixels per second to scroll
            gap: Gap in pixels between end and start of loop
        """
        self.text = text
        self.max_width = max_width
        self.scroll_speed = scroll_speed
        self.gap = gap

        self.offset = 0.0
        self.last_update = time.time()

    def update(self, text_width: int) -> tuple[int, bool]:
        """Update scroll position and return current offset.

        Args:
            text_width: Actual rendered width of the text

        Returns:
            Tuple of (current x offset, should_draw_second_copy)
        """
        current_time = time.time()

        # If text fits, no scrolling needed
        if text_width <= self.max_width:
            return 0, False

        # Calculate delta time
        dt = current_time - self.last_update
        self.last_update = current_time

        # Update offset (scroll left = increase offset)
        self.offset += self.scroll_speed * dt

        # Loop when text has scrolled completely off screen
        loop_point = text_width + self.gap
        if self.offset >= loop_point:
            self.offset -= loop_point

        # Determine if we need to draw a second copy for seamless loop
        draw_second = self.offset > 0

        return int(self.offset), draw_second

    def reset(self, new_text: str = None):
        """Reset marquee to beginning.

        Args:
            new_text: Optional new text to display
        """
        if new_text is not None:
            self.text = new_text
        self.offset = 0.0
        self.last_update = time.time()
