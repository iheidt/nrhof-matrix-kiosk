#!/usr/bin/env python3
import logging
from collections.abc import Callable
from enum import Enum


class Intent(str, Enum):
    """Intent constants for type-safe intent routing.

    Inherits from str to maintain backward compatibility with string-based lookups.
    """

    # Navigation intents
    GO_HOME = "go_home"
    GO_BACK = "go_back"
    GO_TO_SETTINGS = "go_to_settings"
    GO_TO_BAND_DETAILS = "go_to_band_details"

    # Selection intents
    SELECT_OPTION = "select_option"
    SELECT_SUB_EXPERIENCE = "select_sub_experience"

    # Media control intents (voice-ready)
    PAUSE = "pause"
    RESUME = "resume"
    NEXT = "next"
    PREVIOUS = "previous"
    RESTART_TRACK = "restart_track"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    SET_VOLUME = "set_volume"

    # Video intents
    PLAY_MUSIC_VIDEO = "play_music_video"
    STOP_VIDEO = "stop_video"

    # System intents (voice-ready)
    CHANGE_LANGUAGE = "change_language"
    CHANGE_MODE = "change_mode"
    CHANGE_VOICE = "change_voice"

    # Special feature intents
    ROLL_FATE = "roll_fate"

    def __str__(self) -> str:
        """Return the string value for compatibility."""
        return self.value


# Backward compatibility alias
Intents = Intent


class IntentRouter:
    """Routes intents to registered handlers.

    All handlers follow the signature: handler(event_bus, **slots)
    This allows handlers to emit events and access slots (intent parameters).
    """

    def __init__(self, event_bus=None):
        """Initialize IntentRouter.

        Args:
            event_bus: EventBus instance (injected, not imported globally)
        """
        self.handlers: dict[str, Callable] = {}
        self.event_bus = event_bus
        self._scene_controller = None  # Injected scene controller (breaks circular dep)
        self.logger = logging.getLogger(__name__)

    def set_scene_controller(self, controller):
        """Inject scene controller for navigation.

        Args:
            controller: Object with switch_to() and go_back() methods
        """
        self._scene_controller = controller

    def get_scene_controller(self):
        """Get the injected scene controller.

        Returns:
            Scene controller instance or None
        """
        return self._scene_controller

    def register(self, handler_name: Intent | str, callback: Callable):
        """Register an intent handler.

        Args:
            handler_name: Intent enum or string name of the intent to handle
            callback: Function to call when intent is emitted
        """
        # Convert Intent enum to string for storage
        key = str(handler_name) if isinstance(handler_name, Intent) else handler_name
        self.handlers[key] = callback

    def emit(self, handler_name: Intent | str, **slots):
        """Emit an intent with optional slot parameters.

        Args:
            handler_name: Intent enum or string name of the intent to emit
            **slots: Slot parameters to pass to the handler (e.g., index=0, volume=50)
        """
        # Convert Intent enum to string for lookup
        key = str(handler_name) if isinstance(handler_name, Intent) else handler_name

        # Log the intent
        if slots:
            params_str = " ".join(f"{k}={v}" for k, v in slots.items())
            self.logger.debug(f"Intent emitted: {key} {params_str}")
        else:
            self.logger.debug(f"Intent emitted: {key}")

        # Dispatch to handler if it exists
        if key in self.handlers:
            # Call with unified signature: handler(event_bus, **slots)
            self.handlers[key](self.event_bus, **slots)
        else:
            # Silently ignore if handler not found
            pass

    def route_voice_intent(self, intent_name: str, slots: dict):
        """Route voice intent to appropriate app intent.

        Handles three cases (in priority order):
        1. LLM aliases (e.g., "PAUSE" → "pausePlayback") via LLM_INTENT_MAP
        2. Rhino canonical names (e.g., "pausePlayback" → Intent.PAUSE)
        3. Direct Intent enum names (future-proof for new intents)

        Args:
            intent_name: Intent name from Rhino or LLM
            slots: Slot parameters
        """
        from nrhof.routing.llm_intent_map import LLM_INTENT_MAP

        # Step 1: Check if it's an LLM alias that needs translation
        if intent_name in LLM_INTENT_MAP:
            canonical_name = LLM_INTENT_MAP[intent_name]
            self.logger.info(f"Translating LLM alias: {intent_name} → {canonical_name}")
            intent_name = canonical_name  # Use canonical name for next steps

        # Map Rhino intent names to Intent enums and optional slot transformations
        # Format: {rhino_intent: (Intent, slot_overrides)}
        # Mapped from nrhof_picovoice.yml context file
        intent_map = {
            # ===== NAVIGATION INTENTS (WORKING) =====
            "goHome": (Intent.GO_HOME, {}),
            "goBack": (Intent.GO_BACK, {}),
            "goToSettings": (Intent.GO_TO_SETTINGS, {}),
            "goToNR38": (Intent.SELECT_OPTION, {"index": 0}),  # NR-38 scene
            "goToNR18": (Intent.SELECT_OPTION, {"index": 1}),  # NR-18 (placeholder)
            "goToVisualizers": (Intent.SELECT_OPTION, {"index": 2}),  # Visualizers scene
            "goToFateMaker": (Intent.SELECT_OPTION, {"index": 3}),  # Fate Maker (placeholder)
            # ===== FATE MAKER INTENTS (NOT IMPLEMENTED) =====
            "rollFate": (Intent.ROLL_FATE, {}),  # Roll fate/reroll
            # ===== MEDIA CONTROL INTENTS (STUBS EXIST) =====
            "nextTrack": (Intent.NEXT, {}),
            "previousTrack": (Intent.PREVIOUS, {}),
            "pausePlayback": (Intent.PAUSE, {}),
            "resumePlayback": (Intent.RESUME, {}),
            "restartTrack": (Intent.RESTART_TRACK, {}),
            # ===== VIDEO INTENTS (NOT IMPLEMENTED) =====
            "playMusicVideo": (Intent.PLAY_MUSIC_VIDEO, {}),
            "stopVideo": (Intent.STOP_VIDEO, {}),
            # ===== SYSTEM INTENTS (PARTIAL) =====
            "changeLanguage": (Intent.CHANGE_LANGUAGE, {}),  # Handler exists
            "changeMode": (Intent.CHANGE_MODE, {}),  # Not implemented
            "changeVoice": (Intent.CHANGE_VOICE, {}),  # Not implemented
            # ===== VOLUME INTENTS (STUBS EXIST) =====
            "increaseVolume": (Intent.VOLUME_UP, {}),
            "decreaseVolume": (Intent.VOLUME_DOWN, {}),
        }

        # Look up the mapped intent
        mapping = intent_map.get(intent_name)

        if mapping:
            intent, slot_overrides = mapping
            # Merge Rhino slots with default overrides (overrides take precedence)
            final_slots = {**slots, **slot_overrides}

            self.logger.info(
                f"Routing voice intent: {intent_name} -> {intent} " f"with slots {final_slots}"
            )
            self.emit(intent, **final_slots)
        else:
            self.logger.warning(f"No mapping found for voice intent: {intent_name}")
