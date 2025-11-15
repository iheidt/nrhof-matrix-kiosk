#!/usr/bin/env python3
"""Gesture detection for touch input."""

import time
from dataclasses import dataclass
from enum import Enum


class GestureType(str, Enum):
    """Recognized gesture types.

    Inherits from str for backward compatibility with string comparisons.
    """

    TAP = "tap"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"


@dataclass
class TouchPoint:
    """Represents a single touch point."""

    x: float
    y: float
    timestamp: float


@dataclass
class Gesture:
    """Detected gesture."""

    type: GestureType
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    duration: float
    distance: float


class GestureDetector:
    """Detects gestures from touch events."""

    def __init__(
        self,
        swipe_threshold: float = 50.0,  # Minimum distance for swipe
        tap_max_duration: float = 0.3,  # Maximum duration for tap
        tap_max_distance: float = 10.0,  # Maximum movement for tap
    ):
        """Initialize gesture detector.

        Args:
            swipe_threshold: Minimum distance in pixels to register as swipe
            tap_max_duration: Maximum duration in seconds for tap
            tap_max_distance: Maximum movement in pixels to still be a tap
        """
        self.swipe_threshold = swipe_threshold
        self.tap_max_duration = tap_max_duration
        self.tap_max_distance = tap_max_distance

        # Track active touches
        self._touches = {}  # stylus_id -> TouchPoint
        self._start_touches = {}  # stylus_id -> TouchPoint (first touch)

    def process_touch(self, stylus_id: str, action: str, x: float, y: float) -> Gesture | None:
        """Process a touch event and potentially return a gesture.

        Args:
            stylus_id: Unique identifier for this touch point
            action: 'down', 'move', or 'up'
            x: Touch x coordinate
            y: Touch y coordinate

        Returns:
            Gesture if detected, None otherwise
        """
        current_time = time.time()

        if action == "down":
            # Start new touch
            touch = TouchPoint(x, y, current_time)
            self._touches[stylus_id] = touch
            self._start_touches[stylus_id] = touch
            return None

        elif action == "move":
            # Update current position
            if stylus_id in self._touches:
                self._touches[stylus_id] = TouchPoint(x, y, current_time)
            return None

        elif action == "up":
            # Touch ended - check for gesture
            if stylus_id not in self._start_touches:
                return None

            start = self._start_touches[stylus_id]
            duration = current_time - start.timestamp
            dx = x - start.x
            dy = y - start.y
            distance = (dx**2 + dy**2) ** 0.5

            # Clean up
            self._touches.pop(stylus_id, None)
            self._start_touches.pop(stylus_id, None)

            # Detect gesture type
            if distance < self.tap_max_distance and duration < self.tap_max_duration:
                # Tap
                return Gesture(
                    type=GestureType.TAP,
                    start_x=start.x,
                    start_y=start.y,
                    end_x=x,
                    end_y=y,
                    duration=duration,
                    distance=distance,
                )

            elif distance >= self.swipe_threshold:
                # Swipe - determine direction
                abs_dx = abs(dx)
                abs_dy = abs(dy)

                if abs_dx > abs_dy:
                    # Horizontal swipe
                    gesture_type = GestureType.SWIPE_RIGHT if dx > 0 else GestureType.SWIPE_LEFT
                else:
                    # Vertical swipe
                    gesture_type = GestureType.SWIPE_DOWN if dy > 0 else GestureType.SWIPE_UP

                return Gesture(
                    type=gesture_type,
                    start_x=start.x,
                    start_y=start.y,
                    end_x=x,
                    end_y=y,
                    duration=duration,
                    distance=distance,
                )

        return None
