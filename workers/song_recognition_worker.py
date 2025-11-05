#!/usr/bin/env python3
"""Song recognition worker - passive ambient music detection."""

import threading
import time
import io
import wave
import numpy as np
from typing import Optional

from audio_source import get_audio_frame, get_sample_rate
from core.logger import get_logger
from core.event_bus import get_event_bus, EventType
from core.song_recognition import SongRecognizer, SongInfo
from core.app_state import get_app_state

logger = get_logger('song_recognition_worker')


class SongRecognitionWorker:
    """Continuously monitors ambient audio for song recognition."""
    
    def __init__(self, config: dict):
        """Initialize song recognition worker.
        
        Args:
            config: Configuration dict
        """
        self.config = config
        self.recognizer = SongRecognizer(config)
        self.enabled = self.recognizer.enabled
        
        # Initialize state even if disabled (for clean shutdown)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.event_bus = get_event_bus()
        self.app_state = get_app_state()
        
        if not self.enabled:
            logger.info("Song recognition worker disabled")
            return
        
        # Recognition settings
        song_config = config.get('song_recognition', {})
        self.recognition_interval = song_config.get('min_interval_seconds', 30)
        self.audio_buffer_seconds = song_config.get('audio_buffer_seconds', 10)
        
        # Audio buffer for recognition
        self.sample_rate = get_sample_rate()
        self.buffer_size = int(self.sample_rate * self.audio_buffer_seconds)
        self.audio_buffer = []
    
    def start(self):
        """Start the song recognition worker."""
        if not self.enabled:
            logger.info("Song recognition worker not started (disabled)")
            return
        
        if self.running:
            logger.warning("Song recognition worker already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="SongRecognitionWorker")
        self.thread.start()
        logger.info("Song recognition worker started", interval=self.recognition_interval)
    
    def stop(self):
        """Stop the song recognition worker."""
        if not self.running:
            return
        
        logger.info("Stopping song recognition worker...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        logger.info("Song recognition worker stopped")
    
    def _worker_loop(self):
        """Main worker loop - periodically recognizes ambient music."""
        logger.info("Song recognition loop started")
        
        last_recognition_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check if it's time to recognize
                if current_time - last_recognition_time >= self.recognition_interval:
                    # Collect audio buffer
                    audio_data = self._collect_audio_buffer()
                    
                    if audio_data:
                        # Attempt recognition
                        logger.debug("Attempting song recognition...")
                        song_info = self.recognizer.recognize_from_audio(audio_data, self.sample_rate)
                        
                        if song_info:
                            # Song recognized!
                            logger.info("Ambient song recognized", 
                                       title=song_info.title,
                                       artist=song_info.artist,
                                       score=song_info.score)
                            
                            # Update app state
                            self._update_app_state(song_info)
                            
                            # Emit event
                            self.event_bus.emit(
                                EventType.SONG_RECOGNIZED,
                                title=song_info.title,
                                artist=song_info.artist,
                                album=song_info.album,
                                score=song_info.score
                            )
                        else:
                            logger.debug("No song recognized in ambient audio")
                    
                    last_recognition_time = current_time
                
                # Sleep briefly
                time.sleep(1.0)
                
            except Exception as e:
                logger.error("Error in song recognition loop", error=str(e))
                time.sleep(5.0)
        
        logger.info("Song recognition loop ended")
    
    def _collect_audio_buffer(self) -> Optional[bytes]:
        """Collect audio buffer for recognition.
        
        Returns:
            Audio data as bytes (WAV format) or None
        """
        try:
            # Collect audio frames
            frames = []
            samples_needed = self.buffer_size
            
            logger.debug("Collecting audio buffer", seconds=self.audio_buffer_seconds)
            
            while len(frames) * 2048 < samples_needed and self.running:
                audio_frame = get_audio_frame()
                if audio_frame:
                    frames.append(audio_frame)
                else:
                    time.sleep(0.01)
            
            if not frames:
                return None
            
            # Concatenate frames
            audio_data = b''.join(frames)
            
            # Convert to WAV format (ACRCloud expects WAV)
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            
            wav_bytes = wav_buffer.getvalue()
            logger.debug("Audio buffer collected", size_bytes=len(wav_bytes))
            
            return wav_bytes
            
        except Exception as e:
            logger.error("Failed to collect audio buffer", error=str(e))
            return None
    
    def _update_app_state(self, song_info: SongInfo):
        """Update app state with recognized song.
        
        Args:
            song_info: Recognized song information
        """
        try:
            # Update ambient song in app state
            from core.app_state import TrackInfo
            
            track_info = TrackInfo(
                title=song_info.title,
                artist=song_info.artist,
                album=song_info.album or "",
                duration=song_info.duration_ms / 1000.0 if song_info.duration_ms else 0.0
            )
            
            # Store in app state (we'll add this method)
            self.app_state.update_ambient_song(track_info)
            
        except Exception as e:
            logger.error("Failed to update app state", error=str(e))