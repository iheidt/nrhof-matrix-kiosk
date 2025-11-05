#!/usr/bin/env python3
import os
import sys
import argparse
import importlib
import threading
from pathlib import Path
import pygame

# Import version
from __version__ import __version__

# Load environment variables from .env if python-dotenv is available
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from scene_manager import SceneManager
from scenes.splash_scene import SplashScene  # Only eager import
from voice_router import VoiceRouter
from voice_engine import VoiceEngine
from intent_router import IntentRouter, Intents
from app_context import AppContext
from config_loader import load_config
from event_bus import EventBus, EventType, get_event_bus
from app_state import AppState, get_app_state, SceneProfile
from workers.audio_worker import AudioWorker
from workers.recognition_worker import RecognitionWorker
from logger import get_logger
from renderers import create_renderer

ROOT = Path(__file__).resolve().parent


def register_intents(intent_router: IntentRouter, scene_manager: SceneManager, app_context: AppContext):
    """Register all application intents.
    
    Args:
        intent_router: IntentRouter instance
        scene_manager: SceneManager instance
        app_context: AppContext instance
    """
    # Navigation intents
    intent_router.register(Intents.GO_HOME, lambda **kw: scene_manager.switch_to("MenuScene"))
    intent_router.register(Intents.GO_TO_EXPERIENCE1_HUB, lambda **kw: scene_manager.switch_to("Experience1HubScene"))
    intent_router.register(Intents.GO_TO_EXPERIENCE2_HUB, lambda **kw: scene_manager.switch_to("Experience2HubScene"))
    
    # Main menu option selection
    def select_option_handler(index, **kw):
        if index == 0:
            # NR-38: Music video (was Experience 2)
            scene_manager.switch_to("Experience2HubScene")
        elif index == 1:
            # NR-18: Not implemented yet
            print(f"Placeholder: NR-18 not implemented yet")
        elif index == 2:
            # Visualizer (was Experience 1)
            scene_manager.switch_to("Experience1HubScene")
        elif index == 3:
            # Fate maker: Not implemented yet
            print(f"Placeholder: Fate maker not implemented yet")
        else:
            print(f"Placeholder: Option {index+1} not implemented yet")
    intent_router.register(Intents.SELECT_OPTION, select_option_handler)
    
    # Sub-experience selection
    def select_sub_experience_handler(id, **kw):
        if id == "spectrum_bars":
            scene_manager.switch_to("Experience1SpectrumBarsScene")
        elif id == "waveform":
            scene_manager.switch_to("Experience1WaveformScene")
        elif id == "lissajous":
            scene_manager.switch_to("Experience1LissajousScene")
        elif id == "video_list":
            scene_manager.switch_to("VideoListScene")
        elif id.startswith("video:"):
            # Extract filename from id (format: "video:filename.mp4")
            filename = id.split(":", 1)[1]
            # Store filename in app context for the video player to pick up
            app_context.selected_video = filename
            scene_manager.switch_to("VideoPlayerScene")
        else:
            print(f"Unknown sub-experience: {id}")
    intent_router.register(Intents.SELECT_SUB_EXPERIENCE, select_sub_experience_handler)


def init_pygame_env():
    """Initialize pygame environment variables."""
    os.environ.setdefault("SDL_VIDEO_ALLOW_SCREENSAVER", "0")
    os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
    # Prevent window from minimizing when focus is lost
    os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")



# Global voice router instance for testing/access
voice_router = None


def main():
    global voice_router
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='NRHOF')
    parser.add_argument('--fullscreen', action='store_true', help='Run in fullscreen mode')
    parser.add_argument('--resolution', type=str, help='Display resolution (e.g., 1280x1024)')
    parser.add_argument('--display', type=int, help='Display index (0=primary, 1=secondary)')
    args = parser.parse_args()
    
    cfg = load_config()
    
    # Override config with command-line arguments
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
    
    # Initialize logger
    logger = get_logger('kiosk', cfg.to_dict())
    logger.info("Starting NRHOF", version=__version__)
    
    # Initialize pygame environment
    init_pygame_env()
    
    # Create renderer
    renderer = create_renderer(cfg.to_dict())
    renderer.initialize()
    screen = renderer.get_surface()  # Get pygame surface for backward compatibility
    logger.info("Renderer initialized", backend=cfg.get('render.backend', 'pygame'), 
                resolution=cfg.get('render.resolution'))
    
    # Initialize custom fonts
    from utils import init_custom_fonts
    init_custom_fonts(cfg.to_dict())
    logger.info("Custom fonts initialized")
    
    # Hide mouse cursor for kiosk mode
    pygame.mouse.set_visible(False)
    
    # Create and configure voice router
    voice_router = VoiceRouter()
    
    # Create intent router
    intent_router = IntentRouter()
    
    # Create voice engine (but don't start yet)
    voice_engine = VoiceEngine(voice_router)
    
    # Create scene manager
    scene_manager = SceneManager(screen, cfg.to_dict())  # Pass as dict for now
    
    # Create app context
    app_context = AppContext(cfg.to_dict(), scene_manager, voice_router, voice_engine, intent_router)
    
    # Initialize event bus and app state
    event_bus = get_event_bus()
    app_state = get_app_state()
    
    # Start audio worker
    audio_worker = AudioWorker(cfg.to_dict())
    audio_worker.start()
    
    # Start recognition worker
    recognition_worker = RecognitionWorker(cfg.to_dict())
    recognition_worker.start()
    
    # Initialize preload tracking
    app_context.preload_progress = 0.0
    app_context.preload_done = False
    
    # Eagerly register and switch to Splash
    scene_manager.register_scene('SplashScene', SplashScene(app_context))
    
    # Register all other scenes lazily
    def make_factory(module_name, class_name):
        def factory():
            module = importlib.import_module(module_name)
            scene_class = getattr(module, class_name)
            return scene_class(app_context)
        return factory
    
    scene_manager.register_lazy('IntroScene', make_factory('scenes.intro_scene', 'IntroScene'))
    scene_manager.register_lazy('MenuScene', make_factory('scenes.menu_scene', 'MenuScene'))
    scene_manager.register_lazy('Experience1HubScene', make_factory('scenes.experience1_hub_scene', 'Experience1HubScene'))
    scene_manager.register_lazy('Experience1SpectrumBarsScene', make_factory('scenes.experience1_spectrum_bars', 'Experience1SpectrumBarsScene'))
    scene_manager.register_lazy('Experience1WaveformScene', make_factory('scenes.experience1_waveform', 'Experience1WaveformScene'))
    scene_manager.register_lazy('Experience1LissajousScene', make_factory('scenes.experience1_lissajous', 'Experience1LissajousScene'))
    scene_manager.register_lazy('Experience2HubScene', make_factory('scenes.experience2_hub_scene', 'Experience2HubScene'))
    scene_manager.register_lazy('VideoListScene', make_factory('scenes.video_list_scene', 'VideoListScene'))
    scene_manager.register_lazy('VideoPlayerScene', make_factory('scenes.video_player_scene', 'VideoPlayerScene'))
    
    # Register intent handlers
    register_intents(intent_router, scene_manager, app_context)
    
    # Register voice commands for scene navigation (emit intents)
    def register_voice_commands(voice_router: VoiceRouter, intent_router: IntentRouter):
        """Register all voice commands.
        
        Args:
            voice_router: VoiceRouter instance
            intent_router: IntentRouter instance
        """
        # Navigation commands - all emit go_home intent
        for cmd in ["menu", "home", "main"]:
            voice_router.register_command(cmd, lambda: intent_router.emit(Intents.GO_HOME))
        
        # Option selection with variants
        options = [
            (["one", "1", "first"], 0),
            (["two", "2", "second"], 1),
            (["three", "3", "third"], 2)
        ]
        for variants, index in options:
            for variant in variants:
                voice_router.register_command(
                    variant,
                    lambda idx=index: intent_router.emit(Intents.SELECT_OPTION, index=idx)
                )
    register_voice_commands(voice_router, intent_router)
    voice_router.register_command("three", lambda: intent_router.emit("select_option", index=2))
    voice_router.register_command("3", lambda: intent_router.emit("select_option", index=2))  # Number variant
    voice_router.register_command("third", lambda: intent_router.emit("select_option", index=2))  # Alternative
    
    # Start voice engine
    voice_engine.start()
    
    # Start with splash screen
    scene_manager.switch_to("SplashScene")
    
    # Kick off background preload
    def _progress(done, total):
        app_context.preload_progress = float(done) / float(total)
    
    scenes_to_preload = [
        'IntroScene',
        'MenuScene',
        'Experience1HubScene',
        'Experience1SpectrumBarsScene',
        'Experience1WaveformScene',
        'Experience1LissajousScene',
        'Experience2HubScene',
        'VideoListScene',
        'VideoPlayerScene'
    ]
    
    preload_thread = scene_manager.preload_lazy(scenes_to_preload, progress_cb=_progress, sleep_between=0.05)
    
    # Waiter thread to set preload_done
    def _waiter():
        preload_thread.join()
        app_context.preload_done = True
    
    waiter_thread = threading.Thread(target=_waiter, daemon=True)
    waiter_thread.start()
    
    # Main game loop
    clock = pygame.time.Clock()
    running = True
    frame_count = 0
    
    while running:
        frame_start = pygame.time.get_ticks()
        dt = clock.tick(60) / 1000.0  # Delta time in seconds
        
        # Process events from event bus (non-blocking)
        event_bus.process_events(max_events=100)
        
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                event_bus.emit(EventType.SHUTDOWN, source="main_loop")
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    running = False
                    event_bus.emit(EventType.SHUTDOWN, source="main_loop")
                else:
                    scene_manager.handle_event(event)
            else:
                scene_manager.handle_event(event)
        
        # Update and draw
        scene_manager.update(dt)
        scene_manager.draw()
        pygame.display.flip()
        
        # Update metrics every 60 frames
        frame_count += 1
        if frame_count % 60 == 0:
            fps = clock.get_fps()
            render_time = (pygame.time.get_ticks() - frame_start) / 1000.0
            app_state.update_fps(fps)
            app_state.update_render_time(render_time)
    
    # Cleanup
    print("\nShutting down...")
    audio_worker.stop()
    event_bus.shutdown()
    voice_engine.stop()
    
    # Print final metrics
    metrics = app_state.get_metrics()
    bus_metrics = event_bus.get_metrics()
    print(f"Final metrics: FPS={metrics['fps']}, Events processed={bus_metrics['events_processed']}")
    
    # Shutdown renderer (handles pygame.quit internally)
    renderer.shutdown()


if __name__ == "__main__":
    import signal
    import sys
    
    # Suppress cffi cairo errors on Ctrl+C
    def signal_handler(sig, frame):
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        main()
    except KeyboardInterrupt:
        pass
