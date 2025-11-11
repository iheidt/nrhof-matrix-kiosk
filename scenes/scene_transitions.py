#!/usr/bin/env python3
"""Scene transition effects and easing functions."""

import time

import pygame


def ease_out_cubic(t: float) -> float:
    """Cubic easing out - decelerating to zero velocity.

    Args:
        t: Progress from 0.0 to 1.0

    Returns:
        Eased value from 0.0 to 1.0
    """
    return 1 - pow(1 - t, 3)


def ease_in_out_cubic(t: float) -> float:
    """Cubic easing in/out - acceleration until halfway, then deceleration.

    Args:
        t: Progress from 0.0 to 1.0

    Returns:
        Eased value from 0.0 to 1.0
    """
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2


class SceneTransition:
    """Manages scene transition state and rendering."""

    def __init__(self, duration: float = 0.4):
        """Initialize transition manager.

        Args:
            duration: Transition duration in seconds (default: 0.4)
        """
        self.duration = duration
        self.active = False
        self.progress = 0.0  # 0.0 to 1.0
        self.start_time = 0.0
        self.from_scene = None
        self.from_name = None
        self.to_scene = None
        self.to_name = None
        self.direction = 1  # 1 = left to right (forward), -1 = right to left (back)
        self.from_surface: pygame.Surface | None = None
        self.to_surface: pygame.Surface | None = None

    def start(
        self, from_scene, from_name: str, to_scene, to_name: str, direction: int, screen_size: tuple
    ):
        """Start a new transition.

        Args:
            from_scene: Scene transitioning from
            from_name: Name of from scene
            to_scene: Scene transitioning to
            to_name: Name of to scene
            direction: 1 for forward, -1 for back
            screen_size: (width, height) tuple for offscreen surfaces
        """
        self.active = True
        self.progress = 0.0
        self.start_time = time.time()
        self.from_scene = from_scene
        self.from_name = from_name
        self.to_scene = to_scene
        self.to_name = to_name
        self.direction = direction

        # Create offscreen surfaces for smooth rendering
        self.from_surface = pygame.Surface(screen_size)
        self.to_surface = pygame.Surface(screen_size)

    def update(self) -> bool:
        """Update transition progress.

        Returns:
            True if transition is complete, False otherwise
        """
        if not self.active:
            return False

        elapsed = time.time() - self.start_time
        self.progress = min(1.0, elapsed / self.duration)

        # Return True when complete, but don't call complete() yet
        # Let the caller handle completion to access scene references first
        return self.progress >= 1.0

    def complete(self):
        """Complete the transition and cleanup."""
        self.active = False
        self.from_scene = None
        self.from_name = None
        self.to_scene = None
        self.to_name = None
        self.from_surface = None
        self.to_surface = None

    def render(self, screen: pygame.Surface):
        """Render the transition effect.

        Args:
            screen: Screen surface to render to
        """
        if not self.active or not self.from_surface or not self.to_surface:
            return

        # Render both scenes to offscreen surfaces
        if self.from_scene:
            self.from_scene.draw(self.from_surface)
        if self.to_scene:
            self.to_scene.draw(self.to_surface)

        # Apply easing
        eased_progress = ease_in_out_cubic(self.progress)

        # Calculate slide positions
        screen_width = screen.get_width()
        offset = int(eased_progress * screen_width)

        if self.direction == 1:  # Forward (left to right)
            from_x = -offset
            to_x = screen_width - offset
        else:  # Back (right to left)
            from_x = offset
            to_x = -screen_width + offset

        # Draw both surfaces
        screen.blit(self.from_surface, (from_x, 0))
        screen.blit(self.to_surface, (to_x, 0))
