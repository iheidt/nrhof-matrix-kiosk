#!/usr/bin/env python3
import sys
import pygame

# Import version
from __version__ import __version__

# Load environment variables from .env if python-dotenv is available
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from core.config_loader import load_config
from core.event_bus import EventType
from core.app_initializer import (
    parse_arguments,
    apply_cli_overrides,
    initialize_renderer,
    initialize_fonts,
    create_app_components,
    start_workers,
    register_all_handlers,
    start_preload
)

def main():
    # Parse arguments and load config
    args = parse_arguments()
    cfg = load_config()
    
    # Initialize localization
    from core import localization
    lang = cfg.get('localization.language', 'en')
    localization.set_language(lang)
    
    # Apply CLI overrides
    apply_cli_overrides(cfg, args)
    
    # Initialize renderer and get logger
    renderer, screen, logger = initialize_renderer(cfg)
    logger.info("glow plugs engaging on NRHOF", version=__version__)
    
    # Initialize fonts
    initialize_fonts(cfg, logger)
    
    # Create all app components
    components = create_app_components(cfg, screen)
    
    # Register all handlers
    register_all_handlers(components)
    
    # Start workers (pass voice_engine for wake word callback)
    workers = start_workers(cfg, components['voice_engine'])
    
    # Start voice engine
    components['voice_engine'].start()
    
    # Start with splash screen
    components['scene_manager'].switch_to("SplashScene")
    
    # Start background preload
    start_preload(components['scene_manager'], components['app_context'])
    
    # Main game loop
    scene_manager = components['scene_manager']
    event_bus = components['event_bus']
    app_state = components['app_state']
    voice_engine = components['voice_engine']
    
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
    for worker in workers.values():
        if hasattr(worker, 'stop'):
            worker.stop()
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
