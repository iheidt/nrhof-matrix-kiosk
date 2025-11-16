#!/usr/bin/env python3
"""Voice pipeline constants.

Defines standard frame sizes and sample rates used throughout the voice pipeline.
All voice components (Cobra VAD, Porcupine wake word, Rhino NLU) use these values.
"""

# Sample rate for voice processing (all Picovoice components)
VOICE_SAMPLE_RATE = 16000  # Hz

# Standard frame size for voice pipeline
# Used by: Cobra VAD, Porcupine wake word, Rhino NLU, mic driver
VOICE_FRAME_SIZE = 512  # samples

# Frame duration at 16kHz
VOICE_FRAME_DURATION_MS = 32  # milliseconds (512 samples @ 16kHz)

# Koala noise suppression uses fixed frame size (not configurable)
KOALA_FRAME_SIZE = 256  # samples (fixed by pvkoala)


def frame_duration_ms(frame_size: int, sample_rate: int = VOICE_SAMPLE_RATE) -> float:
    """Calculate frame duration in milliseconds.

    Args:
        frame_size: Number of samples per frame
        sample_rate: Sample rate in Hz

    Returns:
        Frame duration in milliseconds
    """
    return (frame_size / sample_rate) * 1000


def samples_from_ms(duration_ms: float, sample_rate: int = VOICE_SAMPLE_RATE) -> int:
    """Calculate number of samples from duration.

    Args:
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz

    Returns:
        Number of samples
    """
    return int((duration_ms / 1000) * sample_rate)
