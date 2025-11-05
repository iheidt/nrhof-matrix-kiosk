#!/usr/bin/env python3
"""Sonos integration using local network discovery."""

import threading
import time
from typing import Optional
import soco
from soco.discovery import discover

from core.now_playing import Track
from core.source_manager import SourceManager
from core.logger import get_logger

logger = get_logger('sonos_source')


class SonosSource:
    """Polls Sonos speakers for currently playing track and updates SourceManager."""
    
    def __init__(self, config: dict, source_manager: SourceManager):
        """Initialize Sonos source.
        
        Args:
            config: Configuration dict
            source_manager: SourceManager instance
        """
        self.config = config
        self.source_manager = source_manager
        self.enabled = config.get('sonos', {}).get('enabled', False)
        
        # Initialize state
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.speaker: Optional[soco.SoCo] = None
        
        # Polling settings
        self.poll_interval = config.get('sonos', {}).get('poll_interval_seconds', 2.0)
        self.target_room = config.get('sonos', {}).get('target_room')  # Optional: specific room
        
        if not self.enabled:
            logger.info("Sonos integration disabled in config")
            return
        
        # Discover Sonos speakers
        try:
            self._discover_speaker()
            if self.speaker:
                logger.info("Sonos speaker discovered", room=self.speaker.player_name)
            else:
                logger.warning("No Sonos speakers found on network")
                self.enabled = False
        except Exception as e:
            logger.error("Failed to discover Sonos speakers", error=str(e))
            self.enabled = False
    
    def _discover_speaker(self):
        """Discover Sonos speakers on local network."""
        logger.info("Discovering Sonos speakers...")
        try:
            speakers = discover(timeout=10)
        except Exception as e:
            logger.error("Sonos discovery failed", error=str(e))
            return
        
        if not speakers:
            return
        
        # Log all discovered speakers
        room_names = [s.player_name for s in speakers]
        logger.info("Sonos speakers found", count=len(speakers), rooms=room_names)
        
        # If target room specified, find it
        if self.target_room:
            for speaker in speakers:
                if speaker.player_name.lower() == self.target_room.lower():
                    self.speaker = speaker
                    logger.info("Using target Sonos room", room=speaker.player_name)
                    return
            logger.warning("Target room not found", target=self.target_room)
        
        # Find first actively playing speaker
        for speaker in speakers:
            try:
                transport_info = speaker.get_current_transport_info()
                if transport_info.get('current_transport_state') == 'PLAYING':
                    self.speaker = speaker
                    logger.info("Using actively playing Sonos speaker", room=speaker.player_name)
                    return
            except:
                continue
        
        # Fallback to coordinator
        for speaker in speakers:
            if speaker.is_coordinator:
                self.speaker = speaker
                logger.info("No active Sonos playback, using coordinator", room=speaker.player_name)
                return
        
        # Final fallback to any speaker
        self.speaker = list(speakers)[0]
        logger.info("Using first Sonos speaker", room=self.speaker.player_name)
    
    def start(self):
        """Start polling Sonos."""
        if not self.enabled:
            logger.info("Sonos source not started (disabled)")
            return
        
        if self.running:
            logger.warning("Sonos source already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True, name="SonosSource")
        self.thread.start()
        logger.info("Sonos polling started")
    
    def stop(self):
        """Stop polling Sonos."""
        if not self.running:
            return
        
        logger.info("Stopping Sonos source...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5.0)
        
        logger.info("Sonos source stopped")
    
    def _poll_loop(self):
        """Main polling loop."""
        logger.info("Sonos poll loop started")
        
        while self.running:
            try:
                # If target room is set, stick to that speaker
                if self.target_room:
                    # Get current playback from target speaker
                    track_info = self.speaker.get_current_track_info()
                    transport_info = self.speaker.get_current_transport_info()
                    
                    transport_state = transport_info.get('current_transport_state')
                    is_playing = transport_state == 'PLAYING'
                    
                    if is_playing and track_info:
                        track = self._parse_track_info(track_info)
                        if track:
                            self.source_manager.set_from('sonos', track)
                    else:
                        self.source_manager.set_from('sonos', None)
                else:
                    # Dynamic mode: find any actively playing speaker
                    active_track = None
                    speakers = discover(timeout=2)
                    
                    if speakers:
                        for speaker in speakers:
                            try:
                                transport_info = speaker.get_current_transport_info()
                                if transport_info.get('current_transport_state') == 'PLAYING':
                                    track_info = speaker.get_current_track_info()
                                    if track_info:
                                        # Temporarily set speaker for parsing
                                        old_speaker = self.speaker
                                        self.speaker = speaker
                                        active_track = self._parse_track_info(track_info)
                                        self.speaker = old_speaker
                                        
                                        if active_track:
                                            break
                            except:
                                continue
                    
                    if active_track:
                        self.source_manager.set_from('sonos', active_track)
                    else:
                        self.source_manager.set_from('sonos', None)
                
            except Exception as e:
                logger.error("Error polling Sonos", error=str(e))
            
            # Sleep until next poll
            time.sleep(self.poll_interval)
        
        logger.info("Sonos poll loop ended")
    
    def _parse_track_info(self, track_info: dict) -> Optional[Track]:
        """Parse Sonos track info into Track.
        
        Args:
            track_info: Sonos track info dict
            
        Returns:
            Track or None
        """
        try:
            title = track_info.get('title', 'Unknown')
            artist = track_info.get('artist', 'Unknown')
            album = track_info.get('album')
            duration = track_info.get('duration')  # Format: "0:03:45"
            
            # Convert duration to milliseconds
            duration_ms = None
            if duration:
                try:
                    parts = duration.split(':')
                    if len(parts) == 3:
                        h, m, s = parts
                        duration_ms = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000
                except:
                    pass
            
            # Get album art URL
            album_art = track_info.get('album_art')
            if album_art and not album_art.startswith('http'):
                # Make it absolute URL
                album_art = f"http://{self.speaker.ip_address}:1400{album_art}"
            
            # Get room info
            room_name = self.speaker.player_name
            volume = self.speaker.volume
            
            # Get grouped rooms
            grouped_rooms = []
            try:
                group = self.speaker.group
                if group:
                    grouped_rooms = [member.player_name for member in group.members 
                                   if member.player_name != room_name]
            except:
                pass
            
            return Track(
                title=title,
                artist=artist,
                album=album,
                confidence=1.0,
                source='sonos',
                duration_ms=duration_ms,
                image_url=album_art,
                sonos_room=room_name,
                sonos_volume=volume,
                sonos_grouped_rooms=grouped_rooms if grouped_rooms else None
            )
            
        except Exception as e:
            logger.error("Failed to parse Sonos track info", error=str(e))
            return None