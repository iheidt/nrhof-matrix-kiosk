#!/usr/bin/env python3
"""Voice processing modules.

Contains:
- VAD (Voice Activity Detection)
- Cobra (Picovoice VAD)
- Wake word (Porcupine)
- ASR (Automatic Speech Recognition) stub
- NLU (Natural Language Understanding) stub
- TTS (Text-to-Speech) stub
- AEC (Acoustic Echo Cancellation) stub
- Koala (Noise Suppression)
- Front-end (AEC → Koala pipeline)
"""

from .aec import AEC
from .asr import ASR
from .cobra import Cobra, create_cobra
from .front_end import cleanup_voice_pipeline, create_voice_pipeline
from .koala import Koala, create_koala
from .nlu import GrammarNLU
from .tts import TTS
from .vad import VAD, create_vad
from .wake import Porcupine, create_porcupine

__all__ = [
    "VAD",
    "create_vad",
    "Cobra",
    "create_cobra",
    "Porcupine",
    "create_porcupine",
    "ASR",
    "GrammarNLU",
    "TTS",
    "AEC",
    "Koala",
    "create_koala",
    "create_voice_pipeline",
    "cleanup_voice_pipeline",
]
