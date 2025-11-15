"""Voice event handler - responds to wake word and VAD events."""

from nrhof.core.app_state import get_app_state
from nrhof.core.event_bus import EventType, get_event_bus
from nrhof.core.logging_utils import setup_logger

logger = setup_logger(__name__)


class VoiceEventHandler:
    """Handles voice-related events (wake word, VAD, etc.)."""

    def __init__(self, intent_router=None):
        """Initialize voice event handler.

        Args:
            intent_router: Optional IntentRouter for voice intent routing
        """
        self.event_bus = get_event_bus()
        self.app_state = get_app_state()
        self.intent_router = intent_router
        self.is_listening = False

        # Subscribe to events
        self.event_bus.subscribe(EventType.WAKE_WORD_DETECTED, self._on_wake_word)
        self.event_bus.subscribe(EventType.VOICE_SPEECH_START, self._on_speech_start)
        self.event_bus.subscribe(EventType.VOICE_SPEECH_END, self._on_speech_end)
        self.event_bus.subscribe(EventType.VOICE_TIMEOUT, self._on_timeout)
        self.event_bus.subscribe(EventType.VOICE_INTENT_RESOLVED, self._on_intent_resolved)

        logger.info("Voice event handler initialized")

    def _on_wake_word(self, event):
        """Handle wake word detection.

        Sets status to 'Listening...' and emits MIXER_DUCK event.
        """
        keyword = event.payload.get("keyword", "unknown") if event.payload else "unknown"
        logger.info(f"Wake word detected: {keyword}")

        # Set status
        self.app_state.set_status("listening...")
        self.is_listening = True

        # Duck audio for voice interaction
        self.event_bus.emit(EventType.MIXER_DUCK, payload={"gain_db": -20})
        logger.info("Audio ducked for voice interaction")

    def _on_speech_start(self, event):
        """Handle speech start from VAD.

        Only acts if we're in listening mode (after wake word).
        """
        if self.is_listening:
            logger.info("Speech started (VAD)")
            # Keep status as 'listening...'
            # Could add visual feedback here

    def _on_speech_end(self, event):
        """Handle speech end from VAD.

        Clears status and emits MIXER_UNDUCK event.
        """
        if self.is_listening:
            logger.info("Speech ended (VAD)")

            # Clear status
            self.app_state.clear_status()
            self.is_listening = False

            # Restore audio
            self.event_bus.emit(EventType.MIXER_UNDUCK)
            logger.info("Audio restored after voice interaction")

    def _on_timeout(self, event):
        """Handle speech timeout (no speech after wake word).

        Clears status and emits MIXER_UNDUCK event.
        """
        if self.is_listening:
            logger.info("Voice timeout - no speech detected")

            # Clear status
            self.app_state.clear_status()
            self.is_listening = False

            # Restore audio
            self.event_bus.emit(EventType.MIXER_UNDUCK)
            logger.info("Audio restored after timeout")

    def _on_intent_resolved(self, event):
        """Handle intent resolved by Rhino NLU.

        Routes intent to IntentRouter for execution.
        """
        if not event.payload:
            return

        intent = event.payload.get("intent")
        slots = event.payload.get("slots", {})

        logger.info(f"Intent resolved: {intent}, slots={slots}")

        # Route to IntentRouter if available
        if self.intent_router:
            try:
                self.intent_router.route_voice_intent(intent, slots)
            except Exception as e:
                logger.error(f"Failed to route voice intent: {e}")
        else:
            logger.warning("No IntentRouter available for voice intent routing")


# Global instance
_voice_event_handler = None


def get_voice_event_handler() -> VoiceEventHandler:
    """Get global voice event handler instance."""
    global _voice_event_handler
    if _voice_event_handler is None:
        _voice_event_handler = VoiceEventHandler()
    return _voice_event_handler


def init_voice_event_handler(intent_router=None):
    """Initialize voice event handler.

    Args:
        intent_router: Optional IntentRouter for voice intent routing

    Call this during app startup to register event handlers.
    """
    global _voice_event_handler
    if _voice_event_handler is None:
        _voice_event_handler = VoiceEventHandler(intent_router=intent_router)
    elif intent_router and not _voice_event_handler.intent_router:
        # Update existing handler with intent_router if not already set
        _voice_event_handler.intent_router = intent_router

    logger.info("Voice event handler registered")
    return _voice_event_handler
