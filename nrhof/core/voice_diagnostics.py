#!/usr/bin/env python3
"""Voice diagnostics and logging.

Logs voice interaction metrics to logs/voice.jsonl for analysis:
- Wake word detection scores
- VAD (Voice Activity Detection) percentages
- ASR (Automatic Speech Recognition) confidence
- Intent recognition confidence
- Total round-trip time (RTT)
"""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from nrhof.core.logger import get_logger

logger = get_logger("voice_diagnostics")


@dataclass
class VoiceInteractionMetrics:
    """Metrics for a single voice interaction."""

    timestamp: float
    interaction_id: str

    # Wake word detection
    wake_score: float | None = None  # 0.0-1.0 confidence
    wake_keyword: str | None = None

    # Voice Activity Detection
    vad_percent: float | None = None  # % of frames with voice activity
    vad_duration_ms: float | None = None  # Duration of voice activity

    # Speech Recognition
    asr_confidence: float | None = None  # 0.0-1.0 confidence
    asr_text: str | None = None
    asr_latency_ms: float | None = None

    # Intent Recognition
    intent_name: str | None = None
    intent_confidence: float | None = None  # 0.0-1.0 confidence
    intent_slots: dict[str, Any] | None = None

    # Total timing
    total_rtt_ms: float | None = None  # Wake → Intent execution

    # TTS (if applicable)
    tts_latency_ms: float | None = None
    tts_duration_ms: float | None = None

    # Errors
    error: str | None = None


class VoiceDiagnosticsLogger:
    """Logger for voice interaction diagnostics."""

    def __init__(self, log_dir: str = "logs"):
        """Initialize voice diagnostics logger.

        Args:
            log_dir: Directory to write voice.jsonl log file
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "voice.jsonl"

        # Current interaction tracking
        self._current_interaction: VoiceInteractionMetrics | None = None
        self._interaction_start_time: float | None = None

        logger.info(f"Voice diagnostics logging to {self.log_file}")

    def start_interaction(self, interaction_id: str | None = None) -> str:
        """Start tracking a new voice interaction.

        Args:
            interaction_id: Optional ID (auto-generated if not provided)

        Returns:
            Interaction ID
        """
        if interaction_id is None:
            interaction_id = f"voice_{int(time.time() * 1000)}"

        self._interaction_start_time = time.time()
        self._current_interaction = VoiceInteractionMetrics(
            timestamp=self._interaction_start_time,
            interaction_id=interaction_id,
        )

        return interaction_id

    def log_wake_word(self, score: float, keyword: str):
        """Log wake word detection.

        Args:
            score: Wake word confidence score (0.0-1.0)
            keyword: Detected keyword
        """
        if self._current_interaction is None:
            self.start_interaction()

        self._current_interaction.wake_score = score
        self._current_interaction.wake_keyword = keyword

    def log_vad(self, percent: float, duration_ms: float):
        """Log voice activity detection.

        Args:
            percent: Percentage of frames with voice activity
            duration_ms: Duration of voice activity in milliseconds
        """
        if self._current_interaction:
            self._current_interaction.vad_percent = percent
            self._current_interaction.vad_duration_ms = duration_ms

    def log_asr(self, text: str, confidence: float, latency_ms: float):
        """Log speech recognition result.

        Args:
            text: Recognized text
            confidence: ASR confidence score (0.0-1.0)
            latency_ms: ASR processing latency
        """
        if self._current_interaction:
            self._current_interaction.asr_text = text
            self._current_interaction.asr_confidence = confidence
            self._current_interaction.asr_latency_ms = latency_ms

    def log_intent(
        self,
        intent_name: str,
        confidence: float,
        slots: dict[str, Any] | None = None,
    ):
        """Log intent recognition result.

        Args:
            intent_name: Recognized intent name
            confidence: Intent confidence score (0.0-1.0)
            slots: Intent slot values
        """
        if self._current_interaction:
            self._current_interaction.intent_name = intent_name
            self._current_interaction.intent_confidence = confidence
            self._current_interaction.intent_slots = slots

    def log_tts(self, latency_ms: float, duration_ms: float):
        """Log text-to-speech metrics.

        Args:
            latency_ms: TTS generation latency
            duration_ms: TTS audio duration
        """
        if self._current_interaction:
            self._current_interaction.tts_latency_ms = latency_ms
            self._current_interaction.tts_duration_ms = duration_ms

    def log_error(self, error: str):
        """Log error in voice interaction.

        Args:
            error: Error message
        """
        if self._current_interaction:
            self._current_interaction.error = error

    def end_interaction(self):
        """End current interaction and write to log."""
        if self._current_interaction is None:
            return

        # Calculate total RTT
        if self._interaction_start_time:
            total_rtt = (time.time() - self._interaction_start_time) * 1000
            self._current_interaction.total_rtt_ms = round(total_rtt, 2)

        # Write to JSONL file
        try:
            with open(self.log_file, "a") as f:
                json.dump(asdict(self._current_interaction), f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write voice diagnostics: {e}")

        # Reset
        self._current_interaction = None
        self._interaction_start_time = None

    def get_current_metrics(self) -> VoiceInteractionMetrics | None:
        """Get current interaction metrics.

        Returns:
            Current interaction metrics or None
        """
        return self._current_interaction


# Global instance
_voice_diagnostics: VoiceDiagnosticsLogger | None = None


def get_voice_diagnostics() -> VoiceDiagnosticsLogger:
    """Get global voice diagnostics logger.

    Returns:
        Global VoiceDiagnosticsLogger instance
    """
    global _voice_diagnostics
    if _voice_diagnostics is None:
        _voice_diagnostics = VoiceDiagnosticsLogger()
    return _voice_diagnostics
