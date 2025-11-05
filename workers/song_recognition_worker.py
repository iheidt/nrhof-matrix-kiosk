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
                    print(f"[SONG] Attempting recognition at {current_time:.1f}s")
                    # Collect audio buffer
                    audio_data = self._collect_audio_buffer()
                    print(f"[SONG] Buffer collected: {len(audio_data) if audio_data else 0} bytes")
                    
                    if audio_data:
                        # Attempt recognition
                        print(f"[SONG] Calling ACRCloud API...")
                        logger.debug("Attempting song recognition...")
                        song_info = self.recognizer.recognize_from_audio(audio_data, self.sample_rate)
                        print(f"[SONG] API returned: {song_info}")
                        
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
                import traceback
                print(f"[SONG] Loop error: {e}")
                print(f"[SONG] Traceback: {traceback.format_exc()}")
                logger.error("Error in song recognition loop", error=str(e), traceback=traceback.format_exc())
                time.sleep(5.0)
        
        logger.info("Song recognition loop ended")
    
    def _collect_audio_buffer(self) -> Optional[bytes]:
        """Collect audio buffer for recognition.
        
        Returns:
            Audio data as bytes (WAV format) or None
        """
        try:
            # Collect audio frames with timeout
            # get_audio_frame() returns numpy float32 array [-1, 1]
            frames = []
            samples_per_frame = 4096  # samples per call to get_audio_frame()
            frames_needed = int((self.sample_rate * self.audio_buffer_seconds) / samples_per_frame)
            
            logger.debug("Collecting audio buffer", 
                        seconds=self.audio_buffer_seconds,
                        frames_needed=frames_needed)
            
            start_time = time.time()
            timeout = self.audio_buffer_seconds + 5  # Give extra time
            
            while len(frames) < frames_needed and self.running:
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning("Audio buffer collection timeout",
                                 frames_collected=len(frames),
                                 frames_needed=frames_needed)
                    break
                
                audio_frame = get_audio_frame()  # Returns numpy float32 array
                if audio_frame is not None and len(audio_frame) > 0:
                    frames.append(audio_frame)
                else:
                    time.sleep(0.01)
            
            if not frames:
                logger.warning("No audio frames collected")
                return None
            
            if len(frames) < frames_needed / 2:
                logger.warning("Insufficient audio frames",
                             collected=len(frames),
                             needed=frames_needed)
                return None
            
            # Concatenate numpy arrays and convert to int16 PCM
            audio_float = np.concatenate(frames)
            # Convert float32 [-1, 1] to int16 [-32768, 32767]
            audio_int16 = (audio_float * 32767).astype(np.int16)
            audio_data = audio_int16.tobytes()
            
            # Convert to WAV format (ACRCloud expects WAV)
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            
            wav_bytes = wav_buffer.getvalue()
            print(f"[SONG] WAV: {len(wav_bytes)} bytes, {self.sample_rate}Hz, 16-bit, mono, {len(audio_data)/2/self.sample_rate:.1f}s")
            logger.debug("Audio buffer collected",
                        frames=len(frames),
                        size_bytes=len(wav_bytes))
            
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