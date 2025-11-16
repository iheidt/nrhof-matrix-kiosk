"""Cobra Voice Activity Detection from Picovoice.

Processes audio frames at 16kHz to detect speech activity.
"""

import numpy as np

from nrhof.core.logging_utils import setup_logger
from nrhof.core.retry import retry

logger = setup_logger(__name__)

# Try to import pvcobra
try:
    import pvcobra

    HAVE_COBRA = True
except ImportError:
    HAVE_COBRA = False
    logger.warning("pvcobra not installed. Install with: pip install pvcobra")


class Cobra:
    """Cobra voice activity detection processor."""

    def __init__(self, access_key: str | None = None):
        """Initialize Cobra.

        Args:
            access_key: Picovoice access key (reads from env if not provided)
        """
        if not HAVE_COBRA:
            raise ImportError("pvcobra not installed")

        # Get access key from env if not provided
        if access_key is None:
            import os

            access_key = os.getenv("PICOVOICE_ACCESS_KEY")
            if not access_key:
                raise ValueError(
                    "PICOVOICE_ACCESS_KEY not set. "
                    "Get your key from https://console.picovoice.ai/"
                )

        # Create Cobra instance
        self.cobra = pvcobra.create(access_key=access_key)
        self.sample_rate = self.cobra.sample_rate
        self.frame_length = self.cobra.frame_length

        logger.info(
            f"Cobra initialized: {self.sample_rate}Hz, frame_length={self.frame_length} samples"
        )

    def process(self, frame: np.ndarray) -> float:
        """Process audio frame with VAD.

        Args:
            frame: Audio frame (int16 numpy array)

        Returns:
            Voice probability (0.0 to 1.0)
        """
        if len(frame) != self.frame_length:
            raise ValueError(f"Frame size mismatch: expected {self.frame_length}, got {len(frame)}")

        # Process frame - pvcobra expects a list, not numpy array
        frame_list = frame.tolist() if isinstance(frame, np.ndarray) else list(frame)
        voice_probability = self.cobra.process(frame_list)

        return voice_probability

    def reset(self):
        """Reset Cobra state."""
        # Cobra doesn't have explicit reset
        pass

    def cleanup(self):
        """Cleanup Cobra resources."""
        if self.cobra:
            self.cobra.delete()
            logger.debug("Cobra cleaned up")


@retry(tries=3, delay=0.5, exceptions=(Exception,))
def _create_cobra_with_retry(access_key: str | None) -> Cobra:
    """Create Cobra with retry on transient failures.

    Args:
        access_key: Picovoice access key

    Returns:
        Cobra instance

    Raises:
        Exception: If creation fails after retries
    """
    return Cobra(access_key=access_key)


def create_cobra(access_key: str | None = None) -> Cobra | None:
    """Create Cobra instance with retry logic.

    Args:
        access_key: Optional Picovoice access key

    Returns:
        Cobra instance or None if pvcobra not available or creation fails
    """
    if not HAVE_COBRA:
        logger.warning("pvcobra not available, Cobra disabled")
        return None

    try:
        return _create_cobra_with_retry(access_key)
    except Exception as e:
        logger.error(f"Failed to create Cobra after retries: {e}")
        return None
