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


class BaseHubScene(Scene):
    """Base class for hub menu scenes with sub-experience selection."""
    
    def __init__(self, ctx, title=None, items=None, back_intent=None, content_name=None):
        """Initialize hub scene.
        
        Args:
            ctx: AppContext instance
            title: Title text (deprecated, use content_name)
            items: Menu items (deprecated, use content_name)
            back_intent: Intent to emit when going back
            content_name: Name of content file (e.g., 'experience1_hub')
        """
        super().__init__(ctx)
        
        # Load theme if content_name provided
        if content_name:
            from theme_loader import get_theme_loader
            self.theme_loader = get_theme_loader()
            self.theme = self.theme_loader.load_theme(content_name, theme_name='pipboy')
            # Also load shared hub layout
            self.hub_layout = self.theme_loader.load_layout('hub')
            
            self.title = self.theme['content']['title']
            self.subtitle = self.theme['content'].get('subtitle', '')
            self.items = self.theme['content']['items']
            self.color = tuple(self.theme['style']['colors']['primary'])
            self.bg = tuple(self.theme['style']['colors']['background'])
        else:
            # Backward compatibility
            self.theme_loader = None
            self.theme = None
            self.hub_layout = None
            self.title = title or ""
            self.subtitle = ""
            self.items = items or []
            self.color = (140, 255, 140)
            self.bg = (0, 0, 0)
        
        self.back_intent = back_intent
        self.selected_index = 0
        self.back_arrow_rect = None
    
    def on_enter(self):
        """Initialize hub scene."""
        # Color already loaded from theme or backward compatibility in __init__
        self.selected_index = 0
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(self.back_intent)
                return True
            elif event.key == pygame.K_w:
                self.trigger_wakeword()
                return True
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self._select_item(0)
                return True
            elif event.key in (pygame.K_2, pygame.K_KP2):
                if len(self.items) > 1:
                    self._select_item(1)
                return True
            elif event.key in (pygame.K_3, pygame.K_KP3):
                if len(self.items) > 2:
                    self._select_item(2)
                return True
            elif event.key == pygame.K_RETURN:
                self._select_item(self.selected_index)
                return True
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(self.items)
                return True
            elif event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.items)
                return True
        
        # Mouse/touch selection
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # Check if click is on back arrow
            if self.back_arrow_rect and self.back_arrow_rect.collidepoint(mx, my):
                self.ctx.intent_router.emit(self.back_intent)
                return True
            
            # Check if click is on an item (matching draw layout)
            from utils import MARGIN_TOP, MARGIN_LEFT, HUB_MENU_START_Y_OFFSET, HUB_MENU_LINE_HEIGHT
            w, h = self.manager.screen.get_size()
            start_y = MARGIN_TOP + HUB_MENU_START_Y_OFFSET
            
            for i, item in enumerate(self.items):
                y = start_y + i * HUB_MENU_LINE_HEIGHT
                item_rect = pygame.Rect(MARGIN_LEFT, y - 5, int(w * 0.6), HUB_MENU_LINE_HEIGHT)
                if item_rect.collidepoint(mx, my):
                    self._select_item(i)
                    return True
        
        return False
    
    def _select_item(self, index: int):
        """Select a sub-experience by index."""
        from intent_router import Intents
        if 0 <= index < len(self.items):
            item = self.items[index]
            self.ctx.intent_router.emit(Intents.SELECT_SUB_EXPERIENCE, id=item["id"])
    
    def update(self, dt: float):
        """Update hub state."""
        pass
    
    def draw(self, screen: pygame.Surface):
        """Draw the ASCII-style hub menu."""
        from utils import get_font, draw_back_arrow
        
        screen.fill(self.bg)
        w, h = screen.get_size()
        
        # Use theme layout if available, otherwise fall back to constants
        if self.hub_layout:
            layout = self.hub_layout
            style = self.theme['style']
            
            # Draw back arrow
            self.back_arrow_rect = draw_back_arrow(screen, tuple(style['colors']['primary']))
            
            # Title
            title_layout = layout['title']
            title_pos = self.theme_loader.resolve_position(title_layout['position'], (w, h))
            title_font = get_font(title_layout['font_size'])
            title_surface = title_font.render(self.title, True, tuple(style['colors']['primary']))
            screen.blit(title_surface, title_pos)
            
            # Subtitle
            if self.subtitle:
                subtitle_layout = layout['subtitle']
                subtitle_pos = self.theme_loader.resolve_position(subtitle_layout['position'], (w, h))
                subtitle_font = get_font(subtitle_layout['font_size'])
                subtitle_surface = subtitle_font.render(self.subtitle, True, tuple(style['colors']['secondary']))
                screen.blit(subtitle_surface, subtitle_pos)
            
            # Menu items
            items_layout = layout['items']
            start_y = items_layout['start_y']
            line_height = items_layout['line_height']
            item_font = get_font(items_layout['font_size'])
            
            for i, item in enumerate(self.items):
                if i == self.selected_index:
                    prefix = "> "
                    color = tuple(style['colors']['primary'])
                else:
                    prefix = "  "
                    color = tuple(style['colors']['dim'])
                
                text = item_font.render(f"{prefix}{item['label']}", True, color)
                screen.blit(text, (items_layout['indent'], start_y + i * line_height))
            
            # Footer for themed layout
            from utils import dim_color, draw_scanlines, draw_footer
            help_font = get_font(18)
            help_text = "press 1-3, arrow keys + enter, click, or use voice"
            help_surface = help_font.render(help_text, True, dim_color(tuple(style['colors']['primary']), 0.33))
            screen.blit(help_surface, (80, h - 100))
            
            esc_text = "esc: return to main menu"
            esc_surface = help_font.render(esc_text, True, dim_color(tuple(style['colors']['primary']), 0.33))
            screen.blit(esc_surface, (80, h - 75))
            
            draw_scanlines(screen)
            draw_footer(screen, tuple(style['colors']['primary']))
        else:
            # Backward compatibility - use old constants
            from utils import (MARGIN_TOP, MARGIN_LEFT, HUB_TITLE_Y_OFFSET, HUB_SUBTITLE_Y_OFFSET,
                              HUB_MENU_START_Y_OFFSET, HUB_MENU_LINE_HEIGHT, dim_color,
                              draw_scanlines, draw_footer)
            
            self.back_arrow_rect = draw_back_arrow(screen, self.color)
            
            title_font = get_font(48)
            title_surface = title_font.render(self.title, True, self.color)
            screen.blit(title_surface, (MARGIN_LEFT, MARGIN_TOP + HUB_TITLE_Y_OFFSET))
            
            subtitle_font = get_font(24)
            subtitle = subtitle_font.render("select a visualization:", True, self.color)
            screen.blit(subtitle, (MARGIN_LEFT, MARGIN_TOP + HUB_SUBTITLE_Y_OFFSET))
            
            item_font = get_font(32)
            start_y = MARGIN_TOP + HUB_MENU_START_Y_OFFSET
            
            for i, item in enumerate(self.items):
                if i == self.selected_index:
                    prefix = "> "
                    color = self.color
                else:
                    prefix = "  "
                    color = dim_color(self.color)
                
                text = item_font.render(f"{prefix}{item['label']}", True, color)
                screen.blit(text, (MARGIN_LEFT, start_y + i * HUB_MENU_LINE_HEIGHT))
            
            # Footer for backward compatibility
            help_font = get_font(18)
            help_text = "press 1-3, arrow keys + enter, click, or use voice"
            help_surface = help_font.render(help_text, True, dim_color(self.color, 0.33))
            screen.blit(help_surface, (MARGIN_LEFT, h - 100))
            
            esc_text = "esc: return to main menu"
            esc_surface = help_font.render(esc_text, True, dim_color(self.color, 0.33))
            screen.blit(esc_surface, (MARGIN_LEFT, h - 75))
            
            draw_scanlines(screen)
            draw_footer(screen, self.color)


class SceneManager:
    """Manages scene lifecycle and transitions."""
    
    def __init__(self, screen: pygame.Surface, config: dict):
        self.screen = screen
        self.config = config
        self.scenes: Dict[str, Scene] = {}
        self.current_scene: Optional[Scene] = None
        self.current_scene_name: Optional[str] = None
        self._lazy_factories: Dict[str, Callable] = {}  # Lazy loading factories
    
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
    
    def switch_to(self, name: str):
        """Switch to a different scene by name."""
        # Ensure scene is loaded (lazy loading)
        self._ensure_loaded(name)
        
        if name not in self.scenes:
            raise ValueError(f"Scene '{name}' not registered")
        
        if self.current_scene:
            self.current_scene.on_exit()
        
        self.current_scene = self.scenes[name]
        self.current_scene_name = name
        self.current_scene.on_enter()
    
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
