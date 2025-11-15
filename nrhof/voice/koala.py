"""Koala Noise Suppression from Picovoice.

Processes 10ms frames at 16kHz to suppress background noise.
"""

import numpy as np

from nrhof.core.logging_utils import setup_logger

logger = setup_logger(__name__)

# Try to import pvkoala
try:
    import pvkoala

    HAVE_KOALA = True
except ImportError:
    HAVE_KOALA = False
    logger.warning("pvkoala not installed. Install with: pip install pvkoala")


class Koala:
    """Koala noise suppression processor."""

    def __init__(self, access_key: str | None = None):
        """Initialize Koala.

        Args:
            access_key: Picovoice access key (reads from env if not provided)
        """
        if not HAVE_KOALA:
            raise ImportError("pvkoala not installed")

        # Get access key from env if not provided
        if access_key is None:
            import os

            access_key = os.getenv("PICOVOICE_ACCESS_KEY")
            if not access_key:
                raise ValueError(
                    "PICOVOICE_ACCESS_KEY not set. "
                    "Get your key from https://console.picovoice.ai/"
                )

        # Create Koala instance
        self.koala = pvkoala.create(access_key=access_key)
        self.sample_rate = self.koala.sample_rate
        self.frame_length = self.koala.frame_length

        logger.info(
            f"Koala initialized: {self.sample_rate}Hz, " f"frame_length={self.frame_length} samples"
        )

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Process audio frame with noise suppression.

        Args:
            frame: Audio frame (int16 numpy array)

        Returns:
            Denoised frame (int16 numpy array)
        """
        if len(frame) != self.frame_length:
            raise ValueError(f"Frame size mismatch: expected {self.frame_length}, got {len(frame)}")

        # Process frame - pvkoala expects a list, not numpy array
        frame_list = frame.tolist() if isinstance(frame, np.ndarray) else list(frame)
        enhanced_list = self.koala.process(frame_list)

        # Convert back to numpy array
        enhanced_frame = np.array(enhanced_list, dtype=np.int16)
        return enhanced_frame

    def reset(self):
        """Reset Koala state."""
        # Koala doesn't have explicit reset, just delete and recreate if needed
        pass

    def cleanup(self):
        """Cleanup Koala resources."""
        if self.koala:
            self.koala.delete()
            logger.debug("Koala cleaned up")


def create_koala(access_key: str | None = None) -> Koala | None:
    """Create Koala instance.

    Args:
        access_key: Optional Picovoice access key

    Returns:
        Koala instance or None if pvkoala not available
    """
    if not HAVE_KOALA:
        logger.warning("pvkoala not available, Koala disabled")
        return None

    try:
        return Koala(access_key=access_key)
    except Exception as e:
        logger.error(f"Failed to create Koala: {e}")
        return None
