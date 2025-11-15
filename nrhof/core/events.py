#!/usr/bin/env python3
"""Centralized event types for the entire application.

All event types are defined here to avoid ad-hoc string events
and ensure type safety across the codebase.
"""

from enum import Enum, auto

__all__ = ["EventType"]


class EventType(Enum):
    """All possible events in the system."""

    # Audio events
    MUSIC_PRESENT = auto()
    MUSIC_ABSENT = auto()
    AUDIO_LEVEL_CHANGED = auto()

    # Recognition events
    TRACK_CONFIRMED = auto()
    TRACK_RECOGNITION_FAILED = auto()
    RECOGNITION_COOLDOWN = auto()
    SONG_RECOGNIZED = auto()

    # Voice events - Wake word
    WAKE_WORD_DETECTED = auto()

    # Voice events - Speech detection (VAD)
    VOICE_SPEECH_START = auto()  # VAD detected speech start
    VOICE_SPEECH_END = auto()  # VAD detected speech end

    # Voice events - Command lifecycle
    VOICE_COMMAND_START = auto()  # User started speaking a command
    VOICE_COMMAND_END = auto()  # User finished speaking
    VOICE_COMMAND_PROCESSING = auto()  # Command being processed by AI
    VOICE_COMMAND_SUCCESS = auto()  # Command successfully executed
    VOICE_COMMAND_FAILED = auto()  # Command failed to execute
    VOICE_COMMAND_CANCELLED = auto()  # Command cancelled by user

    # Voice events - Recognition
    VOICE_SEGMENT_READY = auto()  # Complete speech segment ready for ASR
    VOICE_TRANSCRIPTION_READY = auto()  # Speech-to-text complete
    VOICE_INTENT_RECOGNIZED = auto()  # Intent extracted from transcription
    VOICE_INTENT_RESOLVED = auto()  # Intent resolved by Rhino NLU (deterministic)

    # Voice events - Feedback
    VOICE_LISTENING_START = auto()  # Microphone opened, listening
    VOICE_LISTENING_STOP = auto()  # Microphone closed
    VOICE_TIMEOUT = auto()  # No speech detected within timeout
    VOICE_ERROR = auto()  # Voice system error

    # Input events
    TOUCH_EVENT = auto()  # Touch/pen input from UPDD

    # Scene events
    SCENE_CHANGED = auto()

    # Mixer events
    MIXER_DUCK = auto()  # Duck audio for voice interaction
    MIXER_UNDUCK = auto()  # Restore audio after voice interaction

    # System events
    SHUTDOWN = auto()
    LANGUAGE_CHANGED = auto()
