"""Porcupine Wake Word Detection from Picovoice.

Detects wake words in audio frames at 16kHz.
"""

import numpy as np

from nrhof.core.logging_utils import setup_logger
from nrhof.core.retry import retry

logger = setup_logger(__name__)

# Try to import pvporcupine
try:
    import pvporcupine

    HAVE_PORCUPINE = True
except ImportError:
    HAVE_PORCUPINE = False
    logger.warning("pvporcupine not installed. Install with: pip install pvporcupine")


class Porcupine:
    """Porcupine wake word detection processor."""

    def __init__(
        self,
        access_key: str | None = None,
        keywords: list[str] | None = None,
        keyword_paths: list[str] | None = None,
        sensitivity: float = 0.5,
    ):
        """Initialize Porcupine.

        Args:
            access_key: Picovoice access key (reads from env if not provided)
            keywords: Built-in keyword names (e.g., ['picovoice', 'jarvis'])
            keyword_paths: Paths to custom .ppn files
            sensitivity: Detection sensitivity (0.0 to 1.0)
        """
        if not HAVE_PORCUPINE:
            raise ImportError("pvporcupine not installed")

        # Get access key from env if not provided
        if access_key is None:
            import os

            access_key = os.getenv("PICOVOICE_ACCESS_KEY")
            if not access_key:
                raise ValueError(
                    "PICOVOICE_ACCESS_KEY not set. "
                    "Get your key from https://console.picovoice.ai/"
                )

        # Use custom keyword files if provided, otherwise use built-in keywords
        if keyword_paths:
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=keyword_paths,
                sensitivities=[sensitivity] * len(keyword_paths),
            )
            self.keywords = [f"custom_{i}" for i in range(len(keyword_paths))]
        else:
            keywords = keywords or ["picovoice"]
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=keywords,
                sensitivities=[sensitivity] * len(keywords),
            )
            self.keywords = keywords

        self.sample_rate = self.porcupine.sample_rate
        self.frame_length = self.porcupine.frame_length

        logger.info(
            f"Porcupine initialized: {self.sample_rate}Hz, "
            f"frame_length={self.frame_length} samples, "
            f"keywords={self.keywords}"
        )

    def process(self, frame: np.ndarray) -> int:
        """Process audio frame for wake word detection.

        Args:
            frame: Audio frame (int16 numpy array)

        Returns:
            Keyword index if detected (>= 0), -1 otherwise
        """
        if len(frame) != self.frame_length:
            raise ValueError(f"Frame size mismatch: expected {self.frame_length}, got {len(frame)}")

        # Process frame - pvporcupine expects a list or sequence
        frame_list = frame.tolist() if isinstance(frame, np.ndarray) else list(frame)
        keyword_index = self.porcupine.process(frame_list)

        return keyword_index

    def get_keyword(self, index: int) -> str:
        """Get keyword name from index.

        Args:
            index: Keyword index from process()

        Returns:
            Keyword name
        """
        if 0 <= index < len(self.keywords):
            return self.keywords[index]
        return "unknown"

    def reset(self):
        """Reset Porcupine state."""
        # Porcupine doesn't have explicit reset
        pass

    def cleanup(self):
        """Cleanup Porcupine resources."""
        if self.porcupine:
            self.porcupine.delete()
            logger.debug("Porcupine cleaned up")


@retry(tries=3, delay=0.5, exceptions=(Exception,))
def _create_porcupine_with_retry(
    access_key: str | None,
    keywords: list[str] | None,
    keyword_paths: list[str] | None,
    sensitivity: float,
) -> Porcupine:
    """Create Porcupine with retry on transient failures.

    Args:
        access_key: Picovoice access key
        keywords: Built-in keyword names
        keyword_paths: Paths to custom .ppn files
        sensitivity: Detection sensitivity

    Returns:
        Porcupine instance

    Raises:
        Exception: If creation fails after retries
    """
    return Porcupine(
        access_key=access_key,
        keywords=keywords,
        keyword_paths=keyword_paths,
        sensitivity=sensitivity,
    )


def create_porcupine(
    access_key: str | None = None,
    keywords: list[str] | None = None,
    keyword_paths: list[str] | None = None,
    sensitivity: float = 0.5,
) -> Porcupine | None:
    """Create Porcupine instance with retry logic.

    Args:
        access_key: Optional Picovoice access key
        keywords: Built-in keyword names
        keyword_paths: Paths to custom .ppn files
        sensitivity: Detection sensitivity (0.0 to 1.0)

    Returns:
        Porcupine instance or None if pvporcupine not available or creation fails
    """
    if not HAVE_PORCUPINE:
        logger.warning("pvporcupine not available, Porcupine disabled")
        return None

    try:
        return _create_porcupine_with_retry(
            access_key=access_key,
            keywords=keywords,
            keyword_paths=keyword_paths,
            sensitivity=sensitivity,
        )
    except Exception as e:
        logger.error(f"Failed to create Porcupine after retries: {e}")
        return None
