#!/usr/bin/env python3
"""ASR (Automatic Speech Recognition) worker.

Listens for VOICE_SEGMENT_READY events (when Rhino fails to recognize intent)
and transcribes the audio using Whisper ASR.
"""

import numpy as np

from nrhof.core.event_bus import EventType
from nrhof.core.logging_utils import setup_logger
from nrhof.voice.whisper_client import WhisperClient
from nrhof.workers.base import BaseWorker

logger = setup_logger(__name__)


class ASRWorker(BaseWorker):
    """ASR worker for Whisper transcription fallback."""

    def __init__(self, config: dict):
        """Initialize ASR worker.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config, logger_name="asr_worker")

        # Get Whisper config
        whisper_config = config.get("whisper", {})
        self.enabled = whisper_config.get("enabled", True)
        server_url = whisper_config.get("server_url", "http://127.0.0.1:9001")
        timeout = whisper_config.get("timeout", 5.0)

        if not self.enabled:
            self.logger.info("ASR worker disabled by config")
            return

        # Initialize Whisper client
        self.whisper = WhisperClient(server_url=server_url, timeout=timeout)

        # Check if Whisper server is available
        if not self.whisper.is_available():
            self.logger.warning(f"Whisper server not available at {server_url} - ASR will not work")
            self.logger.warning(
                "Start whisper.cpp server: ./whisper-server -m models/ggml-base.en.bin --port 9001"
            )

        # Subscribe to VOICE_SEGMENT_READY events
        self.event_bus.subscribe(EventType.VOICE_SEGMENT_READY, self._on_segment_ready)
        self.logger.info("ASR worker initialized (listening for VOICE_SEGMENT_READY)")

    def start(self):
        """Start ASR worker."""
        if not self.enabled:
            self.logger.info("ASR worker not started (disabled)")
            return
        super().start()

    def _worker_loop(self):
        """ASR worker is event-driven, no polling loop needed."""
        self.logger.info("ASR worker running (event-driven)")
        # Keep thread alive but idle
        import time

        while self._running:
            time.sleep(1.0)

    def _on_segment_ready(self, event):
        """Handle VOICE_SEGMENT_READY event.

        Args:
            event: Event object with payload containing PCM audio
        """
        try:
            # Event is a dataclass with .payload attribute
            payload = event.payload if hasattr(event, "payload") else event
            pcm = payload.get("pcm")
            sample_rate = payload.get("sample_rate", 16000)

            if pcm is None:
                self.logger.warning("VOICE_SEGMENT_READY event missing PCM data")
                return

            # Ensure PCM is int16 numpy array
            if not isinstance(pcm, np.ndarray):
                pcm = np.array(pcm, dtype=np.int16)
            elif pcm.dtype != np.int16:
                pcm = pcm.astype(np.int16)

            duration_ms = (len(pcm) / sample_rate) * 1000
            self.logger.info(f"[ASR] Transcribing {len(pcm)} samples ({duration_ms:.0f}ms)")

            # Transcribe with Whisper
            transcript = self.whisper.transcribe(pcm, sample_rate=sample_rate)

            if transcript:
                self.logger.info(f"[ASR] Transcript: '{transcript}'")
                # Emit transcript for LLM processing (Phase 5)
                self.event_bus.emit(
                    EventType.VOICE_TRANSCRIPTION_READY, payload={"transcript": transcript}
                )
            else:
                self.logger.info("[ASR] No transcript (silence or error)")

        except Exception as e:
            self.logger.error(f"ASR processing failed: {e}")

    def _cleanup(self):
        """Cleanup resources."""
        self.event_bus.unsubscribe(EventType.VOICE_SEGMENT_READY, self._on_segment_ready)
        self.logger.info("ASR worker cleanup complete")
