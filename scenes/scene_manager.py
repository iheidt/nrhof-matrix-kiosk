#!/usr/bin/env python3
import pygame
import threading
import time
from typing import Dict, Optional, Type, Callable


# Global scene registry
_scene_registry: Dict[str, Type['Scene']] = {}


def register_scene(name: str):
    """Decorator to automatically register a scene class.
    
    Args:
        name: Name to register the scene under
        
    Returns:
        Decorator function
        
    Example:
        @register_scene("IntroScene")
        class IntroScene(Scene):
            pass
    """
    def decorator(cls: Type[Scene]) -> Type[Scene]:
        _scene_registry[name] = cls
        return cls
    return decorator


def get_registered_scenes() -> Dict[str, Type['Scene']]:
    """Get all registered scene classes.
    
    Returns:
        Dictionary mapping scene names to scene classes
    """
    return _scene_registry.copy()


class Scene:
    """Base class for all scenes."""
    
    def __init__(self, ctx):
        """Initialize scene with app context.
        
        Args:
            ctx: AppContext instance or SceneManager (for backward compatibility)
        """
        # Support both AppContext and direct SceneManager for backward compatibility
        if hasattr(ctx, 'scene_manager'):
            # It's an AppContext
            self.ctx = ctx
            self.manager = ctx.scene_manager
        else:
            # It's a SceneManager (old style)
            self.manager = ctx
            self.ctx = None
    
    def on_enter(self):
        """Called when scene becomes active."""
        pass
    
    def on_exit(self):
        """Called when scene is about to be replaced."""
        pass
    
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
        from audio_source import get_sample_rate
        
        self.sample_rate = get_sample_rate()  # Use actual audio source sample rate
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
        from audio_source import get_audio_frame
        self.audio_buffer = get_audio_frame(length=self.fft_size)
    
    def on_exit(self):
        """Clean up when leaving scene."""
        # Audio source cleanup handled automatically
        pass



class SceneManager:
    """Manages scene lifecycle and transitions."""
    
    def __init__(self, screen: pygame.Surface, config: dict):
        self.screen = screen
        self.config = config
        self.scenes: Dict[str, Scene] = {}
        self.current_scene: Optional[Scene] = None
        self.current_scene_name: Optional[str] = None
        self._lazy_factories: Dict[str, Callable] = {}  # Lazy loading factories
        self._scene_history: list = []  # Navigation history stack
        self._paused_scenes: Dict[str, Scene] = {}  # Scenes that are paused but not destroyed
        
        # Slide transition state
        self._transition_active = False
        self._transition_progress = 0.0  # 0.0 to 1.0
        self._transition_duration = 0.4  # seconds (adjust for speed)
        self._transition_start_time = 0.0
        self._transition_from_scene: Optional[Scene] = None
        self._transition_from_name: Optional[str] = None
        self._transition_to_scene: Optional[Scene] = None
        self._transition_to_name: Optional[str] = None
        self._transition_direction = 1  # 1 = left to right (forward), -1 = right to left (back)
        
        # Offscreen surfaces for smooth transitions
        self._from_surface: Optional[pygame.Surface] = None
        self._to_surface: Optional[pygame.Surface] = None
        
        # Import lifecycle manager
        try:
            from core.lifecycle import get_lifecycle_manager, LifecyclePhase
            self._lifecycle = get_lifecycle_manager()
            self._has_lifecycle = True
        except ImportError:
            self._lifecycle = None
            self._has_lifecycle = False
    
    def register_scene(self, name: str, scene: Scene):
        """Register a scene with a name."""
        self.scenes[name] = scene
    
    def register_lazy(self, name: str, factory: Callable):
        """Register a lazy-loaded scene factory.
        
        Args:
            name: Scene name
            factory: Callable that returns a Scene instance when called
        """
        self._lazy_factories[name] = factory
    
    def _ease_out_cubic(self, t: float) -> float:
        """Cubic easing out - decelerating to zero velocity.
        
        Args:
            t: Progress from 0.0 to 1.0
            
        Returns:
            Eased value from 0.0 to 1.0
        """
        return 1 - pow(1 - t, 3)
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """Cubic easing in/out - acceleration until halfway, then deceleration.
        
        Args:
            t: Progress from 0.0 to 1.0
            
        Returns:
            Eased value from 0.0 to 1.0
        """
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
    
    def _ensure_loaded(self, name: str):
        """Ensure a scene is loaded, instantiating from factory if needed.
        
        Args:
            name: Scene name to ensure is loaded
        """
        # Already loaded
        if name in self.scenes:
            return
        
        # Load from lazy factory
        if name in self._lazy_factories:
            factory = self._lazy_factories[name]
            scene = factory()
            self.register_scene(name, scene)
            return
        
        # Not found anywhere - will raise error in switch_to
    
    def preload_lazy(self, names: list, progress_cb: Optional[Callable[[int, int], None]] = None, sleep_between: float = 0.0) -> threading.Thread:
        """Preload lazy scenes in a background thread.
        
        Args:
            names: List of scene names to preload
            progress_cb: Optional callback(done, total) called after each scene loads
            sleep_between: Optional delay between loading each scene
            
        Returns:
            Thread object (already started)
        """
        def _preload_worker():
            total = len(names)
            for i, name in enumerate(names):
                self._ensure_loaded(name)
                if progress_cb:
                    progress_cb(i + 1, total)
                if sleep_between > 0:
                    time.sleep(sleep_between)
        
        thread = threading.Thread(target=_preload_worker, daemon=True)
        thread.start()
        return thread
    
    def switch_to(self, name: str, add_to_history: bool = True, pause_current: bool = False, use_transition: bool = True):
        """Switch to a different scene by name with optional slide transition.
        
        Args:
            name: Scene name to switch to
            add_to_history: Whether to add current scene to history (default: True)
            pause_current: If True, pause current scene instead of exiting (default: False)
            use_transition: If True, use slide transition (default: True)
        """
        # Ensure scene is loaded (lazy loading)
        self._ensure_loaded(name)
        
        if name not in self.scenes:
            raise ValueError(f"Scene '{name}' not registered")
        
        # Skip if already transitioning
        if self._transition_active:
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
            # Start slide transition
            self._transition_active = True
            self._transition_progress = 0.0
            self._transition_start_time = time.time()
            self._transition_direction = transition_direction
            
            # Store from scene
            self._transition_from_scene = self.current_scene
            self._transition_from_name = self.current_scene_name
            
            # Prepare to scene
            if name in self._paused_scenes:
                self._transition_to_scene = self._paused_scenes.pop(name)
            else:
                self._transition_to_scene = self.scenes[name]
                # Call on_enter for new scene
                if self._has_lifecycle:
                    from core.lifecycle import LifecyclePhase
                    self._lifecycle.execute(LifecyclePhase.SCENE_BEFORE_ENTER, 
                                          scene_name=name,
                                          scene=self._transition_to_scene)
                self._transition_to_scene.on_enter()
                if self._has_lifecycle:
                    self._lifecycle.execute(LifecyclePhase.SCENE_AFTER_ENTER, 
                                          scene_name=name,
                                          scene=self._transition_to_scene)
            
            self._transition_to_name = name
            
            # Create offscreen surfaces for smooth rendering
            screen_size = self.screen.get_size()
            self._from_surface = pygame.Surface(screen_size)
            self._to_surface = pygame.Surface(screen_size)
            
        else:
            # Instant switch (no transition)
            if self.current_scene:
                if pause_current:
                    # Pause current scene instead of exiting
                    if self._has_lifecycle:
                        from core.lifecycle import LifecyclePhase
                        self._lifecycle.execute(LifecyclePhase.SCENE_PAUSE, 
                                              scene_name=self.current_scene_name,
                                              scene=self.current_scene)
                    self.current_scene.on_pause()
                    self._paused_scenes[self.current_scene_name] = self.current_scene
                else:
                    # Exit current scene
                    if self._has_lifecycle:
                        from core.lifecycle import LifecyclePhase
                        self._lifecycle.execute(LifecyclePhase.SCENE_BEFORE_EXIT, 
                                              scene_name=self.current_scene_name,
                                              scene=self.current_scene)
                    self.current_scene.on_exit()
                    if self._has_lifecycle:
                        self._lifecycle.execute(LifecyclePhase.SCENE_AFTER_EXIT, 
                                              scene_name=self.current_scene_name,
                                              scene=self.current_scene)
            
            # Check if resuming a paused scene
            if name in self._paused_scenes:
                self.current_scene = self._paused_scenes.pop(name)
                if self._has_lifecycle:
                    from core.lifecycle import LifecyclePhase
                    self._lifecycle.execute(LifecyclePhase.SCENE_RESUME, 
                                          scene_name=name,
                                          scene=self.current_scene)
                self.current_scene.on_resume()
            else:
                # Enter new scene
                self.current_scene = self.scenes[name]
                if self._has_lifecycle:
                    from core.lifecycle import LifecyclePhase
                    self._lifecycle.execute(LifecyclePhase.SCENE_BEFORE_ENTER, 
                                          scene_name=name,
                                          scene=self.current_scene)
                self.current_scene.on_enter()
                if self._has_lifecycle:
                    self._lifecycle.execute(LifecyclePhase.SCENE_AFTER_ENTER, 
                                          scene_name=name,
                                          scene=self.current_scene)
            
            self.current_scene_name = name
    
    def go_back(self):
        """Go back to the previous scene in history."""
        if self._scene_history:
            previous_scene = self._scene_history.pop()
            self.switch_to(previous_scene, add_to_history=False)  # Don't add to history when going back
        else:
            # No history, go to menu as fallback
            self.switch_to("MenuScene", add_to_history=False)
    
    def handle_event(self, event: pygame.event.Event):
        """Pass event to current scene."""
        if self.current_scene:
            return self.current_scene.handle_event(event)
        return False
    
    def update(self, dt: float):
        """Update current scene and handle transitions."""
        if self._transition_active:
            # Update transition progress
            elapsed = time.time() - self._transition_start_time
            self._transition_progress = min(1.0, elapsed / self._transition_duration)
            
            # Update both scenes during transition
            if self._transition_from_scene:
                self._transition_from_scene.update(dt)
            if self._transition_to_scene:
                self._transition_to_scene.update(dt)
            
            # Check if transition is complete
            if self._transition_progress >= 1.0:
                self._finish_transition()
        elif self.current_scene:
            self.current_scene.update(dt)
    
    def _finish_transition(self):
        """Complete the transition and clean up."""
        # Exit/cleanup the from scene
        if self._transition_from_scene:
            if self._has_lifecycle:
                from core.lifecycle import LifecyclePhase
                self._lifecycle.execute(LifecyclePhase.SCENE_BEFORE_EXIT, 
                                      scene_name=self._transition_from_name,
                                      scene=self._transition_from_scene)
            self._transition_from_scene.on_exit()
            if self._has_lifecycle:
                self._lifecycle.execute(LifecyclePhase.SCENE_AFTER_EXIT, 
                                      scene_name=self._transition_from_name,
                                      scene=self._transition_from_scene)
        
        # Set new current scene
        self.current_scene = self._transition_to_scene
        self.current_scene_name = self._transition_to_name
        
        # Reset transition state
        self._transition_active = False
        self._transition_progress = 0.0
        self._transition_from_scene = None
        self._transition_from_name = None
        self._transition_to_scene = None
        self._transition_to_name = None
        
        # Explicitly delete transition surfaces to free memory immediately
        if self._from_surface is not None:
            del self._from_surface
            self._from_surface = None
        if self._to_surface is not None:
            del self._to_surface
            self._to_surface = None
    
    def draw(self):
        """Draw current scene with slide transition if active."""
        if self._transition_active:
            # Apply easing to progress
            eased_progress = self._ease_in_out_cubic(self._transition_progress)
            
            # Render both scenes to offscreen surfaces
            if self._transition_from_scene and self._from_surface:
                self._transition_from_scene.draw(self._from_surface)
            if self._transition_to_scene and self._to_surface:
                self._transition_to_scene.draw(self._to_surface)
            
            # Calculate slide positions
            screen_width = self.screen.get_width()
            
            if self._transition_direction == 1:
                # Forward: from slides left, to slides in from right
                from_x = int(-screen_width * eased_progress)
                to_x = int(screen_width * (1.0 - eased_progress))
            else:
                # Back: from slides right, to slides in from left
                from_x = int(screen_width * eased_progress)
                to_x = int(-screen_width * (1.0 - eased_progress))
            
            # Draw both scenes at their slide positions
            if self._from_surface:
                self.screen.blit(self._from_surface, (from_x, 0))
            if self._to_surface:
                self.screen.blit(self._to_surface, (to_x, 0))
        elif self.current_scene:
            self.current_scene.draw(self.screen)
    
    def destroy_scene(self, name: str):
        """Permanently destroy a scene and free its resources.
        
        Args:
            name: Scene name to destroy
        """
        if name in self.scenes:
            scene = self.scenes[name]
            if self._has_lifecycle:
                from core.lifecycle import LifecyclePhase
                self._lifecycle.execute(LifecyclePhase.SCENE_DESTROY, 
                                      scene_name=name,
                                      scene=scene)
            scene.on_destroy()
            del self.scenes[name]
        
        # Also remove from paused scenes if present
        if name in self._paused_scenes:
            del self._paused_scenes[name]
    
    def cleanup_all(self):
        """Cleanup all scenes (called on app shutdown)."""
        # Destroy all scenes
        for name in list(self.scenes.keys()):
            self.destroy_scene(name)
        
        # Clear paused scenes
        self._paused_scenes.clear()
