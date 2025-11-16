#!/usr/bin/env python3
"""LLM worker for intent classification and chat.

Listens for VOICE_TRANSCRIPTION_READY events and classifies them using LLM.
"""

from nrhof.core.event_bus import EventType
from nrhof.core.logging_utils import setup_logger
from nrhof.voice.llm_client import LLMClient
from nrhof.workers.base import BaseWorker

logger = setup_logger(__name__)


class LLMWorker(BaseWorker):
    """LLM worker for intent classification."""

    def __init__(self, config: dict):
        """Initialize LLM worker.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config, logger_name="llm_worker")

        # Get LLM config
        llm_config = config.get("llm", {})
        self.enabled = llm_config.get("enabled", True)
        server_url = llm_config.get("server_url", "http://localhost:11434")
        model = llm_config.get("model", "llama3.1:8b")
        timeout = llm_config.get("timeout", 30.0)

        if not self.enabled:
            self.logger.info("LLM worker disabled by config")
            return

        # Initialize LLM client
        self.llm = LLMClient(server_url=server_url, model=model, timeout=timeout)

        # Check if LLM server is available
        if not self.llm.is_available():
            self.logger.warning(
                f"Ollama server not available at {server_url} - LLM classification will not work"
            )
            self.logger.warning("Start Ollama server: ollama serve")

        # Build list of available intents from LLM_INTENT_MAP (high-level aliases)
        from nrhof.routing.llm_intent_map import LLM_INTENT_MAP

        self.available_intents = sorted(LLM_INTENT_MAP.keys())
        self.logger.info(
            f"LLM worker initialized with {len(self.available_intents)} available intents"
        )

        # Subscribe to VOICE_TRANSCRIPTION_READY events
        self.event_bus.subscribe(EventType.VOICE_TRANSCRIPTION_READY, self._on_transcription_ready)
        self.logger.info("LLM worker initialized (listening for VOICE_TRANSCRIPTION_READY)")

    def start(self):
        """Start LLM worker."""
        if not self.enabled:
            self.logger.info("LLM worker not started (disabled)")
            return
        super().start()

    def _worker_loop(self):
        """LLM worker is event-driven, no polling loop needed."""
        self.logger.info("LLM worker running (event-driven)")
        # Keep thread alive but idle
        import time

        while self._running:
            time.sleep(1.0)

    def _on_transcription_ready(self, event):
        """Handle VOICE_TRANSCRIPTION_READY event.

        Args:
            event: Event object with payload containing transcript
        """
        try:
            # Event is a dataclass with .payload attribute
            payload = event.payload if hasattr(event, "payload") else event
            transcript = payload.get("transcript")

            if not transcript:
                self.logger.warning("VOICE_TRANSCRIPTION_READY event missing transcript")
                return

            self.logger.info(f"[LLM] Classifying transcript: '{transcript}'")

            # Classify intent with LLM
            classification = self.llm.classify_intent(transcript, self.available_intents)

            if classification.get("type") == "intent":
                # LLM classified as an intent
                intent_name = classification.get("intent")
                confidence = classification.get("confidence", 0.0)

                self.logger.info(
                    f"[LLM] ✓ Classified as intent: {intent_name} (confidence: {confidence:.2f})"
                )

                # Validate intent name exists (will be handled by intent router)
                # Just emit - the router handles validation and mapping
                self.event_bus.emit(
                    EventType.VOICE_INTENT_RECOGNIZED,
                    payload={"intent": intent_name, "slots": {}, "confidence": confidence},
                )

            elif classification.get("type") == "chat":
                # LLM classified as a chat/question
                response = classification.get("response", "I'm not sure how to help with that.")
                self.logger.info(f"[LLM] ✓ Classified as chat, suggested response: '{response}'")

                # TODO: Emit chat response event for TTS (Phase 6)
                # For now, just log it
                print(f"[CHAT] {response}")

            elif classification.get("type") == "error":
                # LLM error
                error_msg = classification.get("message", "Unknown error")
                self.logger.error(f"[LLM] Classification error: {error_msg}")

            else:
                self.logger.warning(f"[LLM] Unknown classification type: {classification}")

        except Exception as e:
            self.logger.error(f"LLM processing failed: {e}")

    def _cleanup(self):
        """Cleanup resources."""
        self.event_bus.unsubscribe(
            EventType.VOICE_TRANSCRIPTION_READY, self._on_transcription_ready
        )
        self.logger.info("LLM worker cleanup complete")
