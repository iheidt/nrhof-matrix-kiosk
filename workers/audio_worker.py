#!/usr/bin/env python3
"""
Audio Worker - Background thread for audio monitoring and recognition.

Monitors audio levels, detects music presence, and triggers recognition.
"""
import time

import numpy as np

from audio_source import get_audio_frame, get_sample_rate
from core.app_state import get_app_state
from core.event_bus import EventType

from .base import BaseWorker


class AudioWorker(BaseWorker):
    """Background worker for audio monitoring and recognition."""

    def __init__(self, config: dict):
        """Initialize audio worker.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config, logger_name="audio_worker")
        self.app_state = get_app_state()

        # Configuration
        self.sample_rate = get_sample_rate()
        self.frame_size = config.get("audio_frame_size", 2048)
        self.music_threshold = config.get("music_threshold", 0.01)  # RMS threshold
        self.music_debounce = config.get("music_debounce", 0.5)  # Seconds
        self.poll_interval = config.get("audio_poll_interval", 0.1)  # 100ms

        # State
        self._music_present = False
        self._last_music_change = 0.0
        self._last_level = 0.0

        # Recognition (placeholder for now)
        self._recognition_enabled = config.get("enable_recognition", False)

    # start() and stop() inherited from BaseWorker

    def _worker_loop(self):
        """Main worker loop - runs in background thread."""
        while self._running:
            try:
                # Get audio frame
                frame = get_audio_frame(length=self.frame_size)

                # Calculate RMS level
                rms = np.sqrt(np.mean(frame**2))
                self._last_level = rms

                # Detect music presence with debouncing
                music_now = rms > self.music_threshold

                if music_now != self._music_present:
                    # State change - check debounce
                    elapsed = time.time() - self._last_music_change
                    if elapsed >= self.music_debounce:
                        self._music_present = music_now
                        self._last_music_change = time.time()

                        # Update app state
                        self.app_state.set_music_present(music_now, rms)

                        # Emit event
                        if music_now:
                            self.event_bus.emit(
                                EventType.MUSIC_PRESENT,
                                {"level": float(rms)},
                                source="audio_worker",
                            )

                            # Trigger recognition if enabled
                            if self._recognition_enabled:
                                self._attempt_recognition()
                        else:
                            self.event_bus.emit(EventType.MUSIC_ABSENT, {}, source="audio_worker")
                            # Clear current track
                            self.app_state.set_current_track(None)
                else:
                    # Update level even if state hasn't changed
                    if self._music_present:
                        self.app_state.set_music_present(True, rms)

                # Sleep to avoid busy-waiting
                time.sleep(self.poll_interval)

            except Exception as e:
                print(f"Audio worker error: {e}")
                time.sleep(1.0)  # Back off on error

    def _attempt_recognition(self):
        """Attempt track recognition (placeholder)."""
        # Check if we can attempt recognition (rate limiting)
        if not self.app_state.can_attempt_recognition():
            return

        # Mark recognition as starting
        self.app_state.start_recognition()

        # TODO: Actual recognition logic will go here
        # For now, just emit a cooldown event
        self.event_bus.emit(
            EventType.RECOGNITION_COOLDOWN,
            {"cooldown": self.app_state.rate_limits.recognition_cooldown},
            source="audio_worker",
        )

        # Mark recognition as complete (failed for now)
        self.app_state.end_recognition(success=False)

    def get_current_level(self) -> float:
        """Get current audio level.

        Returns:
            Current RMS level
        """
        return self._last_level

    def is_music_present(self) -> bool:
        """Check if music is currently present.

        Returns:
            True if music detected
        """
        return self._music_present
