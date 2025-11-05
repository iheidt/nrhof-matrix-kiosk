#!/usr/bin/env python3
"""Test script for voice router functionality."""

from routing.voice_router import VoiceRouter


def test_voice_router():
    """Test the voice router with mock callbacks."""
    
    # Create voice router
    router = VoiceRouter()
    
    # Track which commands were called
    called_commands = []
    
    # Register test commands
    router.register_command("menu", lambda: called_commands.append("menu"))
    router.register_command("home", lambda: called_commands.append("home"))
    router.register_command("one", lambda: called_commands.append("one"))
    router.register_command("two", lambda: called_commands.append("two"))
    router.register_command("three", lambda: called_commands.append("three"))
    
    # Test commands
    print("Testing voice router...\n")
    
    test_cases = [
        ("one", "one"),
        ("two", "two"),
        ("three", "three"),
        ("menu", "menu"),
        ("home", "home"),
        ("ONE", "one"),  # Case insensitive
        ("Menu", "menu"),  # Case insensitive
        ("go to menu", "menu"),  # Substring match
        ("select one", "one"),  # Substring match
        ("invalid", None),  # No match
    ]
    
    for text, expected in test_cases:
        called_commands.clear()
        result = router.process_text(text)
        actual = called_commands[0] if called_commands else None
        status = "✓" if actual == expected else "✗"
        print(f"{status} process_text('{text}') -> {actual} (expected: {expected})")
    
    print("\nVoice router test complete!")


if __name__ == "__main__":
    test_voice_router()
