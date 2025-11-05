#!/usr/bin/env python3
"""Source Manager - arbitrates between music sources with priority and debouncing."""

from typing import Optional, Literal
import time

from core.now_playing import Track, NowPlayingState, get_now_playing_state
from core.logger import get_logger

logger = get_logger('source_manager')


class SourceManager:
    """Manages music source priority and updates NowPlayingState.
    
    Priority order: spotify > sonos > vinyl
    
    Features:
    - Debouncing: Minimum time between track changes
    - Hysteresis: Stick to current source unless new source is significantly better
    - Confidence thresholds: Reject low-confidence matches
    """
    
    # Source priority (lower number = higher priority)
    PRIORITY = {
        "spotify": 1,
        "sonos": 2,
        "vinyl": 3
    }
    
    def __init__(self, config: dict):
        """Initialize source manager.
        
        Args:
            config: Configuration dict
        """
        self.config = config
        self.now_playing = get_now_playing_state()
        
        # Debouncing and hysteresis settings
        self.min_change_interval = config.get('source_manager', {}).get('min_change_interval_seconds', 2.0)
        self.confidence_threshold = config.get('source_manager', {}).get('confidence_threshold', 0.6)
        self.hysteresis_time = config.get('source_manager', {}).get('hysteresis_seconds', 5.0)
        
        # State tracking
        self.last_update_time = 0.0
        self.source_last_seen: dict[str, float] = {}  # Track when each source was last active
    
    def set_from(self, source: Literal["spotify", "sonos", "vinyl"], track: Optional[Track]) -> bool:
        """Update track from a source if it should take priority.
        
        Args:
            source: Source name
            track: Track from this source (or None if source is inactive)
            
        Returns:
            True if NowPlayingState was updated, False otherwise
        """
        current_time = time.time()
        
        # Update last seen time for this source
        if track is not None:
            self.source_last_seen[source] = current_time
        
        # Get current track
        current_track = self.now_playing.get_track()
        
        # If no new track, clear if this was the active source
        if track is None:
            if current_track and current_track.source == source:
                logger.info("Source inactive, clearing track", source=source)
                self.now_playing.clear()
                self.last_update_time = current_time
                return True
            return False
        
        # Validate confidence for ACRCloud (vinyl) sources
        if source == "vinyl" and track.confidence < self.confidence_threshold:
            logger.debug("Rejecting low-confidence vinyl match",
                        confidence=track.confidence,
                        threshold=self.confidence_threshold)
            return False
        
        # Check debouncing - don't change too frequently
        time_since_last_change = current_time - self.last_update_time
        if time_since_last_change < self.min_change_interval:
            logger.debug("Debouncing track change",
                        time_since_last=time_since_last_change,
                        min_interval=self.min_change_interval)
            return False
        
        # If no current track, accept new track
        if current_track is None:
            logger.info("Setting initial track",
                       source=source,
                       title=track.title,
                       artist=track.artist)
            self.now_playing.set_track(track)
            self.last_update_time = current_time
            return True
        
        # Check if it's the same track (just updating)
        if track == current_track:
            # Same track, just update metadata if needed
            if track.image_url and not current_track.image_url:
                logger.debug("Updating track metadata", source=source)
                self.now_playing.set_track(track)
                return True
            return False
        
        # Different track - check priority
        new_priority = self.PRIORITY.get(source, 999)
        current_priority = self.PRIORITY.get(current_track.source, 999)
        
        # Higher priority source always wins
        if new_priority < current_priority:
            logger.info("Source priority switch",
                       from_source=current_track.source,
                       to_source=source,
                       title=track.title,
                       artist=track.artist)
            self.now_playing.set_track(track)
            self.last_update_time = current_time
            return True
        
        # Lower priority source - apply hysteresis
        if new_priority > current_priority:
            # Check if current source is still active
            current_source_last_seen = self.source_last_seen.get(current_track.source, 0)
            time_since_current_seen = current_time - current_source_last_seen
            
            # Only switch if current source has been inactive for hysteresis period
            if time_since_current_seen > self.hysteresis_time:
                logger.info("Source fallback after hysteresis",
                           from_source=current_track.source,
                           to_source=source,
                           inactive_time=time_since_current_seen,
                           title=track.title,
                           artist=track.artist)
                self.now_playing.set_track(track)
                self.last_update_time = current_time
                return True
            else:
                logger.debug("Hysteresis blocking source switch",
                            from_source=current_track.source,
                            to_source=source,
                            time_remaining=self.hysteresis_time - time_since_current_seen)
                return False
        
        # Same priority - accept the change (different track from same source)
        if new_priority == current_priority:
            logger.info("Track change from same source",
                       source=source,
                       title=track.title,
                       artist=track.artist)
            self.now_playing.set_track(track)
            self.last_update_time = current_time
            return True
        
        return False
    
    def get_current_source(self) -> Optional[str]:
        """Get the currently active source.
        
        Returns:
            Source name or None
        """
        track = self.now_playing.get_track()
        return track.source if track else None