#!/usr/bin/env python3
"""
Frame state data structures.

Defines the protocol for passing rendering data from scenes to renderers.
This is the contract between scene logic and rendering implementation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ShapeType(Enum):
    """Shape types for rendering."""

    RECT = "rect"
    CIRCLE = "circle"
    LINE = "line"
    POLYGON = "polygon"
    ELLIPSE = "ellipse"


@dataclass
class Shape:
    """Shape rendering command."""

    shape_type: ShapeType
    color: tuple[int, int, int, int]  # RGBA
    position: tuple[float, float]
    size: tuple[float, float] = (0, 0)  # width, height for rect, radius for circle
    thickness: int = 0  # 0 = filled
    points: list[tuple[float, float]] = field(default_factory=list)  # For polygon/line

    @classmethod
    def rect(
        cls,
        x: float,
        y: float,
        w: float,
        h: float,
        color: tuple[int, int, int],
        thickness: int = 0,
        alpha: int = 255,
    ):
        """Create a rectangle shape."""
        return cls(
            shape_type=ShapeType.RECT,
            color=(*color, alpha),
            position=(x, y),
            size=(w, h),
            thickness=thickness,
        )

    @classmethod
    def circle(
        cls,
        x: float,
        y: float,
        radius: float,
        color: tuple[int, int, int],
        thickness: int = 0,
        alpha: int = 255,
    ):
        """Create a circle shape."""
        return cls(
            shape_type=ShapeType.CIRCLE,
            color=(*color, alpha),
            position=(x, y),
            size=(radius, radius),
            thickness=thickness,
        )

    @classmethod
    def line(
        cls,
        points: list[tuple[float, float]],
        color: tuple[int, int, int],
        thickness: int = 1,
        alpha: int = 255,
    ):
        """Create a line/polyline shape."""
        return cls(
            shape_type=ShapeType.LINE,
            color=(*color, alpha),
            position=(0, 0),
            thickness=thickness,
            points=points,
        )

    @classmethod
    def polygon(
        cls,
        points: list[tuple[float, float]],
        color: tuple[int, int, int],
        thickness: int = 0,
        alpha: int = 255,
    ):
        """Create a polygon shape."""
        return cls(
            shape_type=ShapeType.POLYGON,
            color=(*color, alpha),
            position=(0, 0),
            thickness=thickness,
            points=points,
        )


@dataclass
class Text:
    """Text rendering command."""

    content: str
    position: tuple[float, float]
    color: tuple[int, int, int, int]  # RGBA
    font_size: int = 24
    font_family: str = "monospace"
    bold: bool = False
    italic: bool = False
    align: str = "left"  # left, center, right
    font_type: str = "primary"  # primary, secondary, or label

    @classmethod
    def create(
        cls,
        content: str,
        x: float,
        y: float,
        color: tuple[int, int, int],
        font_size: int = 24,
        mono: bool = True,
        alpha: int = 255,
    ):
        """Create a text rendering command."""
        return cls(
            content=content,
            position=(x, y),
            color=(*color, alpha),
            font_size=font_size,
            font_family="monospace" if mono else "sans-serif",
        )


@dataclass
class Image:
    """Image/sprite rendering command."""

    surface: Any  # pygame.Surface or image data
    position: tuple[float, float]
    size: tuple[float, float] | None = None  # None = original size
    alpha: int = 255
    rotation: float = 0.0  # degrees

    @classmethod
    def create(cls, surface: Any, x: float, y: float, alpha: int = 255):
        """Create an image rendering command."""
        return cls(surface=surface, position=(x, y), alpha=alpha)


@dataclass
class Video:
    """Video frame rendering command."""

    frame: Any  # Video frame data
    position: tuple[float, float]
    size: tuple[float, float]

    @classmethod
    def create(cls, frame: Any, x: float, y: float, w: float, h: float):
        """Create a video frame rendering command."""
        return cls(frame=frame, position=(x, y), size=(w, h))


@dataclass
class FrameState:
    """Complete frame state for rendering.

    This is the data structure passed from scenes to renderers.
    It contains all rendering commands for a single frame.
    """

    clear_color: tuple[int, int, int] = (0, 0, 0)
    shapes: list[Shape] = field(default_factory=list)
    texts: list[Text] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)
    videos: list[Video] = field(default_factory=list)

    # Metadata
    scene_name: str = "Unknown"
    timestamp: float = 0.0

    def add_shape(self, shape: Shape):
        """Add a shape to the frame."""
        self.shapes.append(shape)

    def add_text(self, text: Text):
        """Add text to the frame."""
        self.texts.append(text)

    def add_image(self, image: Image):
        """Add an image to the frame."""
        self.images.append(image)

    def add_video(self, video: Video):
        """Add a video frame to the frame."""
        self.videos.append(video)

    def clear(self):
        """Clear all rendering commands."""
        self.shapes.clear()
        self.texts.clear()
        self.images.clear()
        self.videos.clear()
