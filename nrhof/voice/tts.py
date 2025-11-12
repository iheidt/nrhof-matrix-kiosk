#!/usr/bin/env python3
"""Text-to-Speech stub.

Uses macOS 'say' command for quick testing.
"""

import os

from nrhof.core.event_bus import get_event_bus
from nrhof.core.logging_utils import setup_logger

logger = setup_logger(__name__)


class TTS:
    """Stub for system TTS using macOS 'say'."""

    def __init__(self):
        """Initialize TTS stub."""
        self.event_bus = get_event_bus()
        logger.info("TTS stub initialized (macOS 'say')")

    def speak(self, text: str):
        """Speak text using system TTS.

        Args:
            text: Text to speak
        """
        logger.info(f"TTS speaking: {text}")
        # Future: emit VOICE_COMMAND_PROCESSING
        os.system(f"say '{text}' &")
        # Future: emit VOICE_COMMAND_SUCCESS
