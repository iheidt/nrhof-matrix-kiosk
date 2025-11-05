#!/usr/bin/env python3
import threading
import time
import os
import tempfile
from pathlib import Path

import sounddevice as sd
import numpy as np
from scipy.io import wavfile
from openai import OpenAI

from routing.voice_router import VoiceRouter


class VoiceEngine:
    """Voice engine adapter for microphone input and wakeword detection."""
    
    def __init__(self, router: VoiceRouter):
        """Initialize voice engine with router.
        
        Args:
            router: VoiceRouter instance to send transcribed text to
        """
        self.router = router
        self.running = False
        self.thread = None
        self.listening_for_command = False
        
        # Audio settings
        self.sample_rate = 16000  # 16kHz for Whisper
        self.duration = 2.5  # seconds
        
        # OpenAI client (optional - only if API key is set)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            print("Warning: OPENAI_API_KEY not set. STT will not work.")
    
    def start(self):
        """Start the voice engine microphone thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("Voice engine started")
    
    def stop(self):
        """Stop the voice engine microphone thread."""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        print("Voice engine stopped")
    
    def trigger_wakeword(self):
        """Trigger wakeword detection (for testing or actual detection).
        
        Sets the engine into listening mode, ready to process the next speech input.
        """
        self.listening_for_command = True
        print("wakeword detected")
    
    def _listen_loop(self):
        """Background thread that will listen for microphone input.
        
        This is a placeholder that will eventually:
        1. Capture audio from microphone
        2. Detect wakeword (or use trigger_wakeword() for testing)
        3. When listening_for_command is True, transcribe speech
        4. Call self.router.process_text(transcribed_text)
        """
        last_idle_print = time.time()
        
        while self.running:
            # TODO: Add Porcupine wakeword detection here
            # TODO: When wakeword detected, call self.trigger_wakeword()
            
            # If wakeword was triggered, process speech
            if self.listening_for_command:
                # Process STT in a separate thread to avoid blocking
                stt_thread = threading.Thread(target=self._process_stt, daemon=True)
                stt_thread.start()
                # Reset flag immediately so we don't trigger multiple times
                self.listening_for_command = False
            
            # Placeholder: print idle message every 10 seconds
            current_time = time.time()
            if current_time - last_idle_print >= 10.0:
                print("voice engine idle")
                last_idle_print = current_time
            
            # Sleep briefly to avoid busy-waiting
            time.sleep(0.1)
    
    def _process_stt(self):
        """Process speech-to-text in a separate thread."""
        try:
            # Check if OpenAI client is available
            if not self.openai_client:
                print("STT error: OpenAI API key not set")
                return
            
            # Record audio
            print("recording command...")
            audio_data = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16
            )
            sd.wait()  # Wait for recording to complete
            
            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                wavfile.write(tmp_path, self.sample_rate, audio_data)
            
            # Transcribe with OpenAI Whisper
            print("transcribing...")
            with open(tmp_path, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            # Get transcribed text
            text = transcript.text.strip()
            print(f"transcribed text: {text}")
            
            # Route to voice router
            if text:
                self.router.process_text(text)
        
        except Exception as e:
            print(f"STT error: {e}")
            # Reset state on error
            self.listening_for_command = False
