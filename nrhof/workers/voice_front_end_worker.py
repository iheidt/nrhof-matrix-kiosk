#!/usr/bin/env python3
"""Voice front-end worker.

Consolidates microphone processing, VAD, and wake word detection into a single worker.
Processes frames through: Mic → AEC → Koala → Cobra (VAD) & Porcupine (wake word).
"""

import time
from enum import Enum, auto

import numpy as np

from nrhof.core.app_state import get_app_state
from nrhof.core.audio_io import calculate_rms, get_mic_stream
from nrhof.core.event_bus import EventType
from nrhof.core.logging_utils import setup_logger
from nrhof.core.voice_constants import (
    VOICE_FRAME_DURATION_MS,
    VOICE_FRAME_SIZE,
    VOICE_SAMPLE_RATE,
    samples_from_ms,
)
from nrhof.voice.cobra import create_cobra
from nrhof.voice.front_end import create_voice_pipeline
from nrhof.voice.rhino import create_rhino
from nrhof.voice.wake import create_porcupine
from nrhof.workers.base import BaseWorker

logger = setup_logger(__name__)


class VoiceState(Enum):
    """Voice processing state machine.

    States:
        IDLE: Waiting for wake word
        WAKE_DETECTED: Wake word just detected, waiting for speech
        SPEECH_ACTIVE: Speech detected and being captured
        SPEECH_ENDING: Speech ended, processing accumulated segment
    """

    IDLE = auto()
    WAKE_DETECTED = auto()
    SPEECH_ACTIVE = auto()
    SPEECH_ENDING = auto()


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
        self.vad_tail_ms = voice_config.get("vad_tail_ms", 700)  # Silence before ending
        self.speech_timeout_s = voice_config.get("speech_timeout_s", 4.0)  # Timeout after wake
        self.intent_cooldown_s = voice_config.get("intent_cooldown_s", 2.0)  # Cooldown after intent
        self.min_post_speech_silence_ms = voice_config.get("min_post_speech_silence_ms", 800)
        self.rhino_finalize_timeout_ms = voice_config.get("rhino_finalize_timeout_ms", 8000)
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

        # State machine
        self.state = VoiceState.IDLE
        self.speech_start_time: float | None = None
        self.wake_word_time: float | None = None
        self.silence_frame_count = 0

        # Speech segment buffering (for ASR)
        self.segment_buffer: list[np.ndarray] = []  # Accumulate PCM frames for ASR
        self.last_intent_time: float = 0.0  # Last time an intent was resolved (for cooldown)

        # Calculate tail frames
        self.tail_frames = int(self.vad_tail_ms / VOICE_FRAME_DURATION_MS)

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

        # Frame buffering (Cobra/Porcupine need standard frame size)
        self.vad_frame_length = self.cobra.frame_length if self.cobra else VOICE_FRAME_SIZE
        self.wake_frame_length = self.porcupine.frame_length if self.porcupine else VOICE_FRAME_SIZE
        self.frame_buffer = np.array([], dtype=np.int16)

        # Initialize Rhino NLU
        self.rhino = None
        rhino_config = voice_config.get("rhino", {})
        if rhino_config.get("enabled", True):
            context_path = rhino_config.get("context_path")
            debug_save_audio = rhino_config.get("debug_save_audio", False)
            if context_path:
                self.rhino = create_rhino(
                    context_path=context_path,
                    debug_save_audio=debug_save_audio,
                )
                if self.rhino:
                    self.logger.info("Rhino NLU enabled for intent recognition")
                    if debug_save_audio:
                        self.logger.info("Rhino debug mode: saving audio to /tmp")
                else:
                    self.logger.warning("Failed to initialize Rhino NLU")
            else:
                self.logger.warning("Rhino enabled but no context_path specified")

    def start(self):
        """Start voice front-end worker."""
        if not self.enabled:
            self.logger.info("Voice front-end worker not started (disabled)")
            return
        super().start()

    def _worker_loop(self):
        """Main worker loop - processes voice pipeline frames."""
        # Initialize mic stream
        if not get_mic_stream(sample_rate=VOICE_SAMPLE_RATE, frame_size=VOICE_FRAME_SIZE):
            self.logger.error("Failed to initialize mic stream")
            return

        # Note: BaseWorker.start() already logs 'VoiceFrontEndWorker started'
        self.last_update_time = time.time()
        self.last_log_time = time.time()

        # Create voice pipeline (AEC → Koala)
        # Use standard frame size to match mic driver and downstream processors
        for cleaned_frame in create_voice_pipeline(
            enable_koala=True, frame_duration_ms=VOICE_FRAME_DURATION_MS
        ):
            if not self._running:
                break

            self.frame_count += 1
            current_time = time.time()

            # Calculate RMS for HUD
            rms = calculate_rms(cleaned_frame)
            self.rms_accumulator.append(float(rms))

            # Buffer frames for VAD/wake word
            self.frame_buffer = np.concatenate([self.frame_buffer, cleaned_frame])

            # Process when we have enough samples
            while len(self.frame_buffer) >= max(self.vad_frame_length, self.wake_frame_length):
                # Extract frame for processing
                frame_512 = self.frame_buffer[:VOICE_FRAME_SIZE]
                self.frame_buffer = self.frame_buffer[VOICE_FRAME_SIZE:]

                # Run Cobra VAD
                if self.cobra:
                    try:
                        voice_prob = self.cobra.process(frame_512)
                        self._process_vad(voice_prob, current_time, frame_512)
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

            # Check for speech timeout after wake word
            if (
                self.state in (VoiceState.WAKE_DETECTED, VoiceState.SPEECH_ACTIVE)
                and self.wake_word_time
            ):
                if (current_time - self.wake_word_time) > self.speech_timeout_s:
                    self.logger.info(f"Speech timeout in state {self.state.name}")

                    # Emit timeout event (VoiceEventHandler will restore audio & clear status)
                    self.event_bus.emit(EventType.VOICE_TIMEOUT)

                    # Reset to idle
                    self._transition_to(VoiceState.IDLE)
                    self.wake_word_time = None
                    self.silence_frame_count = 0
                    self.segment_buffer.clear()

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

            # Small sleep to prevent CPU starvation of main thread
            # Koala yields frames at ~16-32ms intervals
            # Sleep for ~5ms to yield CPU to main thread while staying responsive
            time.sleep(0.005)

        # Note: Loop exits when self._running = False (BaseWorker.stop() logs 'stopped')

    def _process_vad(self, voice_prob: float, current_time: float, frame_512: np.ndarray):
        """Process VAD result and emit speech events.

        Args:
            voice_prob: Voice probability from Cobra (0.0 to 1.0)
            current_time: Current timestamp
            frame_512: Current 512-sample frame (for buffering)
        """
        # Only process VAD when waiting for or capturing speech
        if self.state == VoiceState.IDLE:
            return

        is_speech_now = voice_prob >= self.vad_threshold

        # State machine transitions
        if self.state == VoiceState.WAKE_DETECTED:
            if is_speech_now:
                # Transition: WAKE_DETECTED → SPEECH_ACTIVE
                self._transition_to(VoiceState.SPEECH_ACTIVE)
                self.speech_start_time = current_time
                self.silence_frame_count = 0
                self.speech_segments += 1
                self.segment_buffer.append(frame_512.copy())
                self.logger.debug(f"Speech started (prob={voice_prob:.2f})")
                self.event_bus.emit(EventType.VOICE_SPEECH_START)
            # else: stay in WAKE_DETECTED, waiting for speech

        elif self.state == VoiceState.SPEECH_ACTIVE:
            if is_speech_now:
                # Active speech - reset silence counter and buffer frame
                self.silence_frame_count = 0
                self.segment_buffer.append(frame_512.copy())
            else:
                # Silence during speech - increment counter but keep buffering (tail)
                self.silence_frame_count += 1
                self.segment_buffer.append(frame_512.copy())

                # Check if tail timeout reached
                if self.silence_frame_count >= self.tail_frames:
                    # Transition: SPEECH_ACTIVE → IDLE (via processing)
                    if self.speech_start_time:
                        duration = (current_time - self.speech_start_time) * 1000
                        self.logger.debug(
                            f"Speech ended (duration={duration:.0f}ms, tail={self.silence_frame_count} frames)"
                        )
                    self.event_bus.emit(EventType.VOICE_SPEECH_END)

                    # Emit complete segment for ASR
                    if len(self.segment_buffer) > 0:
                        self._emit_speech_segment()

                    # Transition back to idle
                    self._transition_to(VoiceState.IDLE)
                    self.wake_word_time = None
                    self.silence_frame_count = 0

    def _on_wake_word_detected(self, keyword_index: int, current_time: float):
        """Handle wake word detection.

        Args:
            keyword_index: Index of detected keyword
            current_time: Current timestamp
        """
        keyword = self.porcupine.get_keyword(keyword_index)
        self.wake_word_count += 1
        self.logger.info(f"Wake word detected! keyword={keyword}")

        # Transition: IDLE → WAKE_DETECTED
        self._transition_to(VoiceState.WAKE_DETECTED)
        self.wake_word_time = current_time
        self.silence_frame_count = 0
        self.segment_buffer.clear()
        self.logger.debug(f"State: {self.state.name} - waiting for speech")

        # Emit event
        self.event_bus.emit(EventType.WAKE_WORD_DETECTED, payload={"keyword": keyword})

    def _emit_speech_segment(self):
        """Emit complete speech segment and process with Rhino NLU."""
        if not self.segment_buffer:
            self.logger.warning("No speech segment to emit (buffer empty)")
            return

        # Concatenate all buffered frames into single array
        segment_pcm = np.concatenate(self.segment_buffer)
        num_samples = len(segment_pcm)
        duration_ms = (num_samples / VOICE_SAMPLE_RATE) * 1000

        # Add explicit post-speech silence padding for Rhino finalization
        # This ensures Rhino has enough silence to detect speech endpoint
        post_silence_samples = samples_from_ms(self.min_post_speech_silence_ms)
        silence_padding = np.zeros(post_silence_samples, dtype=np.int16)
        segment_pcm = np.concatenate([segment_pcm, silence_padding])

        # Validate PCM data
        pcm_min = segment_pcm.min()
        pcm_max = segment_pcm.max()
        pcm_dtype = segment_pcm.dtype

        self.logger.info(
            f"Emitting speech segment: {num_samples} samples ({duration_ms:.0f}ms) "
            f"+ {post_silence_samples} silence samples ({self.min_post_speech_silence_ms}ms), "
            f"dtype={pcm_dtype}, range=[{pcm_min}, {pcm_max}]"
        )

        # Process with Rhino NLU if available
        if self.rhino:
            try:
                intent, slots = self.rhino.process_segment(
                    segment_pcm, sample_rate=VOICE_SAMPLE_RATE
                )

                if intent is not None:
                    # Check cooldown to prevent accidental re-triggers
                    now = time.time()
                    time_since_last_intent = now - self.last_intent_time

                    if time_since_last_intent < self.intent_cooldown_s:
                        self.logger.info(
                            f"[Rhino] Intent '{intent}' ignored (cooldown: "
                            f"{time_since_last_intent:.1f}s < {self.intent_cooldown_s}s)"
                        )
                    else:
                        # Rhino understood the intent - emit VOICE_INTENT_RESOLVED
                        self.logger.info(f"[Rhino] Intent resolved: {intent}")
                        self.event_bus.emit(
                            EventType.VOICE_INTENT_RESOLVED,
                            payload={"intent": intent, "slots": slots},
                        )
                        # Update last intent time
                        self.last_intent_time = now
                else:
                    # Rhino did not understand - emit segment for fallback ASR (Phase 4)
                    self.logger.debug("[Rhino] No intent recognized")
                    self.event_bus.emit(
                        EventType.VOICE_SEGMENT_READY,
                        payload={"pcm": segment_pcm, "sample_rate": VOICE_SAMPLE_RATE},
                    )

                # Note: No need to reset here - process_segment() resets at start of next call

            except Exception as e:
                self.logger.error(f"Rhino processing failed: {e}")
                # Emit segment anyway for fallback
                self.event_bus.emit(
                    EventType.VOICE_SEGMENT_READY,
                    payload={"pcm": segment_pcm, "sample_rate": VOICE_SAMPLE_RATE},
                )
        else:
            # No Rhino - just emit segment for ASR
            self.event_bus.emit(
                EventType.VOICE_SEGMENT_READY,
                payload={"pcm": segment_pcm, "sample_rate": VOICE_SAMPLE_RATE},
            )

        # Clear buffer
        self.segment_buffer.clear()

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

        if self.rhino:
            try:
                self.rhino.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up Rhino: {e}")

        self.logger.info("Voice front-end worker cleanup complete")

    def _transition_to(self, new_state: VoiceState):
        """Transition to a new state with logging.

        Args:
            new_state: Target state
        """
        if new_state != self.state:
            self.logger.debug(f"State transition: {self.state.name} → {new_state.name}")
            self.state = new_state
