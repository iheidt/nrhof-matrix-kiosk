#!/usr/bin/env python3
"""ACRCloud song recognition integration."""

import time
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass
from acrcloud.recognizer import ACRCloudRecognizer
from core.logger import get_logger

logger = get_logger('song_recognition')


@dataclass
class SongInfo:
    """Information about a recognized song."""
    title: str
    artist: str
    album: Optional[str] = None
    release_date: Optional[str] = None
    duration_ms: Optional[int] = None
    score: int = 0  # Recognition confidence score (0-100)
    acrid: Optional[str] = None  # ACRCloud track ID
    
    def __str__(self):
        return f"{self.artist} - {self.title}"


class SongRecognizer:
    """Handles ambient song recognition using ACRCloud."""
    
    def __init__(self, config: dict):
        """Initialize song recognizer.
        
        Args:
            config: Configuration dict with ACRCloud credentials
        """
        self.config = config
        self.enabled = config.get('song_recognition', {}).get('enabled', False)
        
        if not self.enabled:
            logger.info("Song recognition disabled in config")
            return
        
        # Get ACRCloud credentials
        acr_config = config.get('song_recognition', {})
        self.host = acr_config.get('host')
        self.access_key = acr_config.get('access_key')
        self.access_secret = acr_config.get('access_secret')
        self.timeout = acr_config.get('timeout', 10)
        
        # Validation
        if not all([self.host, self.access_key, self.access_secret]):
            logger.warning("ACRCloud credentials not configured. Song recognition disabled.")
            self.enabled = False
            return
        
        # Initialize recognizer
        try:
            self.recognizer = ACRCloudRecognizer({
                'host': self.host,
                'access_key': self.access_key,
                'access_secret': self.access_secret,
                'timeout': self.timeout
            })
            logger.info("ACRCloud recognizer initialized", host=self.host)
        except Exception as e:
            logger.error("Failed to initialize ACRCloud recognizer", error=str(e))
            self.enabled = False
        
        # Rate limiting
        self.min_interval = acr_config.get('min_interval_seconds', 30)
        self.last_recognition_time = 0
        self.last_recognized_song: Optional[SongInfo] = None
    
    def can_recognize(self) -> bool:
        """Check if enough time has passed since last recognition.
        
        Returns:
            True if recognition can proceed
        """
        if not self.enabled:
            return False
        
        elapsed = time.time() - self.last_recognition_time
        return elapsed >= self.min_interval
    
    def recognize_from_audio(self, audio_data: bytes, sample_rate: int = 44100) -> Optional[SongInfo]:
        """Recognize song from audio data.
        
        Args:
            audio_data: Raw audio bytes (PCM)
            sample_rate: Sample rate in Hz
            
        Returns:
            SongInfo if recognized, None otherwise
        """
        if not self.can_recognize():
            return None
        
        try:
            # ACRCloud expects audio data
            result = self.recognizer.recognize_by_filebuffer(audio_data, 0)
            
            # Update last recognition time
            self.last_recognition_time = time.time()
            
            # Parse result
            song_info = self._parse_result(result)
            
            if song_info:
                self.last_recognized_song = song_info
                logger.info("Song recognized", 
                           title=song_info.title,
                           artist=song_info.artist,
                           score=song_info.score)
            
            return song_info
            
        except Exception as e:
            logger.error("Song recognition failed", error=str(e))
            return None
    
    def _parse_result(self, result: dict) -> Optional[SongInfo]:
        """Parse ACRCloud result into SongInfo.
        
        Args:
            result: ACRCloud API response
            
        Returns:
            SongInfo if song found, None otherwise
        """
        try:
            # Check status
            status = result.get('status', {})
            if status.get('code') != 0:
                logger.debug("No song recognized", msg=status.get('msg'))
                return None
            
            # Extract metadata
            metadata = result.get('metadata', {})
            music_list = metadata.get('music', [])
            
            if not music_list:
                return None
            
            # Get first (best) match
            music = music_list[0]
            
            # Extract song info
            title = music.get('title', 'Unknown')
            artists = music.get('artists', [])
            artist = artists[0].get('name', 'Unknown') if artists else 'Unknown'
            album = music.get('album', {}).get('name')
            release_date = music.get('release_date')
            duration_ms = music.get('duration_ms')
            score = music.get('score', 0)
            acrid = music.get('acrid')
            
            return SongInfo(
                title=title,
                artist=artist,
                album=album,
                release_date=release_date,
                duration_ms=duration_ms,
                score=score,
                acrid=acrid
            )
            
        except Exception as e:
            logger.error("Failed to parse ACRCloud result", error=str(e))
            return None
    
    def get_last_recognized(self) -> Optional[SongInfo]:
        """Get the last successfully recognized song.
        
        Returns:
            Last SongInfo or None
        """
        return self.last_recognized_song