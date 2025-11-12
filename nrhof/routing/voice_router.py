#!/usr/bin/env python3
from collections.abc import Callable


class VoiceRouter:
    """Routes voice commands to registered callbacks."""

    def __init__(self):
        self.commands: dict[str, Callable] = {}

    def register_command(self, keyword: str, callback: Callable):
        """Register a voice command keyword with its callback.

        Args:
            keyword: The keyword to listen for (case-insensitive)
            callback: Function to call when keyword is detected
        """
        self.commands[keyword.lower()] = callback

    def process_text(self, text: str) -> bool:
        """Process text input and execute matching command.

        Args:
            text: Input text to process

        Returns:
            True if a command was found and executed, False otherwise
        """
        text_lower = text.lower().strip()

        # Check for exact keyword match
        if text_lower in self.commands:
            self.commands[text_lower]()
            return True

        # Check if any keyword appears in the text
        for keyword, callback in self.commands.items():
            if keyword in text_lower:
                callback()
                return True

        return False
