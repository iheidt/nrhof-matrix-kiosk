#!/usr/bin/env python3
import time
import pygame
from scenes.scene_manager import Scene, register_scene
from ui.components import draw_scanlines
from ui.fonts import render_mixed_text
from renderers import FrameState, Shape, Text
from __version__ import __version__
from core.theme_loader import get_theme_loader


@register_scene("SplashScene")
class SplashScene(Scene):
    """Splash screen with loading progress."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        self.screen = ctx.scene_manager.screen if hasattr(ctx, 'scene_manager') else None
        self.progress = 0.0
        self._start = 0.0
        
        # Load theme (content + layout + style)
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme('splash', theme_name='pipboy')
        
        # Extract values from theme
        default_min_secs = self.theme['style'].get('timing', {}).get('splash_min_seconds', 2.0)
        self._min_secs = self.theme['content'].get('min_seconds', default_min_secs)
        self.color = tuple(self.theme['style']['colors']['primary'])
    
    def on_enter(self):
        """Initialize splash screen."""
        self._start = time.time()
        self.progress = 0.0
        
        # Reload theme to pick up any content changes
        self.theme = self.theme_loader.load_theme('splash', theme_name='pipboy')
        default_min_secs = self.theme['style'].get('timing', {}).get('splash_min_seconds', 2.0)
        self._min_secs = self.theme['content'].get('min_seconds', default_min_secs)
        self.color = tuple(self.theme['style']['colors']['primary'])
    
    def on_exit(self):
        """Clean up splash screen."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        # No interaction during splash
        return False
    
    def update(self, dt: float):
        """Update splash screen progress."""
        elapsed = time.time() - self._start
        
        # Read preload progress from app context
        if hasattr(self.ctx, 'preload_progress'):
            self.progress = self.ctx.preload_progress
        else:
            # Animate progress to match min_seconds duration with ease-in-out
            # Progress should reach 1.0 at min_seconds
            t = min(1.0, elapsed / self._min_secs)  # Normalized time (0 to 1)
            # Ease-in-out cubic: smooth acceleration and deceleration
            if t < 0.5:
                self.progress = 4 * t * t * t
            else:
                self.progress = 1 - pow(-2 * t + 2, 3) / 2
        
        # Check if loading is done and minimum time has elapsed
        preload_done = getattr(self.ctx, 'preload_done', False)
        
        if (preload_done or self.progress >= 1.0) and elapsed >= self._min_secs:
            # Check if skip_intro flag is enabled
            skip_intro = self.ctx.config.get('flags', {}).get('skip_intro', False)
            next_scene = 'MenuScene' if skip_intro else 'IntroScene'
            # Disable transition from splash screen
            self.manager.switch_to(next_scene, use_transition=False)
    
    def draw(self, screen: pygame.Surface):
        """Build frame state for rendering."""
        style = self.theme['style']
        frame = FrameState(clear_color=tuple(style['colors']['background']))
        
        w, h = screen.get_size()
        screen_size = (w, h)
        
        # Get content, layout, and style from theme
        content = self.theme['content']
        layout = self.theme['layout']
        style = self.theme['style']
        
        # Title text
        from core.localization import t
        title_layout = layout['title']
        title_pos = self.theme_loader.resolve_position(title_layout['position'], screen_size)
        # Use localization for title
        title_content = t('splash.title')
        title_text = Text.create(
            content=title_content,
            x=title_pos[0],
            y=title_pos[1],
            color=tuple(style['colors']['primary']),
            font_size=title_layout['font_size'],
            mono=True
        )
        title_text.align = title_layout['align']
        title_text.font_type = title_layout.get('font_type', 'primary')  # Store font type
        frame.add_text(title_text)
        
        # Version text
        version_layout = layout['version']
        version_pos = self.theme_loader.resolve_position(version_layout['position'], screen_size)
        version_text = Text.create(
            content=f'v{__version__}',
            x=version_pos[0],
            y=version_pos[1],
            color=tuple(style['colors']['secondary']),
            font_size=version_layout['font_size'],
            mono=True
        )
        version_text.align = version_layout['align']
        version_text.font_type = version_layout.get('font_type', 'primary')
        frame.add_text(version_text)
        
        # Loading text
        loading_layout = layout['loading_text']
        loading_pos = self.theme_loader.resolve_position(loading_layout['position'], screen_size)
        # Use localization for loading text
        loading_content = t('splash.loading')
        loading_text = Text.create(
            content=loading_content,
            x=loading_pos[0],
            y=loading_pos[1],
            color=tuple(style['colors']['secondary']),
            font_size=loading_layout['font_size'],
            mono=True
        )
        loading_text.align = loading_layout['align']
        loading_text.font_type = loading_layout.get('font_type', 'primary')
        frame.add_text(loading_text)
        
        # Progress bar
        bar_layout = layout['progress_bar']
        bar_pos = self.theme_loader.resolve_position(bar_layout['position'], screen_size)
        bar_width = bar_layout['width']
        bar_height = bar_layout['height']
        bar_x = bar_pos[0] - bar_width // 2  # Center the bar
        bar_y = bar_pos[1]
        
        # Border
        primary = style['colors']['primary']
        border_color = tuple(int(c * 0.5) for c in primary)
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
                color=tuple(style['colors']['primary']),
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
        # Use font_type from layout (primary, secondary, or label)
        font_type = getattr(text, 'font_type', 'primary')
        # Use mixed text rendering for Japanese support
        color = text.color[:3]
        surface = render_mixed_text(text.content, text.font_size, font_type, color)
        x, y = text.position
        if text.align == "center":
            rect = surface.get_rect(center=(int(x), int(y)))
            screen.blit(surface, rect)
        else:
            screen.blit(surface, (int(x), int(y)))