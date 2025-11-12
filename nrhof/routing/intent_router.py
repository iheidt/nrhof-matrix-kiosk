#!/usr/bin/env python3
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
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    SET_VOLUME = "set_volume"

    # System intents (voice-ready)
    CHANGE_LANGUAGE = "change_language"

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
            print(f"Intent emitted: {key} {params_str}")
        else:
            print(f"Intent emitted: {key}")

        # Dispatch to handler if it exists
        if key in self.handlers:
            # Call with unified signature: handler(event_bus, **slots)
            self.handlers[key](self.event_bus, **slots)
        else:
            # Silently ignore if handler not found
            pass
