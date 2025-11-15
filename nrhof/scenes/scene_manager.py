#!/usr/bin/env python3
import gc
from collections.abc import Callable

import pygame

from nrhof.core.mem_probe import get_memory_probe

from .scene_cache import SceneCache
from .scene_transitions import SceneTransition


class Scene:
    """Base class for all scenes."""

    def __init__(self, ctx):
        """Initialize scene with app context.

        Args:
            ctx: AppContext instance or SceneManager (for backward compatibility)
        """
        # Support both AppContext and direct SceneManager for backward compatibility
        if hasattr(ctx, "scene_manager"):
            # It's an AppContext
            self.ctx = ctx
            self.manager = ctx.scene_manager
        else:
            # It's a SceneManager (old style)
            self.manager = ctx
            self.ctx = None

        # Memory probe for leak detection
        self._mem_probe = get_memory_probe()
        self._scene_name = self.__class__.__name__

        # Track event subscription tokens for cleanup
        self._bus_tokens = []

        # Track surfaces/textures for cleanup
        self._cached_surfaces = []

        # Track per-scene data structures
        self._scene_caches = []

    def on_enter(self):
        """Called when scene becomes active."""
        # Optional: Take memory snapshot on enter (only if profiling enabled)
        import os

        if os.getenv("ENABLE_MEMORY_PROFILING", "0") == "1":
            self._mem_probe.snapshot(f"enter:{self._scene_name}")

    def on_exit(self):
        """Called when scene is about to be replaced.

        Performs aggressive cleanup:
        - Unsubscribes all event handlers
        - Deletes cached surfaces/textures
        - Clears per-scene data structures
        - Clears pygame event queue
        - Forces garbage collection
        """
        # Unsubscribe all event handlers using tokens
        if hasattr(self, "ctx") and self.ctx and hasattr(self.ctx, "event_bus"):
            for token in self._bus_tokens:
                try:
                    self.ctx.event_bus.unsubscribe_token(token)
                except Exception:
                    pass  # Handler may already be unsubscribed
        self._bus_tokens.clear()

        # Delete cached surfaces to free VRAM
        for surface in self._cached_surfaces:
            try:
                del surface
            except Exception:
                pass
        self._cached_surfaces.clear()

        # Clear per-scene caches
        for cache in self._scene_caches:
            try:
                if isinstance(cache, dict):
                    cache.clear()
                elif isinstance(cache, list):
                    cache.clear()
            except Exception:
                pass
        self._scene_caches.clear()

        # Clear pygame event queue to prevent stale events
        pygame.event.clear()

        # Evict global font and widget caches
        try:
            from nrhof.ui.components.now_playing import evict_now_playing_font_cache
            from nrhof.ui.components.timeclock import evict_timeclock_font_cache
            from nrhof.ui.fonts import evict_all_font_caches

            evict_all_font_caches()
            evict_timeclock_font_cache()
            evict_now_playing_font_cache()
        except Exception:
            pass  # Gracefully handle if imports fail

        # Optional: Force garbage collection and memory profiling
        # These operations can take 200-800ms and block the main thread
        # Only enable for debugging memory leaks
        import os

        if os.getenv("ENABLE_MEMORY_PROFILING", "0") == "1":
            # Force garbage collection (can take 100-500ms with large heaps)
            gc.collect()

            # Take memory snapshot on exit and compare (can take 100-300ms)
            self._mem_probe.snapshot(f"exit:{self._scene_name}")
            self._mem_probe.compare(
                f"enter:{self._scene_name}", f"exit:{self._scene_name}", top_n=15
            )

    def on_pause(self):
        """Called when scene is paused (backgrounded but not exited)."""
        pass

    def on_resume(self):
        """Called when scene is resumed (foregrounded after pause)."""
        pass

    def on_destroy(self):
        """Called when scene is being permanently destroyed."""
        pass

    def handle_event(self, event: pygame.event.Event):
        """Handle pygame events. Return True if event was handled."""
        return False

    def update(self, dt: float):
        """Update scene logic. dt is time since last frame in seconds."""
        pass

    def draw(self, screen: pygame.Surface):
        """Draw the scene to the screen."""
        pass

    # Helper methods for cleanup tracking
    def subscribe_event(self, event_type, handler):
        """Subscribe to an event and track token for automatic cleanup.

        Args:
            event_type: EventType to subscribe to
            handler: Handler function

        Returns:
            Subscription token

        Example:
            def my_handler(event):
                print(f"Got event: {event}")
            self.subscribe_event(EventType.LANGUAGE_CHANGED, my_handler)
        """
        if hasattr(self, "ctx") and self.ctx and hasattr(self.ctx, "event_bus"):
            token = self.ctx.event_bus.subscribe(event_type, handler)
            self._bus_tokens.append(token)
            return token
        return None

    def register_surface(self, surface: pygame.Surface):
        """Register a surface for automatic cleanup.

        Args:
            surface: Pygame surface to track
        """
        self._cached_surfaces.append(surface)

    def register_cache(self, cache: dict | list):
        """Register a cache (dict or list) for automatic cleanup.

        Args:
            cache: Dictionary or list to clear on exit
        """
        self._scene_caches.append(cache)

    def trigger_wakeword(self):
        """Trigger wakeword detection (helper method for all scenes)."""
        if self.ctx and self.ctx.voice_engine:
            self.ctx.voice_engine.trigger_wakeword()

    def handle_common_events(self, event: pygame.event.Event, back_intent, back_arrow_rect=None):
        """Handle common events across all scenes.

        Args:
            event: Pygame event to handle
            back_intent: Intent to emit when ESC is pressed or back arrow clicked
            back_arrow_rect: Optional pygame.Rect for back arrow click detection

        Returns:
            True if event was handled, False otherwise
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(back_intent)
                return True
            elif event.key == pygame.K_w:
                self.trigger_wakeword()
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if back_arrow_rect and back_arrow_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(back_intent)
                return True
        return False


class BaseAudioScene(Scene):
    """Base class for audio-reactive scenes using centralized audio source."""

    def __init__(self, ctx, sample_rate=44100, fft_size=1024):
        """Initialize audio scene.

        Args:
            ctx: AppContext instance
            sample_rate: Audio sample rate in Hz (for reference)
            fft_size: FFT buffer size
        """
        super().__init__(ctx)
        import numpy as np

        from nrhof.core.audio_io import get_mic_sample_rate

        self.sample_rate = get_mic_sample_rate()  # Use actual audio source sample rate
        self.fft_size = fft_size
        self.audio_buffer = np.zeros(self.fft_size)
        self.back_arrow_rect = None
        self.settings_rect = None  # Store settings text rect for click detection

    def start_audio_stream(self):
        """Start the audio input stream (now handled by audio_source)."""
        # Audio source initializes automatically on first get_audio_frame() call
        pass

    def stop_audio_stream(self):
        """Stop and clean up the audio input stream (handled by audio_source)."""
        # Cleanup handled by audio_source module
        pass

    def update_audio_buffer(self):
        """Update audio buffer from centralized audio source."""
        from nrhof.core.audio_io import get_mic_frame

        frame = get_mic_frame()
        if frame is not None:
            self.audio_buffer = frame

    def on_exit(self):
        """Clean up when leaving scene."""
        # Audio source cleanup handled automatically
        pass


class SceneManager:
    """Manages scene lifecycle and transitions."""

    def __init__(self, screen: pygame.Surface, config: dict):
        self.screen = screen
        self.config = config
        self.current_scene: Scene | None = None
        self.current_scene_name: str | None = None
        self._scene_history: list = []  # Navigation history stack

        # Use modular components
        self._cache = SceneCache()
        self._transition = SceneTransition(duration=0.4)

        # Backward compatibility - expose cache.scenes as self.scenes
        self.scenes = self._cache.scenes

        # Import lifecycle manager
        try:
            from nrhof.core.lifecycle import LifecyclePhase, get_lifecycle_manager  # noqa: F401

            self._lifecycle = get_lifecycle_manager()
            self._has_lifecycle = True
        except ImportError:
            self._lifecycle = None
            self._has_lifecycle = False

    def register_scene(self, name: str, scene: Scene):
        """Register a scene with a name."""
        self._cache.register(name, scene)

    def register_lazy(self, name: str, factory: Callable):
        """Register a lazy-loaded scene factory.

        Args:
            name: Scene name
            factory: Callable that returns a Scene instance when called
        """
        self._cache.register_lazy(name, factory)

    def _ensure_loaded(self, name: str):
        """Ensure a scene is loaded, instantiating from factory if needed.

        Args:
            name: Scene name to ensure is loaded
        """
        self._cache.ensure_loaded(name)

    def preload_lazy(
        self,
        names: list,
        progress_cb: Callable[[int, int], None] | None = None,
        sleep_between: float = 0.0,
    ):
        """Preload lazy scenes in a background thread.

        Args:
            names: List of scene names to preload
            progress_cb: Optional callback(done, total) called after each scene loads
            sleep_between: Optional delay between loading each scene

        Returns:
            Thread object (already started)
        """
        return self._cache.preload_lazy(names, progress_cb, sleep_between)

    def switch_to(
        self,
        name: str,
        add_to_history: bool = True,
        pause_current: bool = False,
        use_transition: bool = True,
    ):
        """Switch to a different scene by name with optional slide transition.

        Args:
            name: Scene name to switch to
            add_to_history: Whether to add current scene to history (default: True)
            pause_current: If True, pause current scene instead of exiting (default: False)
            use_transition: If True, use slide transition (default: True)
        """
        # Record scene transition for performance monitoring
        from nrhof.core.observability import get_performance_monitor

        perf_monitor = get_performance_monitor()
        from_scene = self.current_scene_name or "None"
        perf_monitor.record_scene_transition(from_scene, name)

        # Ensure scene is loaded (lazy loading)
        self._ensure_loaded(name)

        if name not in self.scenes:
            raise ValueError(f"Scene '{name}' not registered")

        # Skip if already transitioning
        if self._transition.active:
            print(f"\n[SWITCH BLOCKED] Tried to switch to {name} but transition is active\n")
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"[SWITCH] Blocked - transition active (tried to switch to {name})")
            return

        # Skip if trying to switch to the same scene (unless it's the first scene)
        if name == self.current_scene_name and self.current_scene is not None:
            return

        # Add current scene to history before switching (if requested)
        if add_to_history and self.current_scene_name and self.current_scene_name != name:
            self._scene_history.append(self.current_scene_name)

        # Determine transition direction (forward = 1, back = -1)
        is_going_back = not add_to_history
        transition_direction = -1 if is_going_back else 1

        if use_transition and self.current_scene:
            # Prepare to scene (don't call on_enter yet - do it after transition)
            to_scene = self._cache.resume(name)
            is_resumed = to_scene is not None
            if not to_scene:
                to_scene = self._cache.get(name)

            # Start slide transition immediately (before calling on_enter to avoid blocking)
            print(f"\n[TRANSITION START] {self.current_scene_name} -> {name}\n")
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"[SWITCH] Starting transition: {self.current_scene_name} -> {name}")
            self._transition.start(
                self.current_scene,
                self.current_scene_name,
                to_scene,
                name,
                transition_direction,
                self.screen.get_size(),
            )
            # Track whether scene was resumed (so we know not to call on_enter again)
            self._transition._is_resumed_scene = is_resumed

        else:
            # Instant switch (no transition)
            if self.current_scene:
                if pause_current:
                    # Pause current scene instead of exiting
                    if self._has_lifecycle:
                        from nrhof.core.lifecycle import LifecyclePhase

                        self._lifecycle.execute(
                            LifecyclePhase.SCENE_PAUSE,
                            scene_name=self.current_scene_name,
                            scene=self.current_scene,
                        )
                    self.current_scene.on_pause()
                    self._cache.pause(self.current_scene_name, self.current_scene)
                else:
                    # Exit current scene
                    if self._has_lifecycle:
                        from nrhof.core.lifecycle import LifecyclePhase

                        self._lifecycle.execute(
                            LifecyclePhase.SCENE_BEFORE_EXIT,
                            scene_name=self.current_scene_name,
                            scene=self.current_scene,
                        )
                    self.current_scene.on_exit()
                    if self._has_lifecycle:
                        self._lifecycle.execute(
                            LifecyclePhase.SCENE_AFTER_EXIT,
                            scene_name=self.current_scene_name,
                            scene=self.current_scene,
                        )

            # Check if resuming a paused scene
            resumed_scene = self._cache.resume(name)
            if resumed_scene:
                self.current_scene = resumed_scene
                if self._has_lifecycle:
                    from nrhof.core.lifecycle import LifecyclePhase

                    self._lifecycle.execute(
                        LifecyclePhase.SCENE_RESUME,
                        scene_name=name,
                        scene=self.current_scene,
                    )
                self.current_scene.on_resume()
            else:
                # Enter new scene
                self.current_scene = self._cache.get(name)
                if self._has_lifecycle:
                    from nrhof.core.lifecycle import LifecyclePhase

                    self._lifecycle.execute(
                        LifecyclePhase.SCENE_BEFORE_ENTER,
                        scene_name=name,
                        scene=self.current_scene,
                    )
                self.current_scene.on_enter()
                if self._has_lifecycle:
                    self._lifecycle.execute(
                        LifecyclePhase.SCENE_AFTER_ENTER,
                        scene_name=name,
                        scene=self.current_scene,
                    )

            self.current_scene_name = name

    def go_back(self):
        """Go back to the previous scene in history."""
        if self._scene_history:
            previous_scene = self._scene_history.pop()
            self.switch_to(
                previous_scene,
                add_to_history=False,
            )  # Don't add to history when going back
        else:
            # No history, go to menu as fallback
            self.switch_to("MenuScene", add_to_history=False)

    def handle_event(self, event: pygame.event.Event):
        """Pass event to current scene.

        Note: Events are blocked during transitions to prevent clicks
        from being ignored (since switch_to() is blocked during transitions).
        """
        # Debug logging for mouse clicks
        if event.type == pygame.MOUSEBUTTONDOWN:
            print(
                f"\n[CLICK DEBUG] button={event.button}, pos={event.pos}, transition={self._transition.active}, scene={self.current_scene_name}\n"
            )
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"[CLICK] button={event.button}, pos={event.pos}, "
                f"transition_active={self._transition.active}, "
                f"scene={self.current_scene_name if self.current_scene else 'None'}"
            )

        # Block events during transitions to prevent ignored clicks
        if self._transition.active:
            if event.type == pygame.MOUSEBUTTONDOWN:
                import logging

                logger = logging.getLogger(__name__)
                logger.info("[CLICK] Blocked - transition active")
            return False

        if self.current_scene:
            handled = self.current_scene.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                import logging

                logger = logging.getLogger(__name__)
                logger.info(f"[CLICK] Handled by scene: {handled}")
            return handled
        return False

    def update(self, dt: float):
        """Update current scene and handle transitions."""
        if self._transition.active:
            # Update both scenes during transition
            if self._transition.from_scene:
                self._transition.from_scene.update(dt)
            if self._transition.to_scene:
                self._transition.to_scene.update(dt)

            # Check if transition is complete
            if self._transition.update():
                self._finish_transition()
        elif self.current_scene:
            self.current_scene.update(dt)

    def _finish_transition(self):
        """Complete the transition and clean up."""
        # Exit/cleanup the from scene
        if self._transition.from_scene:
            if self._has_lifecycle:
                from nrhof.core.lifecycle import LifecyclePhase

                self._lifecycle.execute(
                    LifecyclePhase.SCENE_BEFORE_EXIT,
                    scene_name=self._transition.from_name,
                    scene=self._transition.from_scene,
                )
            self._transition.from_scene.on_exit()
            if self._has_lifecycle:
                self._lifecycle.execute(
                    LifecyclePhase.SCENE_AFTER_EXIT,
                    scene_name=self._transition.from_name,
                    scene=self._transition.from_scene,
                )

        # Set new current scene
        self.current_scene = self._transition.to_scene
        self.current_scene_name = self._transition.to_name

        # Call on_enter() NOW (after transition animation completes)
        # This prevents blocking the UI during the transition
        # Check if scene needs initialization (not resumed)
        if (
            not hasattr(self._transition, "_is_resumed_scene")
            or not self._transition._is_resumed_scene
        ):
            if self._has_lifecycle:
                from nrhof.core.lifecycle import LifecyclePhase

                self._lifecycle.execute(
                    LifecyclePhase.SCENE_BEFORE_ENTER,
                    scene_name=self.current_scene_name,
                    scene=self.current_scene,
                )
            self.current_scene.on_enter()
            if self._has_lifecycle:
                self._lifecycle.execute(
                    LifecyclePhase.SCENE_AFTER_ENTER,
                    scene_name=self.current_scene_name,
                    scene=self.current_scene,
                )

        # Complete transition (cleans up surfaces)
        print(f"\n[TRANSITION COMPLETE] Now in {self.current_scene_name}\n")
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"[SWITCH] Transition complete: now in {self.current_scene_name}")
        self._transition.complete()

    def draw(self):
        """Draw current scene with slide transition if active."""
        if self._transition.active:
            # Render transition
            self._transition.render(self.screen)
        elif self.current_scene:
            self.current_scene.draw(self.screen)

    def destroy_scene(self, name: str):
        """Permanently destroy a scene and free its resources.

        Args:
            name: Scene name to destroy
        """
        scene = self._cache.get(name)
        if scene:
            if self._has_lifecycle:
                from nrhof.core.lifecycle import LifecyclePhase

                self._lifecycle.execute(LifecyclePhase.SCENE_DESTROY, scene_name=name, scene=scene)
            scene.on_destroy()
            del self._cache.scenes[name]

        # Also remove from paused scenes if present
        if self._cache.is_paused(name):
            self._cache.resume(name)  # Remove from paused

    def cleanup_all(self):
        """Cleanup all scenes (called on app shutdown)."""
        # Destroy all scenes
        for name in list(self._cache.scenes.keys()):
            self.destroy_scene(name)

        # Clear cache
        self._cache.clear()
