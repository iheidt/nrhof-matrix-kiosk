"""Voice engine orchestrator - coordinates wake word, VAD, ASR, NLU, TTS pipeline."""

import os
import tempfile
import threading
import time

import numpy as np
import sounddevice as sd
from openai import OpenAI
from scipy.io import wavfile

from nrhof.voice.asr import ASR
from nrhof.voice.nlu import GrammarNLU
from nrhof.voice.tts import TTS


class VoiceEngine:
    """Voice engine orchestrator for the complete voice pipeline.

    Coordinates:
    - Wake word detection (via external trigger)
    - Voice Activity Detection (VAD)
    - Automatic Speech Recognition (ASR)
    - Natural Language Understanding (NLU)
    - Text-to-Speech (TTS)

    Note: AEC and noise suppression are handled by VoiceFrontEndWorker.
    """

    def __init__(self, voice_router, ctx=None):
        """Initialize voice engine with router.

        Args:
            voice_router: VoiceRouter instance to send recognized intents to
            ctx: Application context (optional)
        """
        self.router = voice_router
        self.ctx = ctx
        self.running = False
        self.thread = None
        self.listening_for_command = False

        # Audio settings
        self.sample_rate = 16000  # 16kHz for Whisper
        self.duration = 2.5  # seconds

        # Voice pipeline components
        # Note: AEC and Koala are handled by VoiceFrontEndWorker via create_voice_pipeline()
        self.asr = ASR(ctx)
        self.nlu = GrammarNLU()
        self.tts = TTS()

        # OpenAI client (optional - only if API key is set)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            print("Warning: OPENAI_API_KEY not set. STT will not work.")

    def start(self):
        """Start the voice engine orchestration thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._orchestration_loop,
            daemon=True,
            name="voice_engine_orchestrator",
        )
        self.thread.start()
        print("Voice engine started")

    def stop(self):
        """Stop the voice engine orchestration thread."""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        print("Voice engine stopped")

    def trigger_wakeword(self):
        """Trigger wake word detection (called by wake word worker).

        Sets the engine into listening mode, ready to process the next speech input.
        """
        self.listening_for_command = True
        print("wakeword detected")

    def _orchestration_loop(self):
        """Background orchestration loop.

        Coordinates the voice pipeline:
        1. Wait for wake word trigger (set by external wake word worker)
        2. When triggered, process speech through ASR → NLU → Router
        3. Return to idle state
        """
        last_idle_print = time.time()

        while self.running:
            # Check if wake word was triggered
            if self.listening_for_command:
                # Process STT in a separate thread to avoid blocking
                stt_thread = threading.Thread(
                    target=self._process_speech_pipeline,
                    daemon=True,
                    name="voice_speech_pipeline",
                )
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

    def _process_speech_pipeline(self):
        """Process complete speech pipeline: ASR → NLU → Router."""
        try:
            # Step 1: ASR (Automatic Speech Recognition)
            text = self._run_asr()
            if not text:
                return

            print(f"transcribed text: {text}")

            # Step 2: NLU (Natural Language Understanding) - optional
            # For now, pass raw text to router
            # In future: intent = self.nlu.parse(text)

            # Step 3: Route to voice router
            self.router.process_text(text)

        except Exception as e:
            print(f"Speech pipeline error: {e}")
            self.listening_for_command = False

    def _run_asr(self) -> str | None:
        """Run Automatic Speech Recognition.

        Returns:
            Transcribed text or None if failed
        """
        try:
            # Check if OpenAI client is available
            if not self.openai_client:
                print("STT error: OpenAI API key not set")
                return None

            # Record audio
            print("recording command...")
            audio_data = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
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
                    language="en",
                )

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            # Return transcribed text
            return transcript.text.strip()

        except Exception as e:
            print(f"ASR error: {e}")
            return None
