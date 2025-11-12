"""Typed event payload definitions."""

from typing import Literal, TypedDict


class NowPlayingPayload(TypedDict, total=False):
    """Payload for now playing events."""

    track: str
    artist: str
    album: str
    duration_ms: int
    progress_ms: int
    source: Literal["spotify", "sonos", "unknown"]
    is_playing: bool


class LanguageChangedPayload(TypedDict):
    """Payload for language change events."""

    old: str
    new: str


class SceneChangedPayload(TypedDict):
    """Payload for scene change events."""

    from_scene: str
    to_scene: str
    use_transition: bool


__all__ = ["NowPlayingPayload", "LanguageChangedPayload", "SceneChangedPayload"]
