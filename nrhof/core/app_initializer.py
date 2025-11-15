#!/usr/bin/env python3
"""Application initialization - setup and configuration."""

import os
import sys

from nrhof.core.app_context import AppContext
from nrhof.core.app_state import get_app_state
from nrhof.core.event_bus import get_event_bus
from nrhof.core.logging_utils import setup_logger
from nrhof.core.source_manager import SourceManager
from nrhof.core.voice_event_handler import init_voice_event_handler
from nrhof.integrations.sonos_source import SonosSource
from nrhof.integrations.spotify_source import SpotifySource
from nrhof.integrations.webflow_cache import WebflowCache, WebflowCacheManager
from nrhof.integrations.webflow_client import create_webflow_client
from nrhof.renderers import create_renderer
from nrhof.routing.intent_handlers import register_all_intents
from nrhof.routing.intent_router import IntentRouter
from nrhof.routing.voice_commands import register_all_voice_commands
from nrhof.routing.voice_router import VoiceRouter
from nrhof.scenes.registry import register_all_scenes
from nrhof.scenes.scene_manager import SceneManager
from nrhof.voice.engine import VoiceEngine
from nrhof.workers.audio_worker import AudioWorker
from nrhof.workers.mic_listener_worker import MicListenerWorker
from nrhof.workers.recognition_worker import RecognitionWorker
from nrhof.workers.song_recognition_worker import SongRecognitionWorker
from nrhof.workers.touch_worker import TouchInputWorker
from nrhof.workers.vad_worker import VADWorker
from nrhof.workers.wake_word_worker import WakeWordWorker


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
    logger = setup_logger("kiosk")

    init_pygame_env()

    renderer = create_renderer(cfg)
    renderer.initialize()
    screen = renderer.get_surface()

    backend = cfg.get("render.backend", "pygame")
    resolution = cfg.get("render.resolution")
    logger.info(f"Renderer initialized: backend={backend}, resolution={resolution}")

    return renderer, screen, logger


def initialize_fonts(cfg, logger):
    """Initialize custom fonts.

    Args:
        cfg: Config object
        logger: Logger instance
    """
    from nrhof.ui.fonts import clear_render_cache, init_custom_fonts

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
    logger = setup_logger("app_initializer")

    # Get event bus for injection
    event_bus = get_event_bus()

    voice_router = VoiceRouter()
    intent_router = IntentRouter(event_bus=event_bus)  # Inject event_bus
    scene_manager = SceneManager(screen, cfg)

    # Create app_context first so we can pass it to VoiceEngine
    app_context = AppContext(
        cfg,
        scene_manager,
        voice_router,
        None,  # voice_engine will be set after creation
        intent_router,
    )

    # Create VoiceEngine with context and wire it back to app_context
    voice_engine = VoiceEngine(voice_router, ctx=app_context)
    app_context.voice_engine = voice_engine
    event_bus = get_event_bus()
    app_state = get_app_state()

    # Initialize voice event handler (subscribes to wake word and VAD events)
    init_voice_event_handler()

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
    """Start background workers using WorkerRegistry.

    Args:
        cfg: Config object
        voice_engine: VoiceEngine instance (for wake word callback)

    Returns:
        WorkerRegistry: Registry containing all workers
    """
    from nrhof.core.worker_registry import WorkerRegistry

    logger = setup_logger("app_initializer")
    config_dict = cfg
    event_bus = get_event_bus()

    # Create worker registry
    registry = WorkerRegistry()

    # Register core workers
    registry.register("audio_worker", AudioWorker(config_dict))
    registry.register("recognition_worker", RecognitionWorker(config_dict))
    registry.register("wake_word_worker", WakeWordWorker(config_dict))
    registry.register("song_recognition_worker", SongRecognitionWorker(config_dict))

    # Register source manager and sources
    source_manager = SourceManager(config_dict)
    logger.info("SourceManager initialized")
    registry.register("source_manager", source_manager)
    registry.register("spotify_source", SpotifySource(config_dict, source_manager))
    registry.register("sonos_source", SonosSource(config_dict, source_manager))

    # Register optional workers (conditional)
    mic_listener_config = config_dict.get("mic_listener", {})
    if mic_listener_config.get("enabled", False):
        registry.register("mic_listener_worker", MicListenerWorker(event_bus, mic_listener_config))

    vad_config = config_dict.get("vad", {})
    if vad_config.get("enabled", False):
        registry.register("vad_worker", VADWorker(event_bus, vad_config))

    # Register touch worker (UPDD integration)
    touch_config = config_dict.get("touch", {})
    if touch_config.get("enabled", False):
        registry.register("touch_worker", TouchInputWorker(config_dict))

    # Start all workers
    registry.start_all()

    return registry


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
