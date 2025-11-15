#!/usr/bin/env python3
"""Voice front-end worker.

Consolidates microphone processing, VAD, and wake word detection into a single worker.
Processes frames through: Mic → AEC → Koala → Cobra (VAD) & Porcupine (wake word).
"""

import time

import numpy as np

from nrhof.core.app_state import get_app_state
from nrhof.core.audio_io import calculate_rms, get_mic_stream
from nrhof.core.event_bus import EventType
from nrhof.core.logging_utils import setup_logger
from nrhof.voice.cobra import create_cobra
from nrhof.voice.front_end import create_voice_pipeline
from nrhof.voice.wake import create_porcupine
from nrhof.workers.base import BaseWorker

logger = setup_logger(__name__)


class VoiceFrontEndWorker(BaseWorker):
    """Voice front-end worker.

    Processes microphone input through the voice pipeline and runs:
    - Cobra VAD (emits VOICE_SPEECH_START/END)
    - Porcupine wake word (emits WAKE_WORD_DETECTED)
    - HUD audio level updates (AppState.audio_level)
    """

    def __init__(self, config: dict):
        """Initialize voice front-end worker.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config, logger_name="voice_front_end")

        # Get config
        voice_config = config.get("voice_front_end", {})
        wake_config = config.get("wake_word", {})

        self.enabled = voice_config.get("enabled", True)
        self.enable_vad = voice_config.get("enable_vad", True)
        self.enable_wake_word = wake_config.get("enabled", True)
        self.vad_threshold = voice_config.get("vad_threshold", 0.5)
        self.update_interval_ms = voice_config.get("update_interval_ms", 100)
        self.log_interval_s = voice_config.get("log_interval_s", 10)

        if not self.enabled:
            self.logger.info("Voice front-end disabled by config")
            return

        self.app_state = get_app_state()

        # Stats
        self.frame_count = 0
        self.wake_word_count = 0
        self.speech_segments = 0
        self.last_update_time = 0.0
        self.last_log_time = 0.0
        self.rms_accumulator: list[float] = []

        # VAD state tracking
        self.is_speech = False
        self.speech_start_time: float | None = None

        # Initialize Cobra VAD
        self.cobra = None
        if self.enable_vad:
            self.cobra = create_cobra()
            if self.cobra:
                self.logger.info(
                    f"Cobra VAD enabled (frame_length={self.cobra.frame_length} samples, "
                    f"threshold={self.vad_threshold})"
                )
            else:
                self.logger.warning("Failed to initialize Cobra VAD")
                self.enable_vad = False

        # Initialize Porcupine wake word
        self.porcupine = None
        if self.enable_wake_word:
            keywords = wake_config.get("keywords", ["picovoice"])
            keyword_paths = wake_config.get("keyword_paths", [])
            sensitivity = wake_config.get("sensitivity", 0.5)

            self.porcupine = create_porcupine(
                keywords=keywords, keyword_paths=keyword_paths, sensitivity=sensitivity
            )

            if self.porcupine:
                self.logger.info(f"Porcupine wake word enabled (keywords={keywords})")
            else:
                self.logger.warning("Failed to initialize Porcupine")
                self.enable_wake_word = False

        # Frame buffering (Cobra/Porcupine need 512 samples, Koala outputs 256)
        self.vad_frame_length = self.cobra.frame_length if self.cobra else 512
        self.wake_frame_length = self.porcupine.frame_length if self.porcupine else 512
        self.frame_buffer = np.array([], dtype=np.int16)

    def start(self):
        """Start voice front-end worker."""
        if not self.enabled:
            self.logger.info("Voice front-end worker not started (disabled)")
            return
        super().start()

    def _worker_loop(self):
        """Main worker loop - processes voice pipeline frames."""
        # Initialize mic stream
        if not get_mic_stream(sample_rate=16000, frame_size=512):
            self.logger.error("Failed to initialize mic stream")
            return

        self.logger.info("Voice front-end worker started")
        self.last_update_time = time.time()
        self.last_log_time = time.time()

        # Create voice pipeline (AEC → Koala)
        for cleaned_frame in create_voice_pipeline(enable_koala=True):
            if not self._running:
                break

            self.frame_count += 1
            current_time = time.time()

            # Calculate RMS for HUD
            rms = calculate_rms(cleaned_frame)
            self.rms_accumulator.append(float(rms))

            # Buffer frames for VAD/wake word (need 512 samples)
            self.frame_buffer = np.concatenate([self.frame_buffer, cleaned_frame])

            # Process when we have enough samples
            while len(self.frame_buffer) >= max(self.vad_frame_length, self.wake_frame_length):
                # Extract 512 samples for processing
                frame_512 = self.frame_buffer[:512]
                self.frame_buffer = self.frame_buffer[512:]

                # Run Cobra VAD
                if self.cobra:
                    try:
                        voice_prob = self.cobra.process(frame_512)
                        self._process_vad(voice_prob, current_time)
                    except Exception as e:
                        self.logger.error(f"Cobra VAD failed: {e}")

                # Run Porcupine wake word
                if self.porcupine:
                    try:
                        keyword_index = self.porcupine.process(frame_512)
                        if keyword_index >= 0:
                            self._on_wake_word_detected(keyword_index, current_time)
                    except Exception as e:
                        self.logger.error(f"Porcupine wake word failed: {e}")

            # Update HUD audio level every update_interval_ms
            if (current_time - self.last_update_time) * 1000 >= self.update_interval_ms:
                if len(self.rms_accumulator) > 0:
                    avg_rms = float(sum(self.rms_accumulator) / len(self.rms_accumulator))
                    self.app_state.set_music_present(avg_rms > 0.01, avg_rms)
                    self.rms_accumulator.clear()
                self.last_update_time = current_time

            # Log stats every log_interval_s
            if current_time - self.last_log_time >= self.log_interval_s:
                elapsed = current_time - self.last_log_time
                fps = self.frame_count / elapsed
                self.logger.info(
                    f"Voice front-end: {self.frame_count} frames in {elapsed:.1f}s "
                    f"({fps:.1f} fps), {self.wake_word_count} wake words, "
                    f"{self.speech_segments} speech segments"
                )
                self.frame_count = 0
                self.wake_word_count = 0
                self.speech_segments = 0
                self.last_log_time = current_time

        self.logger.info("Voice front-end worker stopped")

    def _process_vad(self, voice_prob: float, current_time: float):
        """Process VAD result and emit speech events.

        Args:
            voice_prob: Voice probability from Cobra (0.0 to 1.0)
            current_time: Current timestamp
        """
        is_speech_now = voice_prob >= self.vad_threshold

        # Detect speech start
        if is_speech_now and not self.is_speech:
            self.is_speech = True
            self.speech_start_time = current_time
            self.speech_segments += 1
            self.logger.debug(f"Speech started (prob={voice_prob:.2f})")
            self.event_bus.emit(EventType.VOICE_SPEECH_START)

        # Detect speech end
        elif not is_speech_now and self.is_speech:
            self.is_speech = False
            if self.speech_start_time:
                duration = (current_time - self.speech_start_time) * 1000
                self.logger.debug(f"Speech ended (duration={duration:.0f}ms)")
            self.event_bus.emit(EventType.VOICE_SPEECH_END)

    def _on_wake_word_detected(self, keyword_index: int, current_time: float):
        """Handle wake word detection.

        Args:
            keyword_index: Index of detected keyword
            current_time: Current timestamp
        """
        keyword = self.porcupine.get_keyword(keyword_index)
        self.wake_word_count += 1
        self.logger.info(f"Wake word detected! keyword={keyword}")

        # Emit event
        self.event_bus.emit(EventType.WAKE_WORD_DETECTED, payload={"keyword": keyword})

    def _cleanup(self):
        """Cleanup resources."""
        if self.cobra:
            try:
                self.cobra.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up Cobra: {e}")

        if self.porcupine:
            try:
                self.porcupine.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up Porcupine: {e}")

        self.logger.info("Voice front-end worker cleanup complete")
