"""Acoustic Echo Cancellation (AEC) stub.

Currently a pass-through. Will integrate WebRTC AEC3 in Phase 2.
"""

import numpy as np

from nrhof.core.logging_utils import setup_logger

logger = setup_logger(__name__)


class AEC:
    """AEC processor (stub implementation)."""

    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 10):
        """Initialize AEC.

        Args:
            sample_rate: Sample rate in Hz
            frame_duration_ms: Frame duration in milliseconds
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        logger.info(f"AEC initialized (stub): {sample_rate}Hz, {frame_duration_ms}ms frames")

    def process(
        self, mic_frame: np.ndarray, reference_frame: np.ndarray | None = None
    ) -> np.ndarray:
        """Process frame with AEC.

        Args:
            mic_frame: Microphone input (int16)
            reference_frame: Reference audio being played (optional, for echo cancellation)

        Returns:
            Processed frame (int16) - currently just returns input unchanged
        """
        # Stub: pass-through for now
        return mic_frame

    def reset(self):
        """Reset AEC state."""
        pass
