#!/usr/bin/env python3
"""Now Playing data models and state management."""

from dataclasses import dataclass
from typing import Optional, Literal, Callable, List
import time


@dataclass
class Track:
    """Represents a music track from any source."""
    # Basic track info
    title: str
    artist: str
    album: Optional[str] = None
    confidence: float = 1.0  # 0.0-1.0, used for ACRCloud matches
    source: Literal["spotify", "sonos", "vinyl"] = "spotify"
    spotify_id: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # Content type
    content_type: Literal["music", "podcast", "audiobook"] = "music"
    show_name: Optional[str] = None  # For podcasts
    publisher: Optional[str] = None  # For podcasts/audiobooks
    
    # Album art (multiple sizes)
    image_url: Optional[str] = None  # Default/large image
    image_large: Optional[str] = None  # 640x640
    image_medium: Optional[str] = None  # 300x300
    image_small: Optional[str] = None  # 64x64
    release_date: Optional[str] = None
    
    # Playback state
    is_playing: bool = True
    progress_ms: Optional[int] = None
    
    # Device info
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    device_volume: Optional[int] = None
    
    # Context (what's playing from)
    context_type: Optional[str] = None  # "playlist", "album", "artist", "show"
    context_uri: Optional[str] = None
    
    def __eq__(self, other) -> bool:
        """Check if two tracks are the same (ignoring confidence)."""
        if not isinstance(other, Track):
            return False
        return (
            self.title == other.title and
            self.artist == other.artist and
            self.album == other.album and
            self.source == other.source
        )
    
    def __hash__(self) -> int:
        """Hash for deduplication."""
        return hash((self.title, self.artist, self.album, self.source))


class NowPlayingState:
    """Manages current track state and notifies listeners."""
    
    def __init__(self):
        self.track: Optional[Track] = None
        self.last_change_ts: float = 0.0
        self.listeners: List[Callable[[Optional[Track]], None]] = []
    
    def set_track(self, track: Optional[Track]) -> bool:
        """Update current track if it's different.
        
        Args:
            track: New track or None
            
        Returns:
            True if track changed, False otherwise
        """
        if track == self.track:
            return False
        
        self.track = track
        self.last_change_ts = time.time()
        self._notify_listeners()
        return True
    
    def get_track(self) -> Optional[Track]:
        """Get current track."""
        return self.track
    
    def clear(self):
        """Clear current track."""
        self.set_track(None)
    
    def add_listener(self, callback: Callable[[Optional[Track]], None]):
        """Add a listener for track changes.
        
        Args:
            callback: Function called with new track when it changes
        """
        if callback not in self.listeners:
            self.listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[Optional[Track]], None]):
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
_now_playing_state: Optional[NowPlayingState] = None


def get_now_playing_state() -> NowPlayingState:
    """Get the global NowPlayingState singleton."""
    global _now_playing_state
    if _now_playing_state is None:
        _now_playing_state = NowPlayingState()
    return _now_playing_state