import time

from nrhof.core.audio_io import get_mic_stream, stream_mic_frames
from nrhof.core.event_bus import EventType
from nrhof.core.logging_utils import setup_logger
from nrhof.voice.vad import create_vad

from .base import BaseWorker

logger = setup_logger(__name__)


class VADWorker(BaseWorker):
    """Voice Activity Detection worker.

    Streams 10ms mic frames, runs VAD, and emits speech events.
    """

    def __init__(self, event_bus, config: dict | None = None):
        """Initialize VAD worker.

        Args:
            event_bus: Event bus instance
            config: Configuration dict with vad settings
        """
        super().__init__(event_bus)
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

        if not self.enabled:
            logger.info("VAD worker disabled by config")
            return

        # VAD settings
        self.sample_rate = self.config.get("sample_rate", 16000)
        self.frame_duration_ms = self.config.get("frame_duration_ms", 10)
        self.aggressiveness = self.config.get("aggressiveness", 2)
        self.tail_ms = self.config.get("tail_ms", 700)

        # Create VAD
        self.vad = create_vad(
            sample_rate=self.sample_rate,
            frame_duration_ms=self.frame_duration_ms,
            aggressiveness=self.aggressiveness,
            tail_ms=self.tail_ms,
        )

        if self.vad is None:
            logger.error("Failed to create VAD, worker disabled")
            self.enabled = False
            return

        # Stats
        self.frame_count = 0
        self.speech_count = 0
        self.last_log_time = 0.0

    def start(self):
        """Start VAD worker."""
        if not self.enabled:
            logger.info("VAD worker not started (disabled)")
            return
        super().start()

    def _worker_loop(self):
        """Main worker loop - streams mic frames and runs VAD."""
        # Initialize mic stream
        if not get_mic_stream(sample_rate=self.sample_rate, frame_size=512):
            logger.error("Failed to initialize mic stream")
            return

        logger.info(f"VAD worker started: {self.frame_duration_ms}ms frames")
        self.last_log_time = time.time()

        # Stream frames and run VAD
        for frame in stream_mic_frames(frame_duration_ms=self.frame_duration_ms):
            if not self._running:
                break

            self.frame_count += 1
            current_time = time.time()

            # Run VAD on frame
            is_speech, speech_started, speech_ended = self.vad.process_frame(frame)

            # Emit events
            if speech_started:
                self.speech_count += 1
                logger.info("Speech started")
                self.event_bus.emit(EventType.VOICE_SPEECH_START)

            if speech_ended:
                logger.info("Speech ended")
                self.event_bus.emit(EventType.VOICE_SPEECH_END)

            # Log stats every 10 seconds
            if current_time - self.last_log_time >= 10.0:
                elapsed = current_time - self.last_log_time
                fps = self.frame_count / elapsed
                logger.info(
                    f"VAD stats: {self.frame_count} frames in {elapsed:.1f}s "
                    f"({fps:.1f} fps), {self.speech_count} speech segments"
                )
                self.frame_count = 0
                self.speech_count = 0
                self.last_log_time = current_time

        logger.info("VAD worker stopped")

    def _cleanup(self):
        """Cleanup resources."""
        if self.vad:
            self.vad.reset()
        logger.info("VAD worker cleanup complete")
