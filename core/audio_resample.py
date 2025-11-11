#!/usr/bin/env python3
"""Audio resampling utilities.

Handles conversion between different sample rates and formats.
Critical for voice stack: UI audio at 44.1kHz, voice at 16kHz.

This prevents "why is VAD/AEC weird?" bugs by ensuring consistent
format: 16kHz, mono, int16 for all voice processing.
"""

import numpy as np
from scipy import signal

from core.logger import get_logger

logger = get_logger("audio_resample")


def resample_to_16k_mono_int16(
    audio: np.ndarray,
    source_rate: int,
    source_channels: int = 1,
    source_dtype: str = "float32",
) -> np.ndarray:
    """Resample audio to 16kHz mono int16 format for voice processing.

    This is the canonical format for voice stack (VAD, AEC, STT).

    Args:
        audio: Input audio array
        source_rate: Source sample rate (e.g., 44100, 48000)
        source_channels: Number of channels (1=mono, 2=stereo)
        source_dtype: Source data type ('float32', 'int16', etc.)

    Returns:
        Resampled audio as int16 mono at 16kHz

    Examples:
        >>> # Convert 44.1kHz stereo float32 to 16kHz mono int16
        >>> ui_audio = np.random.randn(8820, 2).astype(np.float32)  # 200ms stereo
        >>> voice_audio = resample_to_16k_mono_int16(ui_audio, 44100, 2, 'float32')
        >>> voice_audio.shape
        (3200,)  # 200ms at 16kHz
        >>> voice_audio.dtype
        dtype('int16')
    """
    target_rate = 16000

    # Step 1: Convert to mono if needed
    if source_channels > 1:
        # Average channels (simple downmix)
        audio = np.mean(audio, axis=1 if audio.ndim > 1 else 0)

    # Step 2: Convert to float32 if needed (for resampling)
    if source_dtype == "int16":
        audio = audio.astype(np.float32) / 32768.0  # Normalize int16 to [-1, 1]
    elif source_dtype != "float32":
        audio = audio.astype(np.float32)

    # Step 3: Resample if needed
    if source_rate != target_rate:
        # Calculate resampling ratio
        num_samples = int(len(audio) * target_rate / source_rate)

        # Use scipy's resample for high-quality resampling
        # This uses FFT-based resampling which is slower but higher quality
        audio = signal.resample(audio, num_samples)

    # Step 4: Convert to int16
    # Clip to [-1, 1] range and convert to int16
    audio = np.clip(audio, -1.0, 1.0)
    audio = (audio * 32767).astype(np.int16)

    return audio


def resample_to_16k_mono_int16_fast(
    audio: np.ndarray,
    source_rate: int,
    source_channels: int = 1,
) -> np.ndarray:
    """Fast resampler using simple decimation (lower quality, faster).

    Use this for real-time processing where speed matters more than quality.
    Only works for simple integer ratios (e.g., 48kHz->16kHz, 44.1kHz not ideal).

    Args:
        audio: Input audio array (float32, [-1, 1] range)
        source_rate: Source sample rate
        source_channels: Number of channels

    Returns:
        Resampled audio as int16 mono at 16kHz
    """
    target_rate = 16000

    # Convert to mono if needed
    if source_channels > 1:
        audio = np.mean(audio, axis=1 if audio.ndim > 1 else 0)

    # Simple decimation for integer ratios
    if source_rate % target_rate == 0:
        decimation_factor = source_rate // target_rate
        audio = audio[::decimation_factor]
    else:
        # Fall back to high-quality resampling for non-integer ratios
        num_samples = int(len(audio) * target_rate / source_rate)
        audio = signal.resample(audio, num_samples)

    # Convert to int16
    audio = np.clip(audio, -1.0, 1.0)
    audio = (audio * 32767).astype(np.int16)

    return audio


def calculate_frame_count(duration_ms: int, sample_rate: int = 16000) -> int:
    """Calculate number of samples for a given duration.

    Args:
        duration_ms: Duration in milliseconds (e.g., 10, 20, 30)
        sample_rate: Sample rate in Hz (default: 16000)

    Returns:
        Number of samples

    Examples:
        >>> calculate_frame_count(10, 16000)  # 10ms at 16kHz
        160
        >>> calculate_frame_count(20, 16000)  # 20ms at 16kHz
        320
    """
    return int(sample_rate * duration_ms / 1000)


def split_into_frames(
    audio: np.ndarray,
    frame_size: int,
    hop_size: int | None = None,
) -> list[np.ndarray]:
    """Split audio into fixed-size frames.

    Args:
        audio: Input audio array
        frame_size: Size of each frame in samples
        hop_size: Hop size between frames (default: frame_size, no overlap)

    Returns:
        List of audio frames

    Examples:
        >>> audio = np.arange(1000)
        >>> frames = split_into_frames(audio, 160)  # 10ms frames at 16kHz
        >>> len(frames)
        6  # 1000 / 160 = 6.25, so 6 complete frames
    """
    if hop_size is None:
        hop_size = frame_size

    frames = []
    for i in range(0, len(audio) - frame_size + 1, hop_size):
        frames.append(audio[i : i + frame_size])

    return frames


def get_voice_frame_params() -> dict:
    """Get standard voice processing frame parameters.

    Returns:
        Dictionary with sample_rate, frame_duration_ms, frame_size

    Examples:
        >>> params = get_voice_frame_params()
        >>> params['sample_rate']
        16000
        >>> params['frame_duration_ms']
        10
        >>> params['frame_size']
        160
    """
    return {
        "sample_rate": 16000,
        "frame_duration_ms": 10,
        "frame_size": 160,  # 10ms at 16kHz
        "dtype": "int16",
        "channels": 1,
    }
