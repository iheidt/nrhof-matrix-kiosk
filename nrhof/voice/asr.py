#!/usr/bin/env python3
"""Automatic Speech Recognition stub.

Future: faster-whisper streaming ASR.
"""

from nrhof.core.event_bus import get_event_bus
from nrhof.core.logging_utils import setup_logger

logger = setup_logger(__name__)


class ASR:
    """Stub for streaming ASR (faster-whisper)."""

    def __init__(self, ctx=None):
        """Initialize ASR stub.

        Args:
            ctx: Application context (optional)
        """
        self.ctx = ctx
        self.event_bus = get_event_bus()
        logger.info("ASR stub initialized")

    def start(self):
        """Start ASR listening."""
        logger.info("ASR listening started (stub)")
        # Future: emit VOICE_LISTENING_START when implemented

    def stop(self):
        """Stop ASR listening."""
        logger.info("ASR listening stopped (stub)")
        # Future: emit VOICE_LISTENING_STOP when implemented

    def process(self, audio_frame):
        """Process audio frame for speech recognition.

        Args:
            audio_frame: Audio data to process

        Future: Emit VOICE_PARTIAL_TRANSCRIPT every 300-500ms
        """
        pass
