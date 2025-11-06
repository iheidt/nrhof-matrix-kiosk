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
    
    def switch_to(self, name: str, add_to_history: bool = True):
        """Switch to a different scene by name.
        
        Args:
            name: Scene name to switch to
            add_to_history: Whether to add current scene to history (default: True)
        """
        # Ensure scene is loaded (lazy loading)
        self._ensure_loaded(name)
        
        if name not in self.scenes:
            raise ValueError(f"Scene '{name}' not registered")
        
        # Add current scene to history before switching (if requested)
        if add_to_history and self.current_scene_name and self.current_scene_name != name:
            self._scene_history.append(self.current_scene_name)
        
        if self.current_scene:
            self.current_scene.on_exit()
        
        self.current_scene = self.scenes[name]
        self.current_scene_name = name
        self.current_scene.on_enter()
    
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
        """Update current scene."""
        if self.current_scene:
            self.current_scene.update(dt)
    
    def draw(self):
        """Draw current scene."""
        if self.current_scene:
            self.current_scene.draw(self.screen)
