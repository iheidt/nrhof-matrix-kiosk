#!/usr/bin/env python3
import sys
import time

import pygame

# Import version
from __version__ import __version__

# Load environment variables from .env if python-dotenv is available
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

from core.app_initializer import (
    apply_cli_overrides,
    create_app_components,
    initialize_fonts,
    initialize_renderer,
    parse_arguments,
    register_all_handlers,
    start_workers,
)
from core.config_loader import load_config
from core.event_bus import EventType, get_event_bus
from core.mem_probe import start_trace
from core.observability import get_crash_guard, get_event_tap, get_performance_monitor
from core.preload_manager import start_3d_renderer_preload, start_preload, start_webflow_refresh
from overlays import draw_now_playing_overlay


def main():
    # Initialize lifecycle manager
    from core.lifecycle import LifecyclePhase, execute_hooks, get_lifecycle_manager, register_hook

    lifecycle = get_lifecycle_manager()

    # Register test hooks to verify lifecycle system
    register_hook(
        LifecyclePhase.APP_STARTUP,
        "log_startup",
        lambda ctx: print("[LIFECYCLE] App starting up..."),
        priority=100,
    )

    register_hook(
        LifecyclePhase.APP_READY,
        "log_ready",
        lambda ctx: print(f"[LIFECYCLE] App ready! Components: {list(ctx['components'].keys())}"),
        priority=100,
    )

    register_hook(
        LifecyclePhase.APP_PRE_FRAME,
        "log_first_frame",
        lambda ctx: print(f"[LIFECYCLE] First frame at {ctx.timestamp:.2f}"),
        priority=100,
        once=True,  # Only log first frame
    )

    register_hook(
        LifecyclePhase.APP_SHUTDOWN,
        "log_shutdown",
        lambda ctx: print(f"[LIFECYCLE] App shutting down. Workers: {list(ctx['workers'].keys())}"),
        priority=100,
    )

    # Worker lifecycle hooks
    register_hook(
        LifecyclePhase.WORKER_START,
        "log_worker_start",
        lambda ctx: print(f"[LIFECYCLE] Worker starting: {ctx['worker_name']}"),
        priority=50,
    )

    register_hook(
        LifecyclePhase.WORKER_STOP,
        "log_worker_stop",
        lambda ctx: print(f"[LIFECYCLE] Worker stopping: {ctx['worker_name']}"),
        priority=50,
    )

    # Localization logging is handled in core/localization/service.py

    # Execute APP_STARTUP hooks
    execute_hooks(LifecyclePhase.APP_STARTUP)

    # Parse arguments and load config
    args = parse_arguments()
    cfg = load_config()

    # Initialize localization
    from core import localization

    lang = cfg.get("localization.language", "en")
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
    workers = start_workers(cfg, components["voice_engine"])

    # Start voice engine
    components["voice_engine"].start()

    # Start with splash screen (no transition on app start)
    components["scene_manager"].switch_to("SplashScene", use_transition=False)

    # Start 3D renderer preload in background (for MenuScene D20)
    start_3d_renderer_preload()

    # Start background preload
    start_preload(components["scene_manager"], components["app_context"])

    # Start Webflow cache refresh in background
    if components.get("webflow_cache_manager"):
        start_webflow_refresh(components["webflow_cache_manager"])

    # Execute APP_READY hooks
    execute_hooks(LifecyclePhase.APP_READY, components=components, config=cfg)

    # Start memory tracing for leak detection (only if profiling enabled)
    import os

    if os.getenv("ENABLE_MEMORY_PROFILING", "0") == "1":
        start_trace()

    # Enable event debugging if requested
    if args.debug_events:
        event_tap = get_event_tap()
        event_tap.enable()

        # Subscribe to all events for debugging
        def debug_handler(event):
            event_tap.tap(event.type.value, event.payload, event.source)

        for event_type in EventType:
            components["event_bus"].subscribe(event_type, debug_handler)

    # Main game loop
    scene_manager = components["scene_manager"]
    event_bus = components["event_bus"]
    app_state = components["app_state"]
    voice_engine = components["voice_engine"]

    clock = pygame.time.Clock()
    running = True
    frame_count = 0
    last_gc_time = time.time()  # Track last GC time for periodic cleanup

    # Wrap main loop in crash guard
    crash_guard = get_crash_guard()
    perf_monitor = get_performance_monitor()
    try:
        while running:
            frame_start = pygame.time.get_ticks()
            dt = clock.tick(60) / 1000.0  # Delta time in seconds

            # Record frame time for performance monitoring
            perf_monitor.record_frame_time(dt)

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

            # Draw global overlays (z-index +1)
            draw_now_playing_overlay(screen, cfg)

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

            # Periodic lightweight garbage collection (every 5 seconds)
            # This prevents heap bloat without blocking scene transitions
            current_time = time.time()
            if current_time - last_gc_time > 5.0:
                import gc

                gc.collect(generation=0)  # Only collect youngest generation (fast)
                last_gc_time = current_time

    # Cleanup
    except Exception as exc:
        # Write crash report
        crash_file = crash_guard.write_crash_report(type(exc), exc, exc.__traceback__)

        # Re-raise in dev mode
        import os

        if os.getenv("DEV_MODE", "1") == "1":
            raise
        else:
            print(f"Fatal error. See {crash_file} for details.")
            sys.exit(1)

    print("\nShutting down...")

    # Emit SHUTDOWN event - all workers subscribed to this will auto-stop
    event_bus = get_event_bus()
    event_bus.emit(EventType.SHUTDOWN, source="main")

    # Execute APP_SHUTDOWN hooks
    execute_hooks(LifecyclePhase.APP_SHUTDOWN, components=components, workers=workers)

    # Give workers a moment to process SHUTDOWN event and stop gracefully
    time.sleep(0.5)

    # Join worker threads (they should already be stopping)
    for worker in workers.values():
        if hasattr(worker, "_thread") and worker._thread:
            worker._thread.join(timeout=2.0)

    # Cleanup scenes
    scene_manager.cleanup_all()

    # Shutdown services
    event_bus.shutdown()
    voice_engine.stop()

    # Print final metrics
    metrics = app_state.get_metrics()
    bus_metrics = event_bus.get_metrics()
    lifecycle_metrics = lifecycle.get_metrics()
    print(
        f"Final metrics: FPS={metrics['fps']}, Events processed={bus_metrics['events_processed']}",
    )
    print(f"Lifecycle: Hooks executed={lifecycle_metrics['hooks_executed']}")

    # Print performance report
    print("\n" + perf_monitor.get_report())

    # Execute APP_CLEANUP hooks
    execute_hooks(LifecyclePhase.APP_CLEANUP)

    # Shutdown renderer (handles pygame.quit internally)
    renderer.shutdown()


if __name__ == "__main__":
    import signal

    # Suppress cffi cairo errors on Ctrl+C
    def signal_handler(sig, frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except KeyboardInterrupt:
        pass
