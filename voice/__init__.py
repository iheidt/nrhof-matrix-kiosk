#!/usr/bin/env python3
"""Voice processing modules.

Contains:
- VAD (Voice Activity Detection)
- Wake word utilities
"""

from .vad import VAD, create_vad

__all__ = ["VAD", "create_vad"]
