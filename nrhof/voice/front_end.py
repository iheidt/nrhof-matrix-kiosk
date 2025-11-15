"""Voice front-end pipeline.

Processes microphone frames through AEC → Koala and provides cleaned audio
for downstream processors (Cobra VAD, Porcupine wake word).
"""

from collections.abc import Generator

import numpy as np

from nrhof.core.audio_io import stream_mic_frames
from nrhof.core.logging_utils import setup_logger
from nrhof.voice.aec import AEC
from nrhof.voice.koala import Koala, create_koala

logger = setup_logger(__name__)


def create_voice_pipeline(
    sample_rate: int = 16000,
    frame_duration_ms: int = 10,
    enable_koala: bool = True,
    koala_instance: Koala | None = None,
) -> Generator[np.ndarray, None, None]:
    """Create voice processing pipeline generator.

    Yields cleaned audio frames processed through AEC → Koala.

    Args:
        sample_rate: Sample rate in Hz
        frame_duration_ms: Frame duration in ms (10ms = 160 samples at 16kHz)
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

    if koala:
        koala_frame_length = koala.frame_length
        logger.info(f"Voice pipeline: AEC → Koala ({koala_frame_length} samples)")
    else:
        logger.info("Voice pipeline: AEC only (Koala disabled)")

    # Frame buffering for Koala (needs 256 samples, but we get 160 samples per 10ms frame)
    koala_frame_buffer = np.array([], dtype=np.int16)

    # Stream mic frames and process
    for raw_frame in stream_mic_frames(frame_duration_ms=frame_duration_ms):
        # Step 1: AEC (stub pass-through for now)
        aec_frame = aec.process(raw_frame)

        # Step 2: Koala noise suppression
        if koala:
            # Ensure frame is numpy array
            if not isinstance(aec_frame, np.ndarray):
                aec_frame = np.array(aec_frame, dtype=np.int16)

            # Buffer frames until we have enough for Koala
            koala_frame_buffer = np.concatenate([koala_frame_buffer, aec_frame])

            # Process when we have enough samples
            while len(koala_frame_buffer) >= koala_frame_length:
                # Extract frame for Koala
                koala_input = np.ascontiguousarray(koala_frame_buffer[:koala_frame_length])
                koala_frame_buffer = koala_frame_buffer[koala_frame_length:]

                try:
                    # Koala processes 256 samples and returns 256 samples
                    cleaned_frame = koala.process(koala_input)
                    yield cleaned_frame
                except Exception as e:
                    logger.error(f"Koala processing failed: {e}")
                    # Yield raw frame on error
                    yield koala_input
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
