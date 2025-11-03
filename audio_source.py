#!/usr/bin/env python3
"""
Centralized audio source module.
Provides get_audio_frame() that works on Mac (microphone) or Pi (fallback to sine wave).
"""
import numpy as np
import math
import time

# Try to import sounddevice
try:
    import sounddevice as sd
    HAVE_SOUNDDEVICE = True
except ImportError:
    HAVE_SOUNDDEVICE = False
    print("Warning: sounddevice not available, using sine wave fallback")

# Global state
_audio_stream = None
_audio_buffer = None
_buffer_size = 2048
_sample_rate = 44100
_fallback_time = 0.0
_fallback_freq = 220.0  # A3 note


def _audio_callback(indata, frames, time_info, status):
    """Callback for sounddevice stream."""
    global _audio_buffer
    if status:
        print(f"Audio status: {status}")
    _audio_buffer = indata[:, 0].copy()  # Mono channel


def _init_microphone():
    """Initialize microphone input stream."""
    global _audio_stream, _audio_buffer
    
    if not HAVE_SOUNDDEVICE:
        return False
    
    try:
        # Find the best available input device
        # Prefer USB/external devices over built-in/iPhone
        devices = sd.query_devices()
        input_device = None
        fallback_device = None
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                name_lower = device['name'].lower()
                
                # Skip iPhone/iPad devices
                if 'iphone' in name_lower or 'ipad' in name_lower:
                    continue
                
                # Prefer USB devices
                if 'usb' in name_lower:
                    input_device = i
                    print(f"Audio: Using USB device {i}: {device['name']}")
                    break
                
                # Save first non-iPhone device as fallback
                if fallback_device is None:
                    fallback_device = i
        
        # Use fallback if no USB device found
        if input_device is None:
            input_device = fallback_device
            if input_device is not None:
                print(f"Audio: Using device {i}: {devices[input_device]['name']}")
        
        _audio_buffer = np.zeros(_buffer_size, dtype=np.float32)
        _audio_stream = sd.InputStream(
            device=input_device,
            channels=1,
            samplerate=_sample_rate,
            blocksize=_buffer_size,
            callback=_audio_callback
        )
        _audio_stream.start()
        print(f"Audio: Microphone initialized ({_sample_rate}Hz, {_buffer_size} samples)")
        print(f"Audio: Device {input_device}, Channels: 1, Sample rate: {_sample_rate}")
        return True
    except Exception as e:
        import traceback
        print(f"Audio: Failed to initialize microphone: {e}")
        print(f"Audio: Full traceback:")
        traceback.print_exc()
        return False


def _generate_sine_frame():
    """Generate a sine wave frame as fallback."""
    global _fallback_time
    
    t = np.arange(_buffer_size, dtype=np.float32) / float(_sample_rate)
    t += _fallback_time
    
    # Generate sine wave
    frame = np.sin(2.0 * math.pi * _fallback_freq * t).astype(np.float32)
    
    # Update time offset
    _fallback_time += _buffer_size / float(_sample_rate)
    
    return frame


def get_audio_frame(length: int = None) -> np.ndarray:
    """Get an audio frame from microphone or fallback to sine wave.
    
    Args:
        length: Optional desired frame length (defaults to internal buffer size)
        
    Returns:
        numpy array of float32 audio samples in range [-1, 1]
    """
    global _audio_stream, _audio_buffer
    
    # Initialize on first call
    if _audio_stream is None and _audio_buffer is None:
        if not _init_microphone():
            # Microphone failed, will use sine fallback
            pass
    
    # Use microphone if available
    if _audio_buffer is not None:
        frame = _audio_buffer.copy()
    else:
        # Fallback to sine wave
        frame = _generate_sine_frame()
    
    # Resize if requested length differs
    if length is not None and len(frame) != length:
        if len(frame) > length:
            frame = frame[:length]
        else:
            # Pad with zeros
            frame = np.pad(frame, (0, length - len(frame)), mode='constant')
    
    return frame


def get_sample_rate() -> int:
    """Get the current sample rate."""
    return _sample_rate


def get_buffer_size() -> int:
    """Get the current buffer size."""
    return _buffer_size


def set_fallback_frequency(freq: float):
    """Set the frequency for sine wave fallback.
    
    Args:
        freq: Frequency in Hz (default 220.0)
    """
    global _fallback_freq
    _fallback_freq = freq


def cleanup():
    """Clean up audio resources."""
    global _audio_stream
    if _audio_stream is not None:
        try:
            _audio_stream.stop()
            _audio_stream.close()
        except Exception:
            pass
        _audio_stream = None


# Cleanup on module unload
import atexit
atexit.register(cleanup)