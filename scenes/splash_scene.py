#!/usr/bin/env python3
import time
import pygame
from scene_manager import Scene, register_scene
from utils import get_font, get_matrix_green
from renderers import FrameState, Shape, Text


@register_scene("SplashScene")
class SplashScene(Scene):
    """Splash screen with loading progress."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        self.screen = ctx.scene_manager.screen if hasattr(ctx, 'scene_manager') else None
        self.progress = 0.0
        self._start = 0.0
        self._min_secs = ctx.config.get('splash_min_seconds', 1.0) if hasattr(ctx, 'config') else 1.0
        self.color = (140, 255, 140)
    
    def on_enter(self):
        """Initialize splash screen."""
        self._start = time.time()
        self.progress = 0.0
        self.color = get_matrix_green(self.manager.config)
    
    def on_exit(self):
        """Clean up splash screen."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        # No interaction during splash
        return False
    
    def update(self, dt: float):
        """Update splash screen progress."""
        # Read preload progress from app context
        if hasattr(self.ctx, 'preload_progress'):
            self.progress = self.ctx.preload_progress
        else:
            # Fallback: simulate progress
            self.progress = min(1.0, self.progress + dt * 0.5)
        
        # Check if loading is done and minimum time has elapsed
        elapsed = time.time() - self._start
        preload_done = getattr(self.ctx, 'preload_done', False)
        
        if (preload_done or self.progress >= 1.0) and elapsed >= self._min_secs:
            self.manager.switch_to('IntroScene')
    
    def draw(self, screen: pygame.Surface):
        """Build frame state for rendering."""
        frame = FrameState(clear_color=(0, 0, 0))
        
        w, h = screen.get_size()
        center_x = w // 2
        center_y = h // 2
        
        # Title text
        title = self.manager.config.get('title', 'NRHOF kiosk')
        frame.add_text(Text.create(
            content=title,
            x=center_x,
            y=center_y - 60,
            color=self.color,
            font_size=48,
            mono=True
        ))
        # Center align the title
        frame.texts[-1].align = "center"
        
        # Loading text
        frame.add_text(Text.create(
            content='loading...',
            x=center_x,
            y=center_y + 20,
            color=self.color,
            font_size=24,
            mono=True
        ))
        frame.texts[-1].align = "center"
        
        # Progress bar
        bar_width = 400
        bar_height = 20
        bar_x = center_x - bar_width // 2
        bar_y = center_y + 60
        
        # Border
        border_color = tuple(int(c * 0.5) for c in self.color)
        frame.add_shape(Shape.rect(
            x=bar_x,
            y=bar_y,
            w=bar_width,
            h=bar_height,
            color=border_color,
            thickness=2
        ))
        
        # Filled progress
        fill_width = int(bar_width * self.progress)
        if fill_width > 0:
            frame.add_shape(Shape.rect(
                x=bar_x + 2,
                y=bar_y + 2,
                w=fill_width - 4,
                h=bar_height - 4,
                color=self.color,
                thickness=0
            ))
        
        # For backward compatibility, still render using pygame directly
        # This will be removed once we integrate renderer into app.py
        screen.fill(frame.clear_color)
        for shape in frame.shapes:
            self._render_shape_compat(screen, shape)
        for text in frame.texts:
            self._render_text_compat(screen, text)
    
    def _render_shape_compat(self, screen, shape):
        """Temporary: render shape using pygame (backward compat)."""
        from renderers.frame_state import ShapeType
        color = shape.color[:3]
        if shape.shape_type == ShapeType.RECT:
            x, y = shape.position
            w, h = shape.size
            pygame.draw.rect(screen, color, (int(x), int(y), int(w), int(h)), shape.thickness)
    
    def _render_text_compat(self, screen, text):
        """Temporary: render text using pygame (backward compat)."""
        font = get_font(text.font_size, mono=(text.font_family == "monospace"))
        color = text.color[:3]
        surface = font.render(text.content, True, color)
        x, y = text.position
        if text.align == "center":
            rect = surface.get_rect(center=(int(x), int(y)))
            screen.blit(surface, rect)
        else:
            screen.blit(surface, (int(x), int(y)))