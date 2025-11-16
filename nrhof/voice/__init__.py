#!/usr/bin/env python3
"""Voice processing modules.

Contains:
- VAD (Voice Activity Detection)
- Cobra (Picovoice VAD)
- Wake word (Porcupine)
- ASR (Automatic Speech Recognition) stub
- NLU (Natural Language Understanding) stub
- Rhino (Picovoice NLU for intent recognition)
- TTS (Text-to-Speech) stub
- AEC (Acoustic Echo Cancellation) stub
- Koala (Noise Suppression)
- Front-end (AEC → Koala pipeline)
"""

from nrhof.core.voice_constants import (
    KOALA_FRAME_SIZE,
    VOICE_FRAME_DURATION_MS,
    VOICE_FRAME_SIZE,
    VOICE_SAMPLE_RATE,
    frame_duration_ms,
    samples_from_ms,
)

from .aec import AEC
from .asr import ASR
from .cobra import Cobra, create_cobra
from .front_end import cleanup_voice_pipeline, create_voice_pipeline
from .koala import Koala, KoalaFrameAdapter, create_koala
from .nlu import GrammarNLU
from .rhino import RhinoNLU, create_rhino
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
    "RhinoNLU",
    "create_rhino",
    "TTS",
    "AEC",
    "Koala",
    "KoalaFrameAdapter",
    "create_koala",
    "create_voice_pipeline",
    "cleanup_voice_pipeline",
    # Constants
    "VOICE_SAMPLE_RATE",
    "VOICE_FRAME_SIZE",
    "VOICE_FRAME_DURATION_MS",
    "KOALA_FRAME_SIZE",
    "frame_duration_ms",
    "samples_from_ms",
]
