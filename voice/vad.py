#!/usr/bin/env python3
"""Voice Activity Detection using WebRTC VAD.

Provides speech detection at 16kHz with 10ms frames.
"""

import time

import numpy as np

try:
    import webrtcvad

    HAVE_WEBRTCVAD = True
except ImportError:
    HAVE_WEBRTCVAD = False

from core.logger import get_logger

logger = get_logger(__name__)


class VAD:
    """WebRTC VAD wrapper for speech detection.

    Processes 10ms frames at 16kHz and detects speech activity.
    Includes tail logic to avoid cutting off speech too early.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 10,
        aggressiveness: int = 2,
        tail_ms: int = 700,
    ):
        """Initialize VAD.

        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            frame_duration_ms: Frame duration in ms (must be 10, 20, or 30)
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
            tail_ms: Silence duration before declaring speech end (ms)
        """
        if not HAVE_WEBRTCVAD:
            raise ImportError("webrtcvad not installed. Install with: pip install webrtcvad")

        # Validate parameters
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Invalid sample_rate: {sample_rate}")
        if frame_duration_ms not in [10, 20, 30]:
            raise ValueError(f"Invalid frame_duration_ms: {frame_duration_ms}")
        if not 0 <= aggressiveness <= 3:
            raise ValueError(f"Invalid aggressiveness: {aggressiveness}")

        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.tail_ms = tail_ms

        # Create VAD
        self.vad = webrtcvad.Vad(aggressiveness)
        logger.info(
            f"VAD initialized: {sample_rate}Hz, {frame_duration_ms}ms frames, "
            f"aggressiveness={aggressiveness}, tail={tail_ms}ms"
        )

        # State tracking
        self.is_speech = False
        self.last_speech_time: float | None = None
        self.speech_start_time: float | None = None

    def process_frame(self, frame: np.ndarray) -> tuple[bool, bool, bool]:
        """Process audio frame and detect speech activity.

        Args:
            frame: Audio frame (int16 numpy array)

        Returns:
            Tuple of (is_speech, speech_started, speech_ended)
            - is_speech: True if current frame contains speech
            - speech_started: True if speech just started (transition false→true)
            - speech_ended: True if speech just ended (tail timeout)
        """
        if len(frame) != self.frame_size:
            raise ValueError(f"Frame size mismatch: expected {self.frame_size}, got {len(frame)}")

        # Convert to bytes for WebRTC VAD
        frame_bytes = frame.tobytes()

        # Detect speech in this frame
        current_time = time.time()
        frame_has_speech = self.vad.is_speech(frame_bytes, self.sample_rate)

        speech_started = False
        speech_ended = False

        if frame_has_speech:
            # Speech detected in this frame
            self.last_speech_time = current_time

            if not self.is_speech:
                # Speech just started
                self.is_speech = True
                self.speech_start_time = current_time
                speech_started = True
                logger.debug("Speech started")
        else:
            # No speech in this frame
            if self.is_speech and self.last_speech_time is not None:
                # Check if tail timeout has elapsed
                silence_duration_ms = (current_time - self.last_speech_time) * 1000
                if silence_duration_ms >= self.tail_ms:
                    # Speech ended
                    self.is_speech = False
                    speech_ended = True
                    speech_duration_ms = (
                        (current_time - self.speech_start_time) * 1000
                        if self.speech_start_time
                        else 0
                    )
                    logger.debug(
                        f"Speech ended (duration: {speech_duration_ms:.0f}ms, "
                        f"tail: {silence_duration_ms:.0f}ms)"
                    )
                    self.speech_start_time = None

        return self.is_speech, speech_started, speech_ended

    def reset(self):
        """Reset VAD state."""
        self.is_speech = False
        self.last_speech_time = None
        self.speech_start_time = None
        logger.debug("VAD state reset")


def create_vad(
    sample_rate: int = 16000,
    frame_duration_ms: int = 10,
    aggressiveness: int = 2,
    tail_ms: int = 700,
) -> VAD | None:
    """Create VAD instance.

    Args:
        sample_rate: Audio sample rate
        frame_duration_ms: Frame duration in ms
        aggressiveness: VAD aggressiveness (0-3)
        tail_ms: Silence duration before declaring speech end (ms)

    Returns:
        VAD instance or None if webrtcvad not available
    """
    if not HAVE_WEBRTCVAD:
        logger.warning("webrtcvad not available, VAD disabled")
        return None

    try:
        return VAD(
            sample_rate=sample_rate,
            frame_duration_ms=frame_duration_ms,
            aggressiveness=aggressiveness,
            tail_ms=tail_ms,
        )
    except Exception as e:
        logger.error(f"Failed to create VAD: {e}")
        return None
