#!/usr/bin/env python3
"""Worker management - startup and coordination of background workers."""

from core.logger import get_logger
from core.source_manager import SourceManager
from integrations.sonos_source import SonosSource
from integrations.spotify_source import SpotifySource
from workers.audio_worker import AudioWorker
from workers.recognition_worker import RecognitionWorker
from workers.song_recognition_worker import SongRecognitionWorker
from workers.wake_word_worker import WakeWordWorker


def start_workers(cfg, voice_engine=None):
    """Start background workers.

    Args:
        cfg: Config object
        voice_engine: VoiceEngine instance (for wake word callback)

    Returns:
        dict: Dictionary of workers
    """
    logger = get_logger("worker_manager")
    config_dict = cfg

    # Audio worker (always runs)
    audio_worker = AudioWorker(config_dict)
    audio_worker.start()

    # Recognition worker (legacy, may be disabled)
    recognition_worker = RecognitionWorker(config_dict)
    recognition_worker.start()

    # Wake word worker (new)
    wake_word_worker = WakeWordWorker(config_dict)
    if wake_word_worker.enabled and voice_engine:
        # Set callback to activate voice engine when wake word detected
        def on_wake_word(keyword):
            logger.info("Wake word detected, activating voice engine", keyword=keyword)
            voice_engine.start_listening()

        wake_word_worker.set_callback(on_wake_word)
    wake_word_worker.start()

    # Song recognition worker (legacy ambient ACR - disabled)
    song_recognition_worker = SongRecognitionWorker(config_dict)
    song_recognition_worker.start()

    # Source Manager (new music source arbitration)
    source_manager = SourceManager(config_dict)
    logger.info("SourceManager initialized")

    # Spotify source (primary music source - priority 1)
    spotify_source = SpotifySource(config_dict, source_manager)
    spotify_source.start()

    # Sonos source (secondary music source - priority 2)
    sonos_source = SonosSource(config_dict, source_manager)
    sonos_source.start()

    return {
        "audio_worker": audio_worker,
        "recognition_worker": recognition_worker,
        "wake_word_worker": wake_word_worker,
        "song_recognition_worker": song_recognition_worker,
        "source_manager": source_manager,
        "spotify_source": spotify_source,
        "sonos_source": sonos_source,
    }
