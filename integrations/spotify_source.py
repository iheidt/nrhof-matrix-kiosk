#!/usr/bin/env python3
"""Spotify integration for Now Playing metadata and control."""

import threading
import time
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from core.now_playing import Track
from core.source_manager import SourceManager
from core.logger import get_logger

logger = get_logger('spotify_source')


class SpotifySource:
    """Polls Spotify for currently playing track and updates SourceManager."""
    
    def __init__(self, config: dict, source_manager: SourceManager):
        """Initialize Spotify source.
        
        Args:
            config: Configuration dict
            source_manager: SourceManager instance
        """
        self.config = config
        self.source_manager = source_manager
        self.enabled = config.get('spotify', {}).get('enabled', False)
        
        # Initialize state
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.sp: Optional[spotipy.Spotify] = None
        
        # Polling settings
        self.poll_interval = config.get('spotify', {}).get('poll_interval_seconds', 2.0)
        
        if not self.enabled:
            logger.info("Spotify integration disabled in config")
            return
        
        # Initialize Spotify client
        try:
            self._init_spotify()
            logger.info("Spotify client initialized")
        except Exception as e:
            logger.error("Failed to initialize Spotify client", error=str(e))
            self.enabled = False
    
    def _init_spotify(self):
        """Initialize Spotify client with OAuth."""
        spotify_config = self.config.get('spotify', {})
        
        # Required scopes for reading playback state
        scope = "user-read-playback-state user-read-currently-playing"
        
        auth_manager = SpotifyOAuth(
            client_id=spotify_config.get('client_id'),
            client_secret=spotify_config.get('client_secret'),
            redirect_uri=spotify_config.get('redirect_uri', 'http://localhost:8888/callback'),
            scope=scope,
            cache_path=spotify_config.get('cache_path', '.spotify_cache')
        )
        
        self.sp = spotipy.Spotify(auth_manager=auth_manager)
    
    def start(self):
        """Start polling Spotify."""
        if not self.enabled:
            logger.info("Spotify source not started (disabled)")
            return
        
        if self.running:
            logger.warning("Spotify source already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info("Spotify polling started")
    
    def stop(self):
        """Stop polling Spotify."""
        if not self.running:
            return
        
        logger.info("Stopping Spotify source...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5.0)
        
        logger.info("Spotify source stopped")
    
    def _poll_loop(self):
        """Main polling loop."""
        logger.info("Spotify poll loop started")
        
        while self.running:
            try:
                # Get current playback
                playback = self.sp.current_playback()
                
                if playback and playback.get('is_playing'):
                    track = self._parse_playback(playback)
                    if track:
                        self.source_manager.set_from('spotify', track)
                else:
                    # Nothing playing
                    self.source_manager.set_from('spotify', None)
                
            except Exception as e:
                import traceback
                logger.error("Error polling Spotify", 
                           error=str(e), 
                           error_type=type(e).__name__,
                           traceback=traceback.format_exc())
            
            # Sleep
            time.sleep(self.poll_interval)
        
        logger.info("Spotify poll loop ended")
    
    def _parse_playback(self, playback: dict) -> Optional[Track]:
        """Parse Spotify playback response into Track.
        
        Args:
            playback: Spotify playback response
            
        Returns:
            Track or None
        """
        try:
            item = playback.get('item')
            if not item:
                return None
            
            # Extract track info
            title = item.get('name', 'Unknown')
            artists = item.get('artists', [])
            artist = artists[0].get('name', 'Unknown') if artists else 'Unknown'
            album_info = item.get('album', {})
            album = album_info.get('name')
            
            # Get album art (prefer largest image)
            images = album_info.get('images', [])
            image_url = images[0].get('url') if images else None
            
            # Spotify ID and duration
            spotify_id = item.get('id')
            duration_ms = item.get('duration_ms')
            
            return Track(
                title=title,
                artist=artist,
                album=album,
                confidence=1.0,  # Spotify metadata is always confident
                source='spotify',
                image_url=image_url,
                spotify_id=spotify_id,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error("Failed to parse Spotify playback", error=str(e))
            return None
    
    def get_current_track(self) -> Optional[Track]:
        """Get current track synchronously (for testing/debugging).
        
        Returns:
            Current track or None
        """
        if not self.enabled or not self.sp:
            return None
        
        try:
            playback = self.sp.current_playback()
            if playback and playback.get('is_playing'):
                return self._parse_playback(playback)
        except Exception as e:
            logger.error("Error getting current track", error=str(e))
        
        return None