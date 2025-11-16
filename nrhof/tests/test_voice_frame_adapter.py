#!/usr/bin/env python3
"""Tests for KoalaFrameAdapter frame size conversion."""

import numpy as np

from nrhof.voice.koala import KoalaFrameAdapter


class MockKoala:
    """Mock Koala for testing."""

    def __init__(self):
        self.frame_length = 256
        self.sample_rate = 16000

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Echo input frame (no actual processing)."""
        return frame


class TestKoalaFrameAdapter:
    """Test KoalaFrameAdapter buffering logic."""

    def test_adapter_initialization(self):
        """Test adapter initializes with correct parameters."""
        koala = MockKoala()
        adapter = KoalaFrameAdapter(koala, target_frame_size=512)

        assert adapter.koala_frame_size == 256
        assert adapter.target_frame_size == 512
        assert len(adapter.input_buffer) == 0
        assert len(adapter.output_buffer) == 0

    def test_single_frame_no_output(self):
        """Test that single 256-sample frame doesn't yield output yet."""
        koala = MockKoala()
        adapter = KoalaFrameAdapter(koala, target_frame_size=512)

        frame_256 = np.random.randint(-32768, 32767, 256, dtype=np.int16)
        output = adapter.process(frame_256)

        assert len(output) == 0  # Not enough samples yet
        assert len(adapter.output_buffer) == 256  # Buffered for next call

    def test_two_frames_yields_one_output(self):
        """Test that two 256-sample frames yield one 512-sample frame."""
        koala = MockKoala()
        adapter = KoalaFrameAdapter(koala, target_frame_size=512)

        frame1 = np.random.randint(-32768, 32767, 256, dtype=np.int16)
        frame2 = np.random.randint(-32768, 32767, 256, dtype=np.int16)

        output1 = adapter.process(frame1)
        assert len(output1) == 0

        output2 = adapter.process(frame2)
        assert len(output2) == 1
        assert len(output2[0]) == 512

    def test_large_input_yields_multiple_outputs(self):
        """Test that large input (1024 samples) yields multiple 512-sample frames."""
        koala = MockKoala()
        adapter = KoalaFrameAdapter(koala, target_frame_size=512)

        large_frame = np.random.randint(-32768, 32767, 1024, dtype=np.int16)
        outputs = adapter.process(large_frame)

        # 1024 samples -> 4x 256-sample Koala calls -> 1024 output -> 2x 512-sample frames
        assert len(outputs) == 2
        assert all(len(frame) == 512 for frame in outputs)

    def test_exact_target_size(self):
        """Test input exactly matching target size."""
        koala = MockKoala()
        adapter = KoalaFrameAdapter(koala, target_frame_size=512)

        frame_512 = np.random.randint(-32768, 32767, 512, dtype=np.int16)
        outputs = adapter.process(frame_512)

        assert len(outputs) == 1
        assert len(outputs[0]) == 512

    def test_reset_clears_buffers(self):
        """Test reset clears internal buffers."""
        koala = MockKoala()
        adapter = KoalaFrameAdapter(koala, target_frame_size=512)

        frame_256 = np.random.randint(-32768, 32767, 256, dtype=np.int16)
        adapter.process(frame_256)

        assert len(adapter.output_buffer) > 0

        adapter.reset()

        assert len(adapter.input_buffer) == 0
        assert len(adapter.output_buffer) == 0

    def test_data_integrity(self):
        """Test that data is preserved through buffering."""
        koala = MockKoala()
        adapter = KoalaFrameAdapter(koala, target_frame_size=512)

        # Create distinctive frames
        frame1 = np.full(256, 100, dtype=np.int16)
        frame2 = np.full(256, 200, dtype=np.int16)

        adapter.process(frame1)
        outputs = adapter.process(frame2)

        assert len(outputs) == 1
        # First half should be 100s, second half 200s
        assert np.all(outputs[0][:256] == 100)
        assert np.all(outputs[0][256:] == 200)

    def test_odd_frame_size_conversion(self):
        """Test conversion from 256 to non-standard target size."""
        koala = MockKoala()
        adapter = KoalaFrameAdapter(koala, target_frame_size=384)  # 1.5x Koala size

        # Feed 768 samples (3x 256) -> should yield 2x 384 frames
        frame_768 = np.random.randint(-32768, 32767, 768, dtype=np.int16)
        outputs = adapter.process(frame_768)

        assert len(outputs) == 2
        assert all(len(frame) == 384 for frame in outputs)
