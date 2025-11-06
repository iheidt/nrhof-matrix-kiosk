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
    # Initialize lifecycle manager
    from core.lifecycle import get_lifecycle_manager, LifecyclePhase, execute_hooks, register_hook
    lifecycle = get_lifecycle_manager()
    
    # Register test hooks to verify lifecycle system
    register_hook(
        LifecyclePhase.APP_STARTUP,
        "log_startup",
        lambda ctx: print("[LIFECYCLE] App starting up..."),
        priority=100
    )
    
    register_hook(
        LifecyclePhase.APP_READY,
        "log_ready",
        lambda ctx: print(f"[LIFECYCLE] App ready! Components: {list(ctx['components'].keys())}"),
        priority=100
    )
    
    register_hook(
        LifecyclePhase.APP_PRE_FRAME,
        "log_first_frame",
        lambda ctx: print(f"[LIFECYCLE] First frame at {ctx.timestamp:.2f}"),
        priority=100,
        once=True  # Only log first frame
    )
    
    register_hook(
        LifecyclePhase.APP_SHUTDOWN,
        "log_shutdown",
        lambda ctx: print(f"[LIFECYCLE] App shutting down. Workers: {list(ctx['workers'].keys())}"),
        priority=100
    )
    
    # Worker lifecycle hooks
    register_hook(
        LifecyclePhase.WORKER_START,
        "log_worker_start",
        lambda ctx: print(f"[LIFECYCLE] Worker starting: {ctx['worker_name']}"),
        priority=50
    )
    
    register_hook(
        LifecyclePhase.WORKER_STOP,
        "log_worker_stop",
        lambda ctx: print(f"[LIFECYCLE] Worker stopping: {ctx['worker_name']}"),
        priority=50
    )
    
    # Execute APP_STARTUP hooks
    execute_hooks(LifecyclePhase.APP_STARTUP)
    
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
    
    # Execute APP_READY hooks
    execute_hooks(LifecyclePhase.APP_READY, 
                 components=components,
                 config=cfg.to_dict())
    
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
        
        # Execute PRE_FRAME hooks
        execute_hooks(LifecyclePhase.APP_PRE_FRAME, dt=dt, frame_count=frame_count)
        
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
        
        # Execute POST_FRAME hooks
        execute_hooks(LifecyclePhase.APP_POST_FRAME, dt=dt, frame_count=frame_count)
    
    # Cleanup
    print("\nShutting down...")
    
    # Execute APP_SHUTDOWN hooks
    execute_hooks(LifecyclePhase.APP_SHUTDOWN, 
                 components=components,
                 workers=workers)
    
    # Stop workers
    for worker in workers.values():
        if hasattr(worker, 'stop'):
            worker.stop()
    
    # Cleanup scenes
    scene_manager.cleanup_all()
    
    # Shutdown services
    event_bus.shutdown()
    voice_engine.stop()
    
    # Print final metrics
    metrics = app_state.get_metrics()
    bus_metrics = event_bus.get_metrics()
    lifecycle_metrics = lifecycle.get_metrics()
    print(f"Final metrics: FPS={metrics['fps']}, Events processed={bus_metrics['events_processed']}")
    print(f"Lifecycle: Hooks executed={lifecycle_metrics['hooks_executed']}")
    
    # Execute APP_CLEANUP hooks
    execute_hooks(LifecyclePhase.APP_CLEANUP)
    
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
