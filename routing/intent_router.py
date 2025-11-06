#!/usr/bin/env python3
from typing import Callable, Dict


class Intents:
    """Intent name constants to prevent typos."""
    GO_HOME = "go_home"
    GO_BACK = "go_back"
    GO_TO_EXPERIENCE1_HUB = "go_to_experience1_hub"
    GO_TO_EXPERIENCE2_HUB = "go_to_experience2_hub"
    GO_TO_SETTINGS = "go_to_settings"
    SELECT_OPTION = "select_option"
    SELECT_SUB_EXPERIENCE = "select_sub_experience"


class IntentRouter:
    """Routes intents to registered handlers."""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
    
    def register(self, handler_name: str, callback: Callable):
        """Register an intent handler.
        
        Args:
            handler_name: Name of the intent to handle
            callback: Function to call when intent is emitted
        """
        self.handlers[handler_name] = callback
    
    def emit(self, handler_name: str, **kwargs):
        """Emit an intent with optional parameters.
        
        Args:
            handler_name: Name of the intent to emit
            **kwargs: Additional parameters to pass to the handler
        """
        # Log the intent
        if kwargs:
            params_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
            print(f"Intent emitted: {handler_name} {params_str}")
        else:
            print(f"Intent emitted: {handler_name}")
        
        # Dispatch to handler if it exists
        if handler_name in self.handlers:
            self.handlers[handler_name](**kwargs)
        else:
            # Silently ignore if handler not found
            pass
