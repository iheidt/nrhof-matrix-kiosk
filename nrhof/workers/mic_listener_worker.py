#!/usr/bin/env python3
"""Mic listener worker for debugging and monitoring.

Streams 10ms mic frames and updates AppState with RMS audio level.
Useful for verifying mic path is working and monitoring audio levels.
"""

import time

from nrhof.core.app_state import get_app_state
from nrhof.core.audio_io import calculate_rms, get_mic_stream, stream_mic_frames
from nrhof.core.logging_utils import setup_logger
from nrhof.workers.base import BaseWorker

logger = setup_logger("mic_listener")


class MicListenerWorker(BaseWorker):
    """Debug worker that monitors microphone input.

    Streams 10ms frames and updates AppState.audio_level every 100ms.
    Logs frame count every 5 seconds to verify frame rate.
    """

    def __init__(self, event_bus, config: dict | None = None):
        """Initialize mic listener worker.

        Args:
            event_bus: Event bus instance
            config: Optional config dict with:
                - frame_duration_ms: Frame duration in ms (default: 10)
                - update_interval_ms: How often to update audio level (default: 100)
                - log_interval_s: How often to log stats (default: 5)
        """
        super().__init__(event_bus)
        self.config = config or {}
        self.frame_duration_ms = self.config.get("frame_duration_ms", 10)
        self.update_interval_ms = self.config.get("update_interval_ms", 100)
        self.log_interval_s = self.config.get("log_interval_s", 5)

        self.app_state = get_app_state()
        self.frame_count = 0
        self.last_update_time = 0.0
        self.last_log_time = 0.0
        self.rms_accumulator = []

    def _worker_loop(self):
        """Main worker loop - streams mic frames and updates audio level."""
        # Initialize mic stream if not already done
        if not get_mic_stream(sample_rate=16000, frame_size=512):
            logger.error("Failed to initialize mic stream")
            return

        logger.info(f"Mic listener started: {self.frame_duration_ms}ms frames")
        self.last_update_time = time.time()
        self.last_log_time = time.time()

        # Stream frames
        for frame in stream_mic_frames(frame_duration_ms=self.frame_duration_ms):
            if not self._running:
                break

            self.frame_count += 1
            current_time = time.time()

            # Calculate RMS for this frame
            rms = calculate_rms(frame)
            self.rms_accumulator.append(rms)

            # Update audio level every update_interval_ms
            if (current_time - self.last_update_time) * 1000 >= self.update_interval_ms:
                if self.rms_accumulator:
                    # Average RMS over the interval
                    avg_rms = sum(self.rms_accumulator) / len(self.rms_accumulator)
                    self.app_state.set_music_present(avg_rms > 0.01, avg_rms)
                    self.rms_accumulator = []
                self.last_update_time = current_time

            # Log stats every log_interval_s
            if current_time - self.last_log_time >= self.log_interval_s:
                elapsed = current_time - self.last_log_time
                fps = self.frame_count / elapsed
                # Expected fps is lower than theoretical 100 fps due to audio interface overhead
                # SSL Connex typically achieves ~85 fps for 10ms frames
                expected_fps = 85
                logger.info(
                    f"Mic frames: {self.frame_count} in {elapsed:.1f}s "
                    f"({fps:.1f} fps, expected ~{expected_fps} fps)"
                )
                self.frame_count = 0
                self.last_log_time = current_time

        logger.info("Mic listener stopped")
