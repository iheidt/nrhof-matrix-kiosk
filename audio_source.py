#!/usr/bin/env python3
"""
Centralized audio source module.
Provides get_audio_frame() that works on Mac (microphone) or Pi (fallback to sine wave).

NOTE: This module now wraps core.audio_io for backward compatibility.
New code should use core.audio_io directly.
"""

import math

import numpy as np

from nrhof.core.audio_io import (
    cleanup as audio_io_cleanup,
)
from nrhof.core.audio_io import (
    get_mic_frame,
    get_mic_frame_size,
    get_mic_sample_rate,
    get_mic_stream,
)

# Fallback sine wave state
_fallback_time = 0.0
_fallback_freq = 220.0  # A3 note
_mic_initialized = False


def _init_microphone():
    """Initialize microphone input stream (wrapper for audio_io)."""
    global _mic_initialized

    if _mic_initialized:
        return True

    # Use audio_io abstraction
    sample_rate = 16000  # Porcupine sample rate
    frame_size = 512  # Porcupine frame length

    success = get_mic_stream(sample_rate, frame_size)
    if success:
        _mic_initialized = True
    return success


def _generate_sine_frame():
    """Generate a sine wave frame as fallback."""
    global _fallback_time

    sample_rate = get_mic_sample_rate()
    frame_size = get_mic_frame_size()

    t = np.arange(frame_size, dtype=np.float32) / float(sample_rate)
    t += _fallback_time

    # Generate sine wave
    frame = np.sin(2.0 * math.pi * _fallback_freq * t).astype(np.float32)

    # Update time offset
    _fallback_time += frame_size / float(sample_rate)

    return frame


def get_audio_frame(length: int = None) -> np.ndarray:
    """Get an audio frame from microphone or fallback to sine wave.

    Args:
        length: Optional desired frame length (defaults to internal buffer size)

    Returns:
        numpy array of float32 audio samples in range [-1, 1]
    """
    global _mic_initialized

    # Initialize on first call
    if not _mic_initialized:
        if not _init_microphone():
            # Microphone failed, will use sine fallback
            pass

    # Try to get microphone frame
    frame = get_mic_frame()

    # Fallback to sine wave if mic not available
    if frame is None:
        frame = _generate_sine_frame()

    # Resize if requested length differs
    if length is not None and len(frame) != length:
        if len(frame) > length:
            frame = frame[:length]
        else:
            # Pad with zeros
            frame = np.pad(frame, (0, length - len(frame)), mode="constant")

    return frame


def get_sample_rate() -> int:
    """Get the current sample rate."""
    return get_mic_sample_rate()


def get_buffer_size() -> int:
    """Get the current buffer size."""
    return get_mic_frame_size()


def set_fallback_frequency(freq: float):
    """Set the frequency for sine wave fallback.

    Args:
        freq: Frequency in Hz (default 220.0)
    """
    global _fallback_freq
    _fallback_freq = freq


def cleanup():
    """Clean up audio resources."""
    # Delegate to audio_io
    audio_io_cleanup()
