#!/usr/bin/env python3
"""Voice command registration for the application."""

from routing.intent_router import Intent, IntentRouter
from routing.voice_router import VoiceRouter


def register_all_voice_commands(voice_router: VoiceRouter, intent_router: IntentRouter):
    """Register all voice commands.

    Args:
        voice_router: VoiceRouter instance
        intent_router: IntentRouter instance
    """
    # Navigation commands - all emit go_home intent
    for cmd in ["menu", "home", "main"]:
        voice_router.register_command(cmd, lambda: intent_router.emit(Intent.GO_HOME))

    # Option selection with variants
    options = [
        (["one", "1", "first"], 0),
        (["two", "2", "second"], 1),
        (["three", "3", "third"], 2),
    ]
    for variants, index in options:
        for variant in variants:
            voice_router.register_command(
                variant,
                lambda idx=index: intent_router.emit(Intent.SELECT_OPTION, index=idx),
            )
