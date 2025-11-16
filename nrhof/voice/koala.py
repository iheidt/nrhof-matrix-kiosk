"""Koala Noise Suppression from Picovoice.

Processes 10ms frames at 16kHz to suppress background noise.
"""

import numpy as np

from nrhof.core.logging_utils import setup_logger
from nrhof.core.retry import retry

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


class KoalaFrameAdapter:
    """Adapts Koala's 256-sample output to target frame size (typically 512 samples).

    Koala noise suppression uses a fixed 256-sample frame size that cannot be configured.
    This adapter buffers Koala's output and yields frames of the target size for
    downstream processors (Cobra VAD, Porcupine wake word, Rhino NLU).
    """

    def __init__(self, koala: Koala, target_frame_size: int = 512):
        """Initialize frame adapter.

        Args:
            koala: Koala instance to wrap
            target_frame_size: Desired output frame size in samples (default: 512)
        """
        self.koala = koala
        self.koala_frame_size = koala.frame_length  # Always 256
        self.target_frame_size = target_frame_size
        self.input_buffer = np.array([], dtype=np.int16)
        self.output_buffer = np.array([], dtype=np.int16)

        logger.debug(f"KoalaFrameAdapter: {self.koala_frame_size} → {target_frame_size} samples")

    def process(self, frame: np.ndarray) -> list[np.ndarray]:
        """Process input frame through Koala and return target-sized frames.

        Args:
            frame: Input audio frame (any size)

        Returns:
            List of target-sized frames (may be empty if not enough samples buffered)
        """
        # Ensure numpy array
        if not isinstance(frame, np.ndarray):
            frame = np.array(frame, dtype=np.int16)

        # Buffer input
        self.input_buffer = np.concatenate([self.input_buffer, frame])

        output_frames = []

        # Process all available Koala-sized chunks
        while len(self.input_buffer) >= self.koala_frame_size:
            # Extract frame for Koala
            koala_input = np.ascontiguousarray(self.input_buffer[: self.koala_frame_size])
            self.input_buffer = self.input_buffer[self.koala_frame_size :]

            try:
                # Koala processes and returns same size (256 samples)
                cleaned_chunk = self.koala.process(koala_input)

                # Buffer Koala output
                self.output_buffer = np.concatenate([self.output_buffer, cleaned_chunk])

            except Exception as e:
                logger.error(f"Koala processing failed: {e}")
                # On error, pass through input unchanged
                self.output_buffer = np.concatenate([self.output_buffer, koala_input])

        # Yield target-sized frames from output buffer
        while len(self.output_buffer) >= self.target_frame_size:
            output_frame = self.output_buffer[: self.target_frame_size]
            self.output_buffer = self.output_buffer[self.target_frame_size :]
            output_frames.append(output_frame)

        return output_frames

    def reset(self):
        """Clear internal buffers."""
        self.input_buffer = np.array([], dtype=np.int16)
        self.output_buffer = np.array([], dtype=np.int16)


@retry(tries=3, delay=0.5, exceptions=(Exception,))
def _create_koala_with_retry(access_key: str | None) -> Koala:
    """Create Koala with retry on transient failures.

    Args:
        access_key: Picovoice access key

    Returns:
        Koala instance

    Raises:
        Exception: If creation fails after retries
    """
    return Koala(access_key=access_key)


def create_koala(access_key: str | None = None) -> Koala | None:
    """Create Koala instance with retry logic.

    Args:
        access_key: Optional Picovoice access key

    Returns:
        Koala instance or None if pvkoala not available or creation fails
    """
    if not HAVE_KOALA:
        logger.warning("pvkoala not available, Koala disabled")
        return None

    try:
        return _create_koala_with_retry(access_key)
    except Exception as e:
        logger.error(f"Failed to create Koala after retries: {e}")
        return None
