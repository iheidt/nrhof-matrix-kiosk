#!/usr/bin/env python3
"""Acoustic Echo Cancellation stub.

Future: Implement AEC to remove speaker output from mic input.
"""

from nrhof.core.logger import get_logger

logger = get_logger(__name__)


class AEC:
    """Stub for acoustic echo cancellation (pass-through)."""

    def __init__(self):
        """Initialize AEC stub."""
        logger.info("AEC stub initialized (pass-through)")

    def feed_farend(self, pcm_bytes: bytes):
        """Feed far-end (speaker) audio for echo cancellation.

        Args:
            pcm_bytes: PCM audio data from speaker output

        Future: Use this to cancel echo from mic input
        """
        pass
