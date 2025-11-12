"""Overlays package for NRHOF.

Provides global overlay components that render on top of scenes.
"""

from .now_playing_overlay import draw_now_playing_overlay

__all__ = ["draw_now_playing_overlay"]
