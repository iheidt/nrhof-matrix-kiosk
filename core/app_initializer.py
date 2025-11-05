#!/usr/bin/env python3
"""Application initialization - setup and configuration."""

import os
import sys
import threading
from pathlib import Path
import pygame

from scenes.scene_manager import SceneManager
from routing.voice_router import VoiceRouter
from routing.voice_engine import VoiceEngine
from routing.intent_router import IntentRouter
from core.app_context import AppContext
from core.event_bus import get_event_bus
from core.app_state import get_app_state
from workers.audio_worker import AudioWorker
from workers.recognition_worker import RecognitionWorker
from core.logger import get_logger
from renderers import create_renderer
from routing.intent_handlers import register_all_intents
from routing.voice_commands import register_all_voice_commands
from scenes.scene_registry import register_all_scenes, get_preload_list


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
    parser = argparse.ArgumentParser(description='NRHOF')
    parser.add_argument('--fullscreen', action='store_true', help='Run in fullscreen mode')
    parser.add_argument('--resolution', type=str, help='Display resolution (e.g., 1280x1024)')
    parser.add_argument('--display', type=int, help='Display index (0=primary, 1=secondary)')
    return parser.parse_args()


def apply_cli_overrides(cfg, args):
    """Apply command-line argument overrides to config.
    
    Args:
        cfg: Config object
        args: Parsed arguments
    """
    if args.fullscreen:
        cfg.set('render.fullscreen', True)
    if args.resolution:
        try:
            width, height = map(int, args.resolution.split('x'))
            cfg.set('render.resolution', [width, height])
        except ValueError:
            print(f"Invalid resolution format: {args.resolution}. Use format: WIDTHxHEIGHT")
            sys.exit(1)
    if args.display is not None:
        cfg.set('render.display', args.display)


def initialize_renderer(cfg):
    """Initialize the renderer.
    
    Args:
        cfg: Config object
        
    Returns:
        tuple: (renderer, screen, logger)
    """
    logger = get_logger('kiosk', cfg.to_dict())
    
    init_pygame_env()
    
    renderer = create_renderer(cfg.to_dict())
    renderer.initialize()
    screen = renderer.get_surface()
    
    logger.info("Renderer initialized", 
                backend=cfg.get('render.backend', 'pygame'),
                resolution=cfg.get('render.resolution'))
    
    return renderer, screen, logger


def initialize_fonts(cfg, logger):
    """Initialize custom fonts.
    
    Args:
        cfg: Config object
        logger: Logger instance
    """
    from utils import init_custom_fonts
    init_custom_fonts(cfg.to_dict())
    logger.info("Custom fonts initialized")


def create_app_components(cfg, screen):
    """Create all application components.
    
    Args:
        cfg: Config object
        screen: Pygame surface
        
    Returns:
        dict: Dictionary of components
    """
    voice_router = VoiceRouter()
    intent_router = IntentRouter()
    voice_engine = VoiceEngine(voice_router)
    scene_manager = SceneManager(screen, cfg.to_dict())
    app_context = AppContext(cfg.to_dict(), scene_manager, voice_router, voice_engine, intent_router)
    event_bus = get_event_bus()
    app_state = get_app_state()
    
    return {
        'voice_router': voice_router,
        'intent_router': intent_router,
        'voice_engine': voice_engine,
        'scene_manager': scene_manager,
        'app_context': app_context,
        'event_bus': event_bus,
        'app_state': app_state
    }


def start_workers(cfg):
    """Start background workers.
    
    Args:
        cfg: Config object
        
    Returns:
        tuple: (audio_worker, recognition_worker)
    """
    audio_worker = AudioWorker(cfg.to_dict())
    audio_worker.start()
    
    recognition_worker = RecognitionWorker(cfg.to_dict())
    recognition_worker.start()
    
    return audio_worker, recognition_worker


def register_all_handlers(components):
    """Register all handlers (intents, voice commands, scenes).
    
    Args:
        components: Dictionary of app components
    """
    register_all_scenes(components['scene_manager'], components['app_context'])
    register_all_intents(components['intent_router'], components['scene_manager'], components['app_context'])
    register_all_voice_commands(components['voice_router'], components['intent_router'])


def start_preload(scene_manager, app_context):
    """Start background scene preloading.
    
    Args:
        scene_manager: SceneManager instance
        app_context: AppContext instance
        
    Returns:
        threading.Thread: Waiter thread
    """
    # Initialize preload tracking
    app_context.preload_progress = 0.0
    app_context.preload_done = False
    
    # Progress callback
    def _progress(done, total):
        app_context.preload_progress = float(done) / float(total)
    
    # Start preload
    scenes_to_preload = get_preload_list()
    preload_thread = scene_manager.preload_lazy(scenes_to_preload, progress_cb=_progress, sleep_between=0.05)
    
    # Waiter thread to set preload_done
    def _waiter():
        preload_thread.join()
        app_context.preload_done = True
    
    waiter_thread = threading.Thread(target=_waiter, daemon=True)
    waiter_thread.start()
    
    return waiter_thread