#!/usr/bin/env python3
"""Tests for voice constants and helper functions."""


from nrhof.core.voice_constants import (
    KOALA_FRAME_SIZE,
    VOICE_FRAME_DURATION_MS,
    VOICE_FRAME_SIZE,
    VOICE_SAMPLE_RATE,
    frame_duration_ms,
    samples_from_ms,
)


class TestVoiceConstants:
    """Test voice pipeline constants."""

    def test_constants_are_correct(self):
        """Test that constants have expected values."""
        assert VOICE_SAMPLE_RATE == 16000
        assert VOICE_FRAME_SIZE == 512
        assert VOICE_FRAME_DURATION_MS == 32
        assert KOALA_FRAME_SIZE == 256

    def test_frame_alignment(self):
        """Test that frame size aligns with duration at sample rate."""
        calculated_samples = int(VOICE_SAMPLE_RATE * VOICE_FRAME_DURATION_MS / 1000)
        assert calculated_samples == VOICE_FRAME_SIZE


class TestFrameDurationMs:
    """Test frame_duration_ms helper function."""

    def test_standard_voice_frame(self):
        """Test calculation for standard 512-sample frame at 16kHz."""
        duration = frame_duration_ms(512, 16000)
        assert duration == 32.0

    def test_koala_frame(self):
        """Test calculation for Koala's 256-sample frame."""
        duration = frame_duration_ms(256, 16000)
        assert duration == 16.0

    def test_different_sample_rate(self):
        """Test calculation at different sample rate."""
        duration = frame_duration_ms(441, 44100)
        assert abs(duration - 10.0) < 0.01  # ~10ms


class TestSamplesFromMs:
    """Test samples_from_ms helper function."""

    def test_standard_voice_frame(self):
        """Test conversion from 32ms to samples at 16kHz."""
        samples = samples_from_ms(32.0, 16000)
        assert samples == 512

    def test_koala_frame(self):
        """Test conversion from 16ms to samples at 16kHz."""
        samples = samples_from_ms(16.0, 16000)
        assert samples == 256

    def test_silence_padding(self):
        """Test conversion for typical silence padding (800ms)."""
        samples = samples_from_ms(800.0, 16000)
        assert samples == 12800

    def test_round_down(self):
        """Test that fractional samples are rounded down."""
        samples = samples_from_ms(10.5, 16000)
        assert samples == 168  # int(16000 * 10.5 / 1000)

    def test_default_sample_rate(self):
        """Test that default sample rate is used when not specified."""
        samples = samples_from_ms(32.0)  # No sample_rate arg
        assert samples == 512


class TestFrameAlignment:
    """Test frame alignment calculations."""

    def test_voice_frame_is_multiple_of_koala(self):
        """Test that standard frame size is multiple of Koala frame size."""
        assert VOICE_FRAME_SIZE % KOALA_FRAME_SIZE == 0
        assert VOICE_FRAME_SIZE // KOALA_FRAME_SIZE == 2

    def test_typical_segment_alignment(self):
        """Test that typical speech segment aligns to frame size."""
        # 2 seconds of speech
        segment_samples = 2 * VOICE_SAMPLE_RATE  # 32000 samples
        remainder = segment_samples % VOICE_FRAME_SIZE

        if remainder != 0:
            # Calculate padding needed
            padding = VOICE_FRAME_SIZE - remainder
            assert (segment_samples + padding) % VOICE_FRAME_SIZE == 0
