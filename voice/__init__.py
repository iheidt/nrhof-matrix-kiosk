#!/usr/bin/env python3
"""Voice processing modules.

Contains:
- VAD (Voice Activity Detection)
- Wake word utilities
- ASR (Automatic Speech Recognition) stub
- NLU (Natural Language Understanding) stub
- TTS (Text-to-Speech) stub
- AEC (Acoustic Echo Cancellation) stub
"""

from .aec import AEC
from .asr import ASR
from .nlu import GrammarNLU
from .tts import TTS
from .vad import VAD, create_vad

__all__ = ["VAD", "create_vad", "ASR", "GrammarNLU", "TTS", "AEC"]
