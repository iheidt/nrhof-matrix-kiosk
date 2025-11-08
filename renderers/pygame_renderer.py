#!/usr/bin/env python3
"""
Pygame renderer implementation.

Current rendering backend using pygame.
"""

import pygame

from .base import RendererBase
from .frame_state import FrameState, ShapeType


class PygameRenderer(RendererBase):
    """Pygame-based renderer."""

    def __init__(self, config: dict):
        """Initialize pygame renderer.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.screen: pygame.Surface = None
        self.font_cache = {}  # Cache fonts by (size, family)
        self.font_cache_max_size = 50  # Limit cache size

    def initialize(self):
        """Initialize pygame and create display."""
        import os

        pygame.init()

        # Get display configuration
        display_index = self.config.get("render", {}).get("display", 0)

        # Position window on correct display
        if display_index > 0:
            # Get desktop info to find secondary display position
            info = pygame.display.Info()
            # For macOS with extended display, position window far right
            # This assumes secondary display is to the right of primary
            primary_width = info.current_w
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{primary_width},0"

        flags = 0
        if self.config.get("render", {}).get("fullscreen", False):
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode(self.resolution, flags)
        pygame.display.set_caption(self.config.get("title", "NRHOF Kiosk"))

    def get_font(
        self,
        size: int,
        family: str = "monospace",
        bold: bool = False,
    ) -> pygame.font.Font:
        """Get or create a font from cache.

        Args:
            size: Font size
            family: Font family
            bold: Bold font

        Returns:
            pygame.Font instance
        """
        key = (size, family, bold)
        if key not in self.font_cache:
            # Evict oldest entry if cache is full
            if len(self.font_cache) >= self.font_cache_max_size:
                self.font_cache.pop(next(iter(self.font_cache)))

            if family == "monospace":
                self.font_cache[key] = pygame.font.Font(
                    pygame.font.match_font("courier", bold=bold),
                    size,
                )
            else:
                self.font_cache[key] = pygame.font.Font(
                    pygame.font.match_font("arial", bold=bold),
                    size,
                )
        return self.font_cache[key]

    def render(self, frame_state: FrameState):
        """Render a frame using pygame.

        Args:
            frame_state: Frame state with rendering commands
        """
        # Clear screen
        self.screen.fill(frame_state.clear_color)

        # Render shapes
        for shape in frame_state.shapes:
            self._render_shape(shape)

        # Render images (before text for layering)
        for image in frame_state.images:
            self._render_image(image)

        # Render videos
        for video in frame_state.videos:
            self._render_video(video)

        # Render text (on top)
        for text in frame_state.texts:
            self._render_text(text)

    def _render_shape(self, shape):
        """Render a shape."""
        color = shape.color[:3]  # RGB only for pygame

        if shape.shape_type == ShapeType.RECT:
            x, y = shape.position
            w, h = shape.size
            rect = pygame.Rect(int(x), int(y), int(w), int(h))
            pygame.draw.rect(self.screen, color, rect, shape.thickness)

        elif shape.shape_type == ShapeType.CIRCLE:
            x, y = shape.position
            radius = int(shape.size[0])
            pygame.draw.circle(self.screen, color, (int(x), int(y)), radius, shape.thickness)

        elif shape.shape_type == ShapeType.LINE:
            if len(shape.points) >= 2:
                points = [(int(x), int(y)) for x, y in shape.points]
                pygame.draw.lines(self.screen, color, False, points, shape.thickness)

        elif shape.shape_type == ShapeType.POLYGON:
            if len(shape.points) >= 3:
                points = [(int(x), int(y)) for x, y in shape.points]
                pygame.draw.polygon(self.screen, color, points, shape.thickness)

    def _render_text(self, text):
        """Render text."""
        font = self.get_font(text.font_size, text.font_family, text.bold)
        color = text.color[:3]  # RGB only
        surface = font.render(text.content, True, color)

        x, y = text.position
        if text.align == "center":
            rect = surface.get_rect(center=(int(x), int(y)))
            self.screen.blit(surface, rect)
        elif text.align == "right":
            rect = surface.get_rect(right=int(x), top=int(y))
            self.screen.blit(surface, rect)
        else:  # left
            self.screen.blit(surface, (int(x), int(y)))

    def _render_image(self, image):
        """Render an image/sprite."""
        surface = image.surface
        x, y = image.position

        # Apply alpha if needed
        if image.alpha < 255:
            surface = surface.copy()
            surface.set_alpha(image.alpha)

        # Apply rotation if needed
        if image.rotation != 0:
            surface = pygame.transform.rotate(surface, image.rotation)

        # Apply scaling if needed
        if image.size:
            surface = pygame.transform.scale(surface, (int(image.size[0]), int(image.size[1])))

        self.screen.blit(surface, (int(x), int(y)))

    def _render_video(self, video):
        """Render a video frame."""
        # Video frame is already a pygame surface
        x, y = video.position
        w, h = video.size

        if video.frame:
            scaled = pygame.transform.scale(video.frame, (int(w), int(h)))
            self.screen.blit(scaled, (int(x), int(y)))

    def present(self):
        """Present the frame to display."""
        pygame.display.flip()

    def shutdown(self):
        """Clean up pygame."""
        pygame.quit()

    def get_surface(self) -> pygame.Surface:
        """Get the pygame surface.

        Returns:
            pygame.Surface
        """
        return self.screen
