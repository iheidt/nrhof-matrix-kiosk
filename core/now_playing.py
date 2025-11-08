#!/usr/bin/env python3
"""Now Playing data models and state management."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


@dataclass
class Track:
    """Represents a music track from any source."""

    # Basic track info
    title: str
    artist: str
    album: str | None = None
    confidence: float = 1.0  # 0.0-1.0, used for ACRCloud matches
    source: Literal["spotify", "sonos", "vinyl"] = "spotify"
    spotify_id: str | None = None
    duration_ms: int | None = None

    # Content type
    content_type: Literal["music", "podcast", "audiobook"] = "music"
    show_name: str | None = None  # For podcasts
    publisher: str | None = None  # For podcasts/audiobooks

    # Album art (multiple sizes)
    image_url: str | None = None  # Default/large image
    image_large: str | None = None  # 640x640
    image_medium: str | None = None  # 300x300
    image_small: str | None = None  # 64x64
    release_date: str | None = None

    # Playback state
    is_playing: bool = True
    progress_ms: int | None = None

    # Device info
    device_name: str | None = None
    device_type: str | None = None
    device_volume: int | None = None

    # Context (what's playing from)
    context_type: str | None = None  # "playlist", "album", "artist", "show"
    context_uri: str | None = None

    # Sonos-specific info
    sonos_room: str | None = None  # Room name (e.g., "Living Room")
    sonos_volume: int | None = None  # Volume level 0-100
    sonos_grouped_rooms: list[str] | None = None  # Other rooms in group

    def __eq__(self, other) -> bool:
        """Check if two tracks are the same (ignoring confidence)."""
        if not isinstance(other, Track):
            return False
        return (
            self.title == other.title
            and self.artist == other.artist
            and self.album == other.album
            and self.source == other.source
        )

    def __hash__(self) -> int:
        """Hash for deduplication."""
        return hash((self.title, self.artist, self.album, self.source))


class NowPlayingState:
    """Manages current track state and notifies listeners."""

    def __init__(self):
        self.track: Track | None = None
        self.last_change_ts: float = 0.0
        self.listeners: list[Callable[[Track | None], None]] = []

    def set_track(self, track: Track | None) -> bool:
        """Update current track.

        Args:
            track: New track or None

        Returns:
            True if track changed (by title/artist), False if just updated
        """
        # Check if it's a different track (by title/artist)
        is_different_track = track != self.track

        # Always update to capture progress_ms and other field changes
        self.track = track

        # Only update timestamp and notify if it's actually a different track
        if is_different_track:
            self.last_change_ts = time.time()
            self._notify_listeners()
            return True

        return False

    def get_track(self) -> Track | None:
        """Get current track."""
        return self.track

    def clear(self):
        """Clear current track."""
        self.set_track(None)

    def add_listener(self, callback: Callable[[Track | None], None]):
        """Add a listener for track changes.

        Args:
            callback: Function called with new track when it changes
        """
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback: Callable[[Track | None], None]):
        """Remove a listener.

        Args:
            callback: Function to remove
        """
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _notify_listeners(self):
        """Notify all listeners of track change."""
        for listener in self.listeners:
            try:
                listener(self.track)
            except Exception as e:
                # Don't let listener errors break the state
                print(f"Error in NowPlaying listener: {e}")


# Global singleton
_now_playing_state: NowPlayingState | None = None


def get_now_playing_state() -> NowPlayingState:
    """Get the global NowPlayingState singleton."""
    global _now_playing_state
    if _now_playing_state is None:
        _now_playing_state = NowPlayingState()
    return _now_playing_state
