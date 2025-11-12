#!/usr/bin/env python3
"""Natural Language Understanding stub.

Future: Grammar-based intent classifier.
"""

from core.event_bus import get_event_bus
from core.logger import get_logger

logger = get_logger(__name__)


class GrammarNLU:
    """Stub grammar-based intent classifier."""

    def __init__(self):
        """Initialize NLU stub."""
        self.event_bus = get_event_bus()
        logger.info("GrammarNLU stub initialized")

    def classify(self, text: str) -> dict:
        """Classify text into intent.

        Args:
            text: Transcribed text to classify

        Returns:
            Intent dictionary (empty in stub)

        Future: Implement deterministic mapping and emit VOICE_INTENT_RECOGNIZED
        """
        logger.info(f"NLU classify (stub): {text}")
        # Future: emit VOICE_INTENT_RECOGNIZED event
        return {}
