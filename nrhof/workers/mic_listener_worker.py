#!/usr/bin/env python3
"""Mic listener worker for debugging and monitoring.

Streams 10ms mic frames through AEC → Koala → RMS.
Updates AppState with audio level for HUD display.
"""

import time

import numpy as np

from nrhof.core.app_state import get_app_state
from nrhof.core.audio_io import calculate_rms, get_mic_stream, stream_mic_frames
from nrhof.core.logging_utils import setup_logger
from nrhof.voice.aec import AEC
from nrhof.voice.koala import create_koala
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
                - enable_koala: Enable Koala noise suppression (default: True)
        """
        super().__init__(event_bus)
        self.config = config or {}
        self.frame_duration_ms = self.config.get("frame_duration_ms", 10)
        self.update_interval_ms = self.config.get("update_interval_ms", 100)
        self.log_interval_s = self.config.get("log_interval_s", 5)
        self.enable_koala = self.config.get("enable_koala", True)

        self.app_state = get_app_state()
        self.frame_count = 0
        self.last_update_time = 0.0
        self.last_log_time = 0.0
        self.rms_accumulator: list[float] = []

        # Initialize processing chain
        self.aec = AEC(sample_rate=16000, frame_duration_ms=self.frame_duration_ms)
        self.koala = create_koala() if self.enable_koala else None

        # Frame buffering for Koala (needs 256 samples)
        self.koala_frame_buffer = np.array([], dtype=np.int16)
        self.koala_frame_length = self.koala.frame_length if self.koala else 0

        if self.koala:
            logger.info(
                f"Koala noise suppression enabled (frame_length={self.koala_frame_length} samples)"
            )
        else:
            logger.info("Koala noise suppression disabled")

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

            # Process through pipeline: AEC → Koala → RMS
            processed_frame = self.aec.process(frame)

            if self.koala:
                # Buffer frames until we have enough for Koala
                # Ensure processed_frame is numpy array
                if not isinstance(processed_frame, np.ndarray):
                    processed_frame = np.array(processed_frame, dtype=np.int16)

                self.koala_frame_buffer = np.concatenate([self.koala_frame_buffer, processed_frame])

                # Process when we have enough samples
                while len(self.koala_frame_buffer) >= self.koala_frame_length:
                    # Extract frame for Koala (ensure it's a contiguous array)
                    koala_frame = np.ascontiguousarray(
                        self.koala_frame_buffer[: self.koala_frame_length]
                    )
                    self.koala_frame_buffer = self.koala_frame_buffer[self.koala_frame_length :]

                    try:
                        enhanced_frame = self.koala.process(koala_frame)
                        # Calculate RMS for enhanced frame
                        rms = calculate_rms(enhanced_frame)
                        self.rms_accumulator.append(float(rms))
                    except Exception as e:
                        # If Koala fails, log details and continue
                        logger.error(
                            f"Koala processing failed: {e} | "
                            f"koala_frame type={type(koala_frame)}, "
                            f"len={len(koala_frame) if hasattr(koala_frame, '__len__') else 'N/A'}"
                        )
                        # Calculate RMS directly from original processed frame
                        rms = calculate_rms(processed_frame)
                        self.rms_accumulator.append(float(rms))
            else:
                # No Koala, just calculate RMS directly
                rms = calculate_rms(processed_frame)
                self.rms_accumulator.append(float(rms))

            # Update audio level every update_interval_ms
            if (current_time - self.last_update_time) * 1000 >= self.update_interval_ms:
                if len(self.rms_accumulator) > 0:
                    # Average RMS over the interval
                    avg_rms = float(sum(self.rms_accumulator) / len(self.rms_accumulator))
                    self.app_state.set_music_present(avg_rms > 0.01, avg_rms)
                    self.rms_accumulator.clear()
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

    def _cleanup(self):
        """Cleanup resources."""
        if self.koala:
            try:
                self.koala.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up Koala: {e}")
        logger.info("Mic listener cleanup complete")
