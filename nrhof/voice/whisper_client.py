"""Whisper ASR client for local whisper.cpp server."""

import io
import wave

import numpy as np
import requests

from nrhof.core.logging_utils import setup_logger


class WhisperClient:
    """Client for whisper.cpp server ASR."""

    def __init__(self, server_url: str = "http://127.0.0.1:9001", timeout: float = 5.0):
        """Initialize Whisper client.

        Args:
            server_url: URL of whisper.cpp server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url
        self.timeout = timeout
        self.logger = setup_logger("whisper_client")
        self.logger.info(f"WhisperClient initialized (server: {server_url})")

    def transcribe(self, audio_int16: np.ndarray, sample_rate: int = 16000) -> str | None:
        """Transcribe audio to text.

        Args:
            audio_int16: Audio samples as int16 numpy array
            sample_rate: Sample rate (default: 16000)

        Returns:
            Transcribed text or None on failure
        """
        try:
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int16.tobytes())

            wav_buffer.seek(0)

            # Send to whisper.cpp server
            response = requests.post(
                f"{self.server_url}/inference",
                files={"file": ("audio.wav", wav_buffer, "audio/wav")},
                timeout=self.timeout,
            )

            if response.status_code != 200:
                self.logger.error(f"Whisper server error: {response.status_code}")
                return None

            result = response.json()
            text = result.get("text", "").strip()

            # Filter out blank audio markers
            if text in ["[BLANK_AUDIO]", ""]:
                self.logger.debug("Whisper returned blank/silence")
                return None

            self.logger.info(f"Whisper transcribed: '{text}'")
            return text

        except requests.exceptions.Timeout:
            self.logger.error("Whisper request timeout")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to Whisper server")
            return None
        except Exception as e:
            self.logger.error(f"Whisper transcription failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Whisper server is available.

        Returns:
            True if server is reachable
        """
        try:
            response = requests.get(f"{self.server_url}/", timeout=1.0)
            return response.status_code in [200, 404]  # 404 is ok, means server is up
        except Exception:
            return False
