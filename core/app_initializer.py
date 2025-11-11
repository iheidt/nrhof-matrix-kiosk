#!/usr/bin/env python3
"""Application initialization - setup and configuration."""

import os
import sys

from core.app_context import AppContext
from core.app_state import get_app_state
from core.event_bus import get_event_bus
from core.logger import get_logger
from core.source_manager import SourceManager
from integrations.sonos_source import SonosSource
from integrations.spotify_source import SpotifySource
from integrations.webflow_cache import WebflowCache, WebflowCacheManager
from integrations.webflow_client import create_webflow_client
from renderers import create_renderer
from routing.intent_handlers import register_all_intents
from routing.intent_router import IntentRouter
from routing.voice_commands import register_all_voice_commands
from routing.voice_engine import VoiceEngine
from routing.voice_router import VoiceRouter
from scenes.scene_manager import SceneManager
from scenes.scene_registry import register_all_scenes
from workers.audio_worker import AudioWorker
from workers.mic_listener_worker import MicListenerWorker
from workers.recognition_worker import RecognitionWorker
from workers.song_recognition_worker import SongRecognitionWorker
from workers.wake_word_worker import WakeWordWorker


def init_pygame_env():
    """Initialize pygame environment variables."""
    os.environ.setdefault("SDL_VIDEO_ALLOW_SCREENSAVER", "0")
    os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    import argparse

    parser = argparse.ArgumentParser(description="NRHOF")
    parser.add_argument("--fullscreen", action="store_true", help="Run in fullscreen mode")
    parser.add_argument("--resolution", type=str, help="Display resolution (e.g., 1280x1024)")
    parser.add_argument("--display", type=int, help="Display index (0=primary, 1=secondary)")
    parser.add_argument(
        "--debug-events",
        action="store_true",
        help="Enable event debugging (logs all events)",
    )
    return parser.parse_args()


def apply_cli_overrides(cfg, args):
    """Apply command-line argument overrides to config.

    Args:
        cfg: Config object
        args: Parsed arguments
    """
    if args.fullscreen:
        cfg.set("render.fullscreen", True)
    if args.resolution:
        try:
            width, height = map(int, args.resolution.split("x"))
            cfg.set("render.resolution", [width, height])
        except ValueError:
            print(f"Invalid resolution format: {args.resolution}. Use format: WIDTHxHEIGHT")
            sys.exit(1)
    if args.display is not None:
        cfg.set("render.display", args.display)


def initialize_renderer(cfg):
    """Initialize the renderer.

    Args:
        cfg: Config object

    Returns:
        tuple: (renderer, screen, logger)
    """
    logger = get_logger("kiosk", cfg)

    init_pygame_env()

    renderer = create_renderer(cfg)
    renderer.initialize()
    screen = renderer.get_surface()

    logger.info(
        "Renderer initialized",
        backend=cfg.get("render.backend", "pygame"),
        resolution=cfg.get("render.resolution"),
    )

    return renderer, screen, logger


def initialize_fonts(cfg, logger):
    """Initialize custom fonts.

    Args:
        cfg: Config object
        logger: Logger instance
    """
    from ui.fonts import clear_render_cache, init_custom_fonts

    init_custom_fonts(cfg)
    clear_render_cache()  # Clear any stale cached renders
    logger.info("Custom fonts initialized")


def create_app_components(cfg, screen):
    """Create all application components.

    Args:
        cfg: Config object
        screen: Pygame surface

    Returns:
        dict: Dictionary of components
    """
    logger = get_logger("app_initializer")

    # Get event bus for injection
    event_bus = get_event_bus()

    voice_router = VoiceRouter()
    intent_router = IntentRouter(event_bus=event_bus)  # Inject event_bus
    voice_engine = VoiceEngine(voice_router)
    scene_manager = SceneManager(screen, cfg)
    app_context = AppContext(
        cfg,
        scene_manager,
        voice_router,
        voice_engine,
        intent_router,
    )
    event_bus = get_event_bus()
    app_state = get_app_state()

    # Attach event_bus and app_state to app_context for dependency injection
    app_context.event_bus = event_bus
    app_context.app_state = app_state

    # Initialize Webflow cache manager
    webflow_cache_manager = None
    webflow_client = create_webflow_client(cfg, logger)
    if webflow_client:
        cache = WebflowCache(logger=logger)
        webflow_cache_manager = WebflowCacheManager(webflow_client, cache, logger)
        # Attach to app context for easy access
        app_context.webflow_cache_manager = webflow_cache_manager
        logger.info("Webflow cache manager initialized")

    return {
        "voice_router": voice_router,
        "intent_router": intent_router,
        "voice_engine": voice_engine,
        "scene_manager": scene_manager,
        "app_context": app_context,
        "event_bus": event_bus,
        "app_state": app_state,
        "webflow_cache_manager": webflow_cache_manager,
    }


def start_workers(cfg, voice_engine=None):
    """Start background workers.

    Args:
        cfg: Config object
        voice_engine: VoiceEngine instance (for wake word callback)

    Returns:
        dict: Dictionary of workers
    """
    logger = get_logger("app_initializer")
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

    # Mic listener worker (debug - monitors mic input)
    mic_listener_config = config_dict.get("mic_listener", {})
    mic_listener_worker = None
    if mic_listener_config.get("enabled", False):
        event_bus = get_event_bus()
        mic_listener_worker = MicListenerWorker(event_bus, mic_listener_config)
        mic_listener_worker.start()
        logger.info("MicListenerWorker started (debug mode)")

    return {
        "audio_worker": audio_worker,
        "recognition_worker": recognition_worker,
        "wake_word_worker": wake_word_worker,
        "song_recognition_worker": song_recognition_worker,
        "source_manager": source_manager,
        "spotify_source": spotify_source,
        "sonos_source": sonos_source,
        "mic_listener_worker": mic_listener_worker,
    }


def register_all_handlers(components):
    """Register all handlers (intents, voice commands, scenes).

    Args:
        components: Dictionary of app components
    """
    register_all_scenes(components["scene_manager"], components["app_context"])
    register_all_intents(
        components["intent_router"],
        components["scene_manager"],
        components["app_context"],
    )
    register_all_voice_commands(components["voice_router"], components["intent_router"])


# Preload functions moved to core/preload_manager.py to avoid duplication
# Import them here for backwards compatibility
