#!/usr/bin/env python3
"""
Recognition Worker - Background thread for music recognition.

Placeholder for future integration with services like Shazam, ACRCloud, etc.
"""

import time

import numpy as np

from audio_source import get_audio_frame, get_sample_rate
from nrhof.core.app_state import TrackInfo, get_app_state
from nrhof.core.event_bus import EventType

from .base import BaseWorker


class RecognitionWorker(BaseWorker):
    """Background worker for music recognition."""

    def __init__(self, config: dict, event_bus=None):
        """Initialize recognition worker.

        Args:
            config: Configuration dictionary
            event_bus: Optional event bus instance (defaults to global)
        """
        super().__init__(config, event_bus=event_bus, logger_name="recognition_worker")
        self.app_state = get_app_state()

        # Configuration
        recognizer_config = config.get("recognizer", {})
        self.enabled = recognizer_config.get("enabled", False)
        self.cooldown = recognizer_config.get("cooldown", 5.0)
        self.confidence_threshold = recognizer_config.get("confidence_threshold", 0.7)
        self.same_track_window = recognizer_config.get("same_track_window", 30.0)

        # State
        self._recognition_buffer = []
        self.buffer_duration = 10.0  # Seconds of audio to collect
        self.sample_rate = get_sample_rate()

    def start(self):
        """Start the recognition worker thread."""
        if not self.enabled:
            self.logger.info("Recognition worker disabled by config")
            return
        super().start()

    def _worker_loop(self):
        """Main worker loop - runs in background thread."""
        while self._running:
            try:
                # Check if we should attempt recognition
                if not self._should_recognize():
                    time.sleep(1.0)
                    continue

                # Collect audio buffer
                self.logger.debug("Collecting audio for recognition")
                audio_buffer = self._collect_audio_buffer()

                if audio_buffer is None:
                    time.sleep(1.0)
                    continue

                # Attempt recognition
                self.app_state.start_recognition()
                self.event_bus.emit(
                    EventType.RECOGNITION_COOLDOWN,
                    {"cooldown": self.cooldown},
                    source="recognition_worker",
                )

                try:
                    track = self._recognize_audio(audio_buffer)

                    if track:
                        self.logger.info(
                            "Track recognized",
                            title=track.title,
                            artist=track.artist,
                            confidence=track.confidence,
                        )

                        # Check if it's the same track
                        if not self.app_state.is_same_track(track):
                            self.app_state.set_current_track(track)
                            self.event_bus.emit(
                                EventType.TRACK_CONFIRMED,
                                {
                                    "title": track.title,
                                    "artist": track.artist,
                                    "album": track.album,
                                    "confidence": track.confidence,
                                },
                                source="recognition_worker",
                            )
                        else:
                            self.logger.debug("Same track, suppressing duplicate")

                        self.app_state.end_recognition(success=True)
                    else:
                        self.logger.debug("No track recognized")
                        self.event_bus.emit(
                            EventType.TRACK_RECOGNITION_FAILED,
                            {},
                            source="recognition_worker",
                        )
                        self.app_state.end_recognition(success=False)

                except Exception as e:
                    self.logger.exception("Recognition error", error=str(e))
                    self.app_state.end_recognition(success=False)

                # Wait for cooldown
                time.sleep(self.cooldown)

            except Exception as e:
                self.logger.exception("Recognition worker error", error=str(e))
                time.sleep(5.0)  # Back off on error

    def _should_recognize(self) -> bool:
        """Check if recognition should be attempted.

        Returns:
            True if recognition should be attempted
        """
        # Check if music is present
        music_present, _ = self.app_state.get_music_state()
        if not music_present:
            return False

        # Check rate limiting
        if not self.app_state.can_attempt_recognition():
            return False

        return True

    def _collect_audio_buffer(self) -> np.ndarray | None:
        """Collect audio buffer for recognition.

        Returns:
            Audio buffer or None if collection failed
        """
        try:
            samples_needed = int(self.buffer_duration * self.sample_rate)
            buffer = []

            # Collect audio in chunks
            chunk_size = 2048
            while len(buffer) < samples_needed:
                chunk = get_audio_frame(length=chunk_size)
                buffer.extend(chunk)

                # Check if music stopped
                music_present, _ = self.app_state.get_music_state()
                if not music_present:
                    return None

            return np.array(buffer[:samples_needed])

        except Exception as e:
            self.logger.error("Failed to collect audio buffer", error=str(e))
            return None

    def _recognize_audio(self, audio_buffer: np.ndarray) -> TrackInfo | None:
        """Recognize audio using recognition service.

        This is a placeholder for future integration with services like:
        - Shazam API
        - ACRCloud
        - AudD
        - Custom fingerprinting

        Args:
            audio_buffer: Audio samples to recognize

        Returns:
            TrackInfo if recognized, None otherwise
        """
        # TODO: Integrate with actual recognition service
        # For now, return None (no recognition)

        # Example of what integration would look like:
        # try:
        #     result = shazam_api.recognize(audio_buffer, self.sample_rate)
        #     if result and result['confidence'] >= self.confidence_threshold:
        #         return TrackInfo(
        #             title=result['title'],
        #             artist=result['artist'],
        #             album=result.get('album'),
        #             confidence=result['confidence']
        #         )
        # except Exception as e:
        #     self.logger.error("Recognition API error", error=str(e))

        return None
