"""Voice front-end pipeline.

Processes microphone frames through AEC → Koala and provides cleaned audio
for downstream processors (Cobra VAD, Porcupine wake word).
"""

from collections.abc import Generator

import numpy as np

from nrhof.core.audio_io import stream_mic_frames
from nrhof.core.logging_utils import setup_logger
from nrhof.core.voice_constants import VOICE_FRAME_DURATION_MS, VOICE_SAMPLE_RATE
from nrhof.voice.aec import AEC
from nrhof.voice.koala import Koala, KoalaFrameAdapter, create_koala

logger = setup_logger(__name__)


def create_voice_pipeline(
    sample_rate: int = VOICE_SAMPLE_RATE,
    frame_duration_ms: int = VOICE_FRAME_DURATION_MS,
    enable_koala: bool = True,
    koala_instance: Koala | None = None,
) -> Generator[np.ndarray, None, None]:
    """Create voice processing pipeline generator.

    Yields cleaned audio frames processed through AEC → Koala.

    Args:
        sample_rate: Sample rate in Hz (default: 16kHz)
        frame_duration_ms: Frame duration in ms (default: 32ms = 512 samples for Rhino/Cobra/Porcupine)
        enable_koala: Enable Koala noise suppression
        koala_instance: Optional pre-created Koala instance (if None, creates new one)

    Yields:
        Cleaned audio frames (int16 numpy array)

    Example:
        ```python
        for cleaned_frame in create_voice_pipeline():
            # Feed to Cobra VAD
            voice_prob = cobra.process(cleaned_frame)

            # Feed to Porcupine wake word
            keyword_idx = porcupine.process(cleaned_frame)
        ```
    """
    # Initialize AEC
    aec = AEC(sample_rate=sample_rate, frame_duration_ms=frame_duration_ms)

    # Initialize Koala if enabled
    koala = koala_instance
    if enable_koala and koala is None:
        koala = create_koala()

    # Wrap Koala in frame adapter if enabled
    koala_adapter = None
    if koala:
        target_frame_size = int(sample_rate * frame_duration_ms / 1000)  # e.g., 512 for 32ms
        koala_adapter = KoalaFrameAdapter(koala, target_frame_size=target_frame_size)
        logger.info(
            f"Voice pipeline: AEC → Koala (256 samples) → Adapter ({target_frame_size} samples)"
        )
    else:
        logger.info("Voice pipeline: AEC only (Koala disabled)")

    # Stream mic frames and process
    for raw_frame in stream_mic_frames(frame_duration_ms=frame_duration_ms):
        # Step 1: AEC (stub pass-through for now)
        aec_frame = aec.process(raw_frame)

        # Step 2: Koala noise suppression with frame adaptation
        if koala_adapter:
            # Process through Koala adapter (handles buffering internally)
            output_frames = koala_adapter.process(aec_frame)
            yield from output_frames
        else:
            # No Koala, yield AEC output directly
            yield aec_frame


def cleanup_voice_pipeline(koala: Koala | None = None):
    """Cleanup voice pipeline resources.

    Args:
        koala: Koala instance to cleanup
    """
    if koala:
        try:
            koala.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up Koala: {e}")
