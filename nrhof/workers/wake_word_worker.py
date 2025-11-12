#!/usr/bin/env python3
"""Wake word detection worker - always listening for activation phrase."""

import time
import traceback
from collections.abc import Callable

import numpy as np
import pvporcupine

from nrhof.core.audio_io import get_mic_frame as get_audio_frame
from nrhof.core.event_bus import EventType

from .base import BaseWorker


class WakeWordWorker(BaseWorker):
    """Continuously monitors audio for wake word detection."""

    def __init__(self, config: dict):
        """Initialize wake word worker.

        Args:
            config: Configuration dict
        """
        super().__init__(config, logger_name="wake_word")
        self.enabled = config.get("wake_word", {}).get("enabled", False)
        self.on_wake_word: Callable[[str], None] | None = None

        if not self.enabled:
            self.logger.info("Wake word detection disabled in config")
            return

        # Get wake word config
        wake_config = config.get("wake_word", {})
        self.access_key = wake_config.get("picovoice_access_key")
        self.keywords = wake_config.get("keywords", ["jarvis"])  # Built-in keywords
        self.keyword_paths = wake_config.get("keyword_paths", [])  # Custom .ppn files
        self.sensitivity = wake_config.get("sensitivity", 0.5)

        # Validation
        if not self.access_key:
            self.logger.warning(
                "Picovoice access key not configured. Wake word detection disabled."
            )
            self.enabled = False
            return

        # Initialize Porcupine
        try:
            # Use custom keyword files if provided, otherwise use built-in keywords
            if self.keyword_paths:
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=self.keyword_paths,
                    sensitivities=[self.sensitivity] * len(self.keyword_paths),
                )
            else:
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=self.keywords,
                    sensitivities=[self.sensitivity] * len(self.keywords),
                )

            # Clear log showing what was loaded
            config_str = (
                f"keywords={self.keywords}"
                if not self.keyword_paths
                else f"ppn={self.keyword_paths}"
            )
            self.logger.info(
                f"Porcupine ready: {config_str} | sr={self.porcupine.sample_rate} frame={self.porcupine.frame_length}"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Porcupine: {e}\n{traceback.format_exc()}")
            self.enabled = False
            return

    def start(self):
        """Start the wake word detection worker."""
        if not self.enabled:
            self.logger.info("Wake word worker not started (disabled)")
            return
        super().start()

    def _cleanup(self):
        """Clean up Porcupine resources."""
        if hasattr(self, "porcupine") and self.porcupine:
            self.porcupine.delete()

    def _worker_loop(self):
        """Main worker loop - continuously processes audio for wake word."""
        self.logger.info("Wake word detection loop started")
        self.logger.info(
            f"Porcupine expects frame_length={self.porcupine.frame_length} samples at {self.porcupine.sample_rate}Hz",
        )

        frame_length = self.porcupine.frame_length
        self.logger.info(f"Requesting {frame_length} samples per frame (native 16kHz)")

        frame_count = 0
        last_log_time = time.time()

        while self._running:
            try:
                # Get audio frame (float32 samples) - mic is now natively 16kHz
                audio_frame = get_audio_frame()

                if audio_frame is None:
                    time.sleep(0.01)
                    continue

                # Ensure we have enough samples
                if len(audio_frame) < frame_length:
                    continue

                # Sleep to match audio frame rate (512 samples @ 16kHz = 32ms)
                # This prevents spinning on the same buffer
                time.sleep(0.032)

                frame_count += 1

                # Log stats every 10 seconds
                current_time = time.time()
                if current_time - last_log_time >= 10.0:
                    elapsed = current_time - last_log_time
                    fps = frame_count / elapsed
                    self.logger.info(
                        f"Wake word: {frame_count} frames in {elapsed:.1f}s ({fps:.1f} fps)"
                    )
                    frame_count = 0
                    last_log_time = current_time

                # Convert float32 [-1, 1] to int16 [-32768, 32767] for Porcupine
                # No resampling needed - mic is natively 16kHz
                pcm = (audio_frame[:frame_length] * 32767).astype(np.int16)

                # Apply gain boost - USB lav mic is very quiet
                # Porcupine likes peaks around 15000-24000 for best detection
                GAIN = 1.0
                pcm = (pcm.astype(np.int32) * GAIN).clip(-32768, 32767).astype(np.int16)

                keyword_index = self.porcupine.process(pcm)

                # Log only when wake word is detected
                if keyword_index >= 0:
                    self.logger.info(f"Wake word detected! keyword_index={keyword_index}")

                if keyword_index >= 0:
                    # Wake word detected!
                    if self.keyword_paths:
                        keyword = f"custom_{keyword_index}"
                    else:
                        keyword = self.keywords[keyword_index]
                    self.logger.info("Wake word detected!", keyword=keyword)

                    # Emit event
                    self.event_bus.emit(EventType.WAKE_WORD_DETECTED, payload={"keyword": keyword})

                    # Call callback if set
                    if self.on_wake_word:
                        self.on_wake_word(keyword)

            except Exception as e:
                self.logger.error(
                    f"Error in wake word detection loop: {e}\n{traceback.format_exc()}"
                )
                time.sleep(0.1)

        self.logger.info("Wake word detection loop ended")

    def set_callback(self, callback: Callable[[str], None]):
        """Set callback function for wake word detection.

        Args:
            callback: Function to call when wake word is detected (receives keyword string)
        """
        self.on_wake_word = callback
