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
    frame_duration_ms: int = 32,
    enable_koala: bool = True,
    koala_instance: Koala | None = None,
) -> Generator[np.ndarray, None, None]:
    """Create voice processing pipeline generator.

    Yields cleaned audio frames processed through AEC → Koala.

    Args:
        sample_rate: Sample rate in Hz
        frame_duration_ms: Frame duration in ms (32ms = 512 samples recommended for Rhino/Cobra/Porcupine)
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
        logger.info(
            f"Voice pipeline: AEC → Koala (input: {koala_frame_length} samples, "
            f"output: {frame_duration_ms}ms/{int(sample_rate * frame_duration_ms / 1000)} samples)"
        )
    else:
        logger.info("Voice pipeline: AEC only (Koala disabled)")

    # Frame buffering for Koala input and output
    koala_input_buffer = np.array([], dtype=np.int16)
    koala_output_buffer = np.array([], dtype=np.int16)
    target_output_size = int(sample_rate * frame_duration_ms / 1000)  # e.g., 512 for 32ms

    # Stream mic frames and process
    for raw_frame in stream_mic_frames(frame_duration_ms=frame_duration_ms):
        # Step 1: AEC (stub pass-through for now)
        aec_frame = aec.process(raw_frame)

        # Step 2: Koala noise suppression
        if koala:
            # Ensure frame is numpy array
            if not isinstance(aec_frame, np.ndarray):
                aec_frame = np.array(aec_frame, dtype=np.int16)

            # Buffer incoming frames for Koala processing
            koala_input_buffer = np.concatenate([koala_input_buffer, aec_frame])

            # Process all available Koala-sized chunks
            while len(koala_input_buffer) >= koala_frame_length:
                # Extract frame for Koala
                koala_input = np.ascontiguousarray(koala_input_buffer[:koala_frame_length])
                koala_input_buffer = koala_input_buffer[koala_frame_length:]

                try:
                    # Koala processes koala_frame_length samples (e.g., 256)
                    cleaned_chunk = koala.process(koala_input)

                    # Buffer Koala output until we have target size (e.g., 512)
                    koala_output_buffer = np.concatenate([koala_output_buffer, cleaned_chunk])

                    # Yield when we have enough samples for downstream (512)
                    while len(koala_output_buffer) >= target_output_size:
                        output_frame = koala_output_buffer[:target_output_size]
                        koala_output_buffer = koala_output_buffer[target_output_size:]
                        yield output_frame

                except Exception as e:
                    logger.error(f"Koala processing failed: {e}")
                    # Yield raw frame on error
                    koala_output_buffer = np.concatenate([koala_output_buffer, koala_input])
                    if len(koala_output_buffer) >= target_output_size:
                        output_frame = koala_output_buffer[:target_output_size]
                        koala_output_buffer = koala_output_buffer[target_output_size:]
                        yield output_frame
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
