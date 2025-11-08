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
    start_preload,
    start_webflow_refresh,
    start_workers,
)
from core.config_loader import load_config
from core.event_bus import EventType
from core.localization import t
from core.mem_probe import start_trace
from core.observability import get_crash_guard, get_event_tap, get_performance_monitor

# Global state for Now Playing overlay
_now_playing_marquee = None
_last_track_id = None
_last_progress_time = None
_last_progress_ms = None

# Fade transition tracking
_playback_state_start_time = None
_is_in_playback_state = False
_fade_delay = 1.0  # Delay before starting fade to dim (seconds)
_fade_back_delay = 0.3  # Delay before fading back to primary (seconds)
_fade_duration = 1.0  # Fade duration (seconds) - increased for smoother transition


def draw_now_playing_overlay(screen: pygame.Surface, cfg: dict):
    """Draw Now Playing widget as a global overlay in top-right corner.

    Args:
        screen: Pygame surface to draw on
        cfg: Application config
    """
    import time

    from core.now_playing import get_now_playing_state
    from core.theme_loader import get_theme_loader
    from ui.components.widgets import MarqueeText, draw_now_playing

    global _now_playing_marquee, _last_track_id, _last_progress_time, _last_progress_ms
    global \
        _playback_state_start_time, \
        _is_in_playback_state, \
        _fade_delay, \
        _fade_duration, \
        _fade_back_delay

    # Get theme
    theme_loader = get_theme_loader()
    style = theme_loader.load_style("pipboy")

    # Position in top-right with 50px margins
    margin_top = 110
    margin_right = 40
    widget_width = 416

    screen_width = screen.get_width()
    x = screen_width - widget_width - margin_right  # Extends 39px more to the left
    y = margin_top

    # Get current track
    now_playing = get_now_playing_state()
    track = now_playing.get_track()

    # Determine title based on source
    if track:
        if track.source == "spotify":
            device = track.device_name if track.device_name else "unknown"
            device_formatted = (
                device.upper()
                .replace("-", ".")
                .replace("'", "")
                .replace("'", "")
                .replace("'", "")
                .replace(chr(8217), "")
            )
            now_playing_title = f"SPOTIFY . {device_formatted}"
        elif track.source == "sonos":
            room = track.sonos_room if track.sonos_room else "unknown"
            room_formatted = (
                room.upper()
                .replace("-", ".")
                .replace("'", "")
                .replace("'", "")
                .replace("'", "")
                .replace(chr(8217), "")
            )
            now_playing_title = f"SONOS . {room_formatted}"
        elif track.source == "vinyl":
            now_playing_title = "RECORD PLAYER"
        else:
            now_playing_title = "NOW PLAYING"

        # Truncate title
        if len(now_playing_title) > 22:
            now_playing_title = now_playing_title[:19] + "..."
    else:
        now_playing_title = "NOW PLAYING"

    # Format track info
    if track:
        artist = track.artist.lower() if track.artist else "unknown artist"
        title = track.title.lower() if track.title else "unknown song"
        song_line = f"{artist} • {title}"

        if track.source == "sonos" and track.sonos_room:
            album_line = f"{track.sonos_room.lower()}"
            if track.sonos_grouped_rooms:
                album_line += f" + {len(track.sonos_grouped_rooms)} more"
        else:
            album_line = track.album.lower() if track.album else f"via {track.source}"
    else:
        song_line = t("now_playing.listening")
        album_line = t("now_playing.none_playing")

    # Initialize marquee if needed
    max_text_width = widget_width - 40 - (24 * 2)
    if _now_playing_marquee is None:
        _now_playing_marquee = MarqueeText(song_line, max_text_width, scroll_speed=50.0, gap=100)

    # Get playback progress with client-side interpolation
    progress_ms = None
    duration_ms = None
    is_playing = False
    fade_amount = 0.0

    if track:
        duration_ms = track.duration_ms
        is_playing = track.is_playing

        track_id = f"{track.title}_{track.artist}_{track.source}"

        # Track change detection
        if track_id != _last_track_id:
            _last_track_id = track_id
            _last_progress_time = None
            _last_progress_ms = None
            if _now_playing_marquee:
                _now_playing_marquee.reset(song_line)

        # Progress interpolation
        if track.progress_ms is not None:
            current_time = time.time()

            if _last_progress_time is None:
                _last_progress_time = current_time
                _last_progress_ms = track.progress_ms

            time_delta = current_time - _last_progress_time

            if abs(track.progress_ms - _last_progress_ms) > 2000:
                _last_progress_ms = track.progress_ms
                _last_progress_time = current_time

            if is_playing:
                progress_ms = _last_progress_ms + int(time_delta * 1000)
            else:
                progress_ms = _last_progress_ms

            if duration_ms and progress_ms > duration_ms:
                progress_ms = duration_ms

        # Track playback state changes for fade transition
        current_time_fade = time.time()
        if is_playing and not _is_in_playback_state:
            # Just started playing
            _is_in_playback_state = True
            _playback_state_start_time = current_time_fade
        elif not is_playing and _is_in_playback_state:
            # Just stopped playing
            _is_in_playback_state = False
            _playback_state_start_time = current_time_fade

        # Calculate fade amount (0.0 = primary, 1.0 = dim)
        if _playback_state_start_time is not None:
            elapsed = current_time_fade - _playback_state_start_time

            if is_playing:
                # Fading to dim (playing state)
                if elapsed < _fade_delay:
                    # Still in delay period, stay at primary
                    fade_amount = 0.0
                else:
                    # Fade from primary to dim
                    fade_progress = min(1.0, (elapsed - _fade_delay) / _fade_duration)
                    fade_amount = fade_progress
            else:
                # Fading back to primary (stopped state) - with delay for smoother transition
                if elapsed < _fade_back_delay:
                    # Stay at dim during delay period
                    fade_amount = 1.0
                else:
                    # Fade from dim back to primary
                    fade_progress = min(1.0, (elapsed - _fade_back_delay) / _fade_duration)
                    fade_amount = 1.0 - fade_progress  # Reverse: 1.0 -> 0.0
    else:
        # No track - trigger fade back to primary if we were in playback state
        if _is_in_playback_state:
            _is_in_playback_state = False
            _playback_state_start_time = time.time()
        elif _playback_state_start_time is not None:
            # Continue fade animation with delay
            elapsed = time.time() - _playback_state_start_time
            if elapsed < _fade_back_delay:
                # Stay at dim during delay period
                fade_amount = 1.0
            else:
                # Fade from dim back to primary
                fade_progress = min(1.0, (elapsed - _fade_back_delay) / _fade_duration)
                fade_amount = 1.0 - fade_progress

            # Reset state after fade completes
            if elapsed >= (_fade_back_delay + _fade_duration):
                _playback_state_start_time = None

    # Draw the widget
    draw_now_playing(
        surface=screen,
        x=x,
        y=y,
        width=widget_width,
        title=now_playing_title,
        line1=song_line,
        line2=album_line,
        theme={"style": style},
        marquee=_now_playing_marquee,
        progress_ms=progress_ms,
        duration_ms=duration_ms,
        is_playing=is_playing,
        fade_amount=fade_amount,
    )

    # Update global state (required for persistence across frames)
    # Note: The global keyword at the top allows us to modify these
    # but we need to be explicit about the updates


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

    # Localization hook - log language changes
    def on_language_change(old_lang, new_lang):
        print(f"[LOCALIZATION] Language changed: {old_lang} -> {new_lang}")

    from core.localization import add_language_change_listener

    add_language_change_listener(on_language_change)

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

    # Execute APP_SHUTDOWN hooks
    execute_hooks(LifecyclePhase.APP_SHUTDOWN, components=components, workers=workers)

    # Stop workers
    for worker in workers.values():
        if hasattr(worker, "stop"):
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
