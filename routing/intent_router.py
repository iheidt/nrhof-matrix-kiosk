#!/usr/bin/env python3
from enum import Enum
from typing import Callable, Dict, Union


class Intent(str, Enum):
    """Intent constants for type-safe intent routing.
    
    Inherits from str to maintain backward compatibility with string-based lookups.
    """
    GO_HOME = "go_home"
    GO_BACK = "go_back"
    GO_TO_SETTINGS = "go_to_settings"
    SELECT_OPTION = "select_option"
    SELECT_SUB_EXPERIENCE = "select_sub_experience"
    
    def __str__(self) -> str:
        """Return the string value for compatibility."""
        return self.value


# Backward compatibility alias
Intents = Intent


class IntentRouter:
    """Routes intents to registered handlers."""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
    
    def register(self, handler_name: Union[Intent, str], callback: Callable):
        """Register an intent handler.
        
        Args:
            handler_name: Intent enum or string name of the intent to handle
            callback: Function to call when intent is emitted
        """
        # Convert Intent enum to string for storage
        key = str(handler_name) if isinstance(handler_name, Intent) else handler_name
        self.handlers[key] = callback
    
    def emit(self, handler_name: Union[Intent, str], **kwargs):
        """Emit an intent with optional parameters.
        
        Args:
            handler_name: Intent enum or string name of the intent to emit
            **kwargs: Additional parameters to pass to the handler
        """
        # Convert Intent enum to string for lookup
        key = str(handler_name) if isinstance(handler_name, Intent) else handler_name
        
        # Log the intent
        if kwargs:
            params_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
            print(f"Intent emitted: {key} {params_str}")
        else:
            print(f"Intent emitted: {key}")
        
        # Dispatch to handler if it exists
        if key in self.handlers:
            self.handlers[key](**kwargs)
        else:
            # Silently ignore if handler not found
            pass
