#!/usr/bin/env python3
"""Audio I/O abstraction layer.

Provides unified interface for:
- Microphone input (sounddevice)
- Player tap for AEC (stub - returns zeros for now)
- Audio ducking for voice mode (stub - no-op for now)

This abstraction makes it easy to add AEC and ducking later without
changing worker code.
"""

import atexit
import threading

import numpy as np

from core.logger import get_logger

logger = get_logger("audio_io")

# Try to import sounddevice
try:
    import sounddevice as sd

    HAVE_SOUNDDEVICE = True
except ImportError:
    HAVE_SOUNDDEVICE = False
    logger.warning("sounddevice not available, microphone input disabled")

# Global state
_mic_stream: object | None = None
_mic_buffer: np.ndarray | None = None
_mic_sample_rate: int = 16000
_mic_frame_size: int = 512
_duck_gain_db: float = 0.0  # Current ducking gain (0 = no duck)
_mic_lock = threading.Lock()  # Prevent race condition on mic init


def _mic_callback(indata, frames, time_info, status):
    """Callback for microphone stream.

    Args:
        indata: Input audio data
        frames: Number of frames
        time_info: Timing information
        status: Stream status
    """
    global _mic_buffer
    if status and "overflow" not in str(status).lower():
        # Only log non-overflow errors
        logger.warning(f"Mic stream status: {status}")
    _mic_buffer = indata[:, 0].copy()  # Mono channel


def get_mic_stream(sample_rate: int = 16000, frame_size: int = 512) -> bool:
    """Initialize and start microphone input stream.

    Args:
        sample_rate: Sample rate in Hz (default: 16000)
        frame_size: Frame size in samples (default: 512)

    Returns:
        True if microphone initialized successfully, False otherwise
    """
    global _mic_stream, _mic_buffer, _mic_sample_rate, _mic_frame_size

    if not HAVE_SOUNDDEVICE:
        logger.error("Cannot initialize mic: sounddevice not available")
        return False

    # Use lock to prevent race condition when multiple workers init simultaneously
    with _mic_lock:
        # Already initialized?
        if _mic_stream is not None:
            # Check if stream is actually active
            try:
                if _mic_stream.active:
                    logger.debug("Mic stream already initialized and active")
                    return True
                else:
                    # Stream exists but not active, clean it up
                    logger.warning("Mic stream exists but not active, reinitializing")
                    try:
                        _mic_stream.stop()
                        _mic_stream.close()
                    except Exception:
                        pass
                    _mic_stream = None
            except Exception:
                # Stream is in bad state, clean it up
                logger.warning("Mic stream in bad state, reinitializing")
                _mic_stream = None

        _mic_sample_rate = sample_rate
        _mic_frame_size = frame_size

        try:
            # Find best input device
            input_device = None

            try:
                devices = sd.query_devices()

                for i, device in enumerate(devices):
                    if device["max_input_channels"] > 0:
                        name_lower = device["name"].lower()

                        # Skip iPhone/iPad devices (Mac only issue)
                        if "iphone" in name_lower or "ipad" in name_lower:
                            continue

                        # Prefer devices with 'usb' in name
                        if "usb" in name_lower:
                            input_device = i
                            logger.info(f"Using USB mic device {i}: {device['name']}")
                            break

                        # Use first available non-iPhone device
                        if input_device is None:
                            input_device = i
                            logger.info(f"Using mic device {i}: {device['name']}")
            except Exception as e:
                logger.warning(f"Device enumeration failed: {e}, using default")

            # Initialize buffer and stream
            _mic_buffer = np.zeros(frame_size, dtype=np.float32)
            _mic_stream = sd.InputStream(
                device=input_device,
                channels=1,
                samplerate=sample_rate,
                blocksize=frame_size,
                latency="high",  # Reduce overflow risk
                callback=_mic_callback,
            )
            _mic_stream.start()
            logger.info(
                f"Mic stream initialized: {sample_rate}Hz, {frame_size} samples, device={input_device}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize mic stream: {e}")
            return False


def get_mic_frame() -> np.ndarray | None:
    """Get latest microphone frame.

    Returns:
        numpy array of float32 audio samples in range [-1, 1], or None if not available
    """
    global _mic_buffer

    if _mic_buffer is None:
        return None

    return _mic_buffer.copy()


def get_player_tap(sample_rate: int = 16000, frame_size: int = 512) -> np.ndarray:
    """Get audio being played (for AEC reference).

    STUB: Currently returns zeros. Will be implemented later to tap into
    the audio player for acoustic echo cancellation.

    Args:
        sample_rate: Sample rate in Hz (default: 16000)
        frame_size: Frame size in samples (default: 512)

    Returns:
        numpy array of float32 zeros (stub implementation)
    """
    # TODO: Implement real player tap for AEC
    # This will eventually tap into pygame.mixer or the audio output
    # to get the reference signal for echo cancellation
    return np.zeros(frame_size, dtype=np.float32)


def set_duck(gain_db: float):
    """Set audio ducking gain for voice mode.

    STUB: Currently a no-op. Will be implemented later to reduce
    background audio volume during voice interactions.

    Args:
        gain_db: Gain reduction in dB (negative value, e.g., -12.0 for 12dB reduction)
    """
    global _duck_gain_db
    _duck_gain_db = gain_db
    # TODO: Implement actual ducking by reducing pygame.mixer volume
    # or applying gain to audio output
    logger.debug(f"Duck gain set to {gain_db}dB (stub - not applied yet)")


def clear_duck():
    """Clear audio ducking (restore normal volume).

    STUB: Currently a no-op. Will be implemented later.
    """
    global _duck_gain_db
    _duck_gain_db = 0.0
    # TODO: Implement actual ducking clear
    logger.debug("Duck cleared (stub - not applied yet)")


def get_mic_sample_rate() -> int:
    """Get microphone sample rate.

    Returns:
        Sample rate in Hz
    """
    return _mic_sample_rate


def get_mic_frame_size() -> int:
    """Get microphone frame size.

    Returns:
        Frame size in samples
    """
    return _mic_frame_size


def cleanup():
    """Clean up audio I/O resources."""
    global _mic_stream, _mic_buffer

    if _mic_stream is not None:
        try:
            _mic_stream.stop()
            _mic_stream.close()
            logger.info("Mic stream closed")
        except Exception as e:
            logger.warning(f"Error closing mic stream: {e}")
        _mic_stream = None
        _mic_buffer = None


# Cleanup on module unload
atexit.register(cleanup)
