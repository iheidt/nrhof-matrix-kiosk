#!/usr/bin/env python3
"""
Application State - Thread-safe shared state for multi-threaded architecture.

State is read by render loop and written by workers.
"""
import threading
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum, auto


class SceneProfile(Enum):
    """Scene rendering profiles."""
    IDLE = auto()           # No music, low activity
    VISUALIZER = auto()     # Music playing, visualizing
    RECOGNITION = auto()    # Actively recognizing track
    VIDEO = auto()          # Playing music video
    ERROR = auto()          # Error state


@dataclass
class TrackInfo:
    """Information about a recognized track."""
    title: str
    artist: str
    album: Optional[str] = None
    track_key: str = ""     # Deterministic key for deduplication
    confidence: float = 0.0
    recognized_at: float = 0.0
    
    def __post_init__(self):
        if not self.track_key:
            self.track_key = f"{self.artist}:{self.title}".lower().replace(" ", "_")
        if self.recognized_at == 0:
            self.recognized_at = time.time()


@dataclass
class NetworkState:
    """Network connectivity state."""
    is_online: bool = True
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    retry_after: float = 0.0  # Exponential backoff timestamp


@dataclass
class RateLimits:
    """Rate limiting state."""
    last_recognition_attempt: float = 0.0
    recognition_cooldown: float = 5.0  # Seconds between attempts
    last_webflow_sync: Dict[str, float] = field(default_factory=dict)  # track_key -> timestamp
    webflow_sync_window: float = 300.0  # Don't sync same track within 5 minutes


class AppState:
    """Thread-safe application state."""
    
    def __init__(self):
        """Initialize application state."""
        self._lock = threading.RLock()  # Reentrant lock
        
        # Audio state
        self.music_present: bool = False
        self.audio_level: float = 0.0
        self.last_audio_update: float = time.time()
        
        # Track state
        self.current_track: Optional[TrackInfo] = None
        self.last_track: Optional[TrackInfo] = None
        self.track_changed_at: float = 0.0
        
        # Scene state
        self.scene_profile: SceneProfile = SceneProfile.IDLE
        self.current_scene_name: str = "SplashScene"
        self.scene_changed_at: float = time.time()
        
        # Recognition state
        self.last_recog_ts: float = 0.0
        self.recognition_in_progress: bool = False
        
        # Network state
        self.network: NetworkState = NetworkState()
        
        # Rate limits
        self.rate_limits: RateLimits = RateLimits()
        
        # Offline mode
        self.offline_mode: bool = False
        self.pending_syncs: list[TrackInfo] = []
        
        # Performance metrics
        self.fps: float = 60.0
        self.avg_render_time: float = 0.0
        self.recognition_attempts: int = 0
        self.recognition_successes: int = 0
        self.network_failures: int = 0
    
    # Audio state methods
    def set_music_present(self, present: bool, level: float = 0.0):
        """Set music presence state.
        
        Args:
            present: Whether music is present
            level: Audio level (0.0-1.0)
        """
        with self._lock:
            self.music_present = present
            self.audio_level = level
            self.last_audio_update = time.time()
    
    def get_music_state(self) -> tuple[bool, float]:
        """Get music presence and level.
        
        Returns:
            (music_present, audio_level)
        """
        with self._lock:
            return self.music_present, self.audio_level
    
    # Track state methods
    def set_current_track(self, track: Optional[TrackInfo]):
        """Set current track.
        
        Args:
            track: Track info or None
        """
        with self._lock:
            if track != self.current_track:
                self.last_track = self.current_track
                self.current_track = track
                self.track_changed_at = time.time()
    
    def get_current_track(self) -> Optional[TrackInfo]:
        """Get current track.
        
        Returns:
            Current track info or None
        """
        with self._lock:
            return self.current_track
    
    def is_same_track(self, track: TrackInfo) -> bool:
        """Check if track is same as current.
        
        Args:
            track: Track to compare
            
        Returns:
            True if same track
        """
        with self._lock:
            if not self.current_track:
                return False
            return self.current_track.track_key == track.track_key
    
    # Scene state methods
    def set_scene_profile(self, profile: SceneProfile):
        """Set scene rendering profile.
        
        Args:
            profile: Scene profile
        """
        with self._lock:
            if profile != self.scene_profile:
                self.scene_profile = profile
                self.scene_changed_at = time.time()
    
    def get_scene_profile(self) -> SceneProfile:
        """Get current scene profile.
        
        Returns:
            Current scene profile
        """
        with self._lock:
            return self.scene_profile
    
    # Recognition state methods
    def can_attempt_recognition(self) -> bool:
        """Check if recognition attempt is allowed (rate limiting).
        
        Returns:
            True if recognition can be attempted
        """
        with self._lock:
            if self.recognition_in_progress:
                return False
            
            elapsed = time.time() - self.rate_limits.last_recognition_attempt
            return elapsed >= self.rate_limits.recognition_cooldown
    
    def start_recognition(self):
        """Mark recognition as in progress."""
        with self._lock:
            self.recognition_in_progress = True
            self.rate_limits.last_recognition_attempt = time.time()
            self.recognition_attempts += 1
    
    def end_recognition(self, success: bool = False):
        """Mark recognition as complete.
        
        Args:
            success: Whether recognition succeeded
        """
        with self._lock:
            self.recognition_in_progress = False
            self.last_recog_ts = time.time()
            if success:
                self.recognition_successes += 1
    
    # Network state methods
    def set_network_state(self, online: bool):
        """Set network connectivity state.
        
        Args:
            online: Whether network is online
        """
        with self._lock:
            self.network.is_online = online
            if online:
                self.network.last_success = time.time()
                self.network.consecutive_failures = 0
                self.network.retry_after = 0.0
            else:
                self.network.last_failure = time.time()
                self.network.consecutive_failures += 1
                self.network_failures += 1
                
                # Exponential backoff: 2^failures seconds, max 5 minutes
                backoff = min(2 ** self.network.consecutive_failures, 300)
                self.network.retry_after = time.time() + backoff
    
    def can_attempt_network(self) -> bool:
        """Check if network operation is allowed.
        
        Returns:
            True if network operation can be attempted
        """
        with self._lock:
            if self.offline_mode:
                return False
            if not self.network.is_online:
                return time.time() >= self.network.retry_after
            return True
    
    # Webflow sync methods
    def can_sync_track(self, track_key: str) -> bool:
        """Check if track can be synced to Webflow (deduplication).
        
        Args:
            track_key: Track key
            
        Returns:
            True if track can be synced
        """
        with self._lock:
            last_sync = self.rate_limits.last_webflow_sync.get(track_key, 0.0)
            elapsed = time.time() - last_sync
            return elapsed >= self.rate_limits.webflow_sync_window
    
    def mark_track_synced(self, track_key: str):
        """Mark track as synced to Webflow.
        
        Args:
            track_key: Track key
        """
        with self._lock:
            self.rate_limits.last_webflow_sync[track_key] = time.time()
    
    # Offline queue methods
    def queue_for_sync(self, track: TrackInfo):
        """Queue track for later sync when offline.
        
        Args:
            track: Track to queue
        """
        with self._lock:
            if track not in self.pending_syncs:
                self.pending_syncs.append(track)
    
    def get_pending_syncs(self) -> list[TrackInfo]:
        """Get and clear pending syncs.
        
        Returns:
            List of tracks to sync
        """
        with self._lock:
            syncs = self.pending_syncs.copy()
            self.pending_syncs.clear()
            return syncs
    
    # Metrics methods
    def update_fps(self, fps: float):
        """Update FPS metric.
        
        Args:
            fps: Current FPS
        """
        with self._lock:
            # Exponential moving average
            self.fps = 0.9 * self.fps + 0.1 * fps
    
    def update_render_time(self, render_time: float):
        """Update average render time.
        
        Args:
            render_time: Render time in seconds
        """
        with self._lock:
            # Exponential moving average
            self.avg_render_time = 0.9 * self.avg_render_time + 0.1 * render_time
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            return {
                'fps': round(self.fps, 1),
                'avg_render_time_ms': round(self.avg_render_time * 1000, 2),
                'recognition_attempts': self.recognition_attempts,
                'recognition_successes': self.recognition_successes,
                'recognition_rate': (
                    self.recognition_successes / self.recognition_attempts
                    if self.recognition_attempts > 0 else 0.0
                ),
                'network_failures': self.network_failures,
                'network_online': self.network.is_online,
                'pending_syncs': len(self.pending_syncs),
                'offline_mode': self.offline_mode
            }


# Global state instance
_app_state: Optional[AppState] = None


def get_app_state() -> AppState:
    """Get global application state.
    
    Returns:
        Global AppState instance
    """
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state