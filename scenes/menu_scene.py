#!/usr/bin/env python3
import pygame
from pathlib import Path
from scene_manager import Scene, register_scene
from utils import get_font, get_theme_font, draw_scanlines, draw_footer, render_text, load_icon, launch_command, ROOT
from intent_router import Intents
from renderers import FrameState, Shape, Text, Image
from theme_loader import get_theme_loader


@register_scene("MenuScene")
class MenuScene(Scene):
    """Menu selection scene with 3 options."""
    
    def __init__(self, manager):
        super().__init__(manager)
        
        # Load theme (content + layout + style)
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme('menu', theme_name='pipboy')
        
        # Extract from theme
        self.entries = self.theme['content']['items']
        self.color = tuple(self.theme['style']['colors']['primary'])
        self.bg = tuple(self.theme['style']['colors']['background'])
        
        # Layout vars (will be calculated in on_enter)
        self.button_rects = []  # Store button rectangles for click detection
        self.button_spacing = 0
        self.button_start_y = 0
    
    def on_enter(self):
        """Initialize menu display."""
        # Content and colors already loaded from theme in __init__
        
        w, h = self.manager.screen.get_size()
        
        # Get layout from theme
        layout = self.theme['layout']
        style = self.theme['style']
        
        # Get margins and calculate usable area
        margins = layout.get('margins', {})
        margin_left = margins.get('left', 50)
        margin_right = margins.get('right', 50)
        margin_top = margins.get('top', 50)
        margin_bottom = margins.get('bottom', 130)
        
        # Calculate two-column layout
        columns = layout.get('columns', {})
        left_col_width = columns.get('left', {}).get('width', 715)
        right_col_width = columns.get('right', {}).get('width', 415)
        col_gutter = columns.get('gutter', 50)
        
        # Column x positions
        self.left_col_x = margin_left
        self.left_col_width = left_col_width
        self.right_col_x = margin_left + left_col_width + col_gutter
        self.right_col_width = right_col_width
        
        # Usable height (excluding top margin and footer)
        self.content_top = margin_top
        self.content_height = h - margin_top - margin_bottom
        
        # Button layout - vertical in left column
        button_config = layout.get('buttons', {})
        self.button_spacing = button_config.get('spacing', 30)
        self.button_start_y = margin_top  # Start at top margin
    
    def on_exit(self):
        """Clean up when leaving scene."""
        pass
    
    def is_select_event(self, event: pygame.event.Event) -> bool:
        """Check if event is a selection trigger (mouse left click or finger touch)."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return True
        if event.type == pygame.FINGERDOWN:
            return True
        return False
    
    def get_event_position(self, event: pygame.event.Event) -> tuple[int, int] | None:
        """Extract position from mouse or touch event."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            return event.pos
        elif event.type == pygame.FINGERDOWN:
            # Convert normalized touch coordinates (0-1) to screen pixels
            w, h = self.manager.screen.get_size()
            return (int(event.x * w), int(event.y * h))
        return None
    
    def handle_event(self, event: pygame.event.Event):
        """Handle menu input."""
        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Return to intro
                self.manager.switch_to("IntroScene")
                return True
            elif event.key == pygame.K_w:
                # Trigger wakeword for testing
                self.trigger_wakeword()
                return True
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.ctx.intent_router.emit(Intents.SELECT_OPTION, index=0)
                return True
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.ctx.intent_router.emit(Intents.SELECT_OPTION, index=1)
                return True
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.ctx.intent_router.emit(Intents.SELECT_OPTION, index=2)
                return True
        
        # Touch/Mouse selection - immediate on tap
        if self.is_select_event(event):
            pos = self.get_event_position(event)
            if pos:
                mx, my = pos
                for i, rect in enumerate(self.button_rects):
                    if rect.collidepoint(mx, my):
                        self.ctx.intent_router.emit(Intents.SELECT_OPTION, index=i)
                        return True
        
        return False
    
    def select_option(self, index: int):
        """Public method to select an option by index (for voice commands)."""
        self.ctx.intent_router.emit(Intents.SELECT_OPTION, index=index)
    
    
    def update(self, dt: float):
        """Update menu state."""
        pass
    
    def draw(self, screen: pygame.Surface):
        """Draw the menu using renderer abstraction."""
        # Build frame state
        frame = FrameState(clear_color=self.bg)
        
        w, h = screen.get_size()
        
        # Get layout and style
        layout = self.theme['layout']
        style = self.theme['style']
        
        # Clear button rects for this frame
        self.button_rects = []
        
        # Render frame state (backward compat)
        self._render_frame_compat(screen, frame)
    
    def _render_frame_compat(self, screen, frame):
        """Temporary: render frame state using pygame (backward compat)."""
        from renderers.frame_state import ShapeType
        
        screen.fill(frame.clear_color)
        
        # Render shapes
        for shape in frame.shapes:
            color = shape.color[:3]
            if shape.shape_type == ShapeType.RECT:
                x, y = shape.position
                w, h = shape.size
                pygame.draw.rect(screen, color, (int(x), int(y), int(w), int(h)), shape.thickness)
        
        # Render images
        for image in frame.images:
            screen.blit(image.surface, (int(image.position[0]), int(image.position[1])))
        
        # Render text
        for text in frame.texts:
            # Use font_type from text object (set in draw method)
            font_type = getattr(text, 'font_type', 'primary')
            font = get_theme_font(text.font_size, font_type)
            
            color = text.color[:3]
            surface = font.render(text.content, True, color)
            
            # Handle alignment
            if hasattr(text, 'align') and text.align == 'center':
                rect = surface.get_rect(center=(int(text.position[0]), int(text.position[1])))
                screen.blit(surface, rect)
            else:
                screen.blit(surface, (int(text.position[0]), int(text.position[1])))
        
        # Draw buttons vertically in left column
        from utils import draw_button
        
        # Get layout and button config
        layout = self.theme['layout']
        buttons_config = layout.get('buttons', {})
        button_width = buttons_config.get('width', '67%')  # Button width override
        
        # Get adornment config to calculate offset
        button_config = layout.get('button', {})
        adornment_config = button_config.get('adornment', {})
        adornment_size = adornment_config.get('size', 25)
        adornment_margin = adornment_config.get('margin_left', 18)
        
        # Offset button x to account for adornment (so adornment stays within margin)
        button_x = self.left_col_x + adornment_size + adornment_margin
        
        y = self.button_start_y
        for i, entry in enumerate(self.entries):
            label = entry.get('label', f'Option {i+1}')
            button_rect = draw_button(
                surface=screen,
                x=button_x,
                y=y,
                container_width=self.left_col_width - (adornment_size + adornment_margin),
                text=label,
                theme={'layout': self.theme['layout'], 'style': self.theme['style']},
                width_pct=button_width  # Override button width
            )
            self.button_rects.append(button_rect)
            y += button_rect.height + self.button_spacing
        
        # Draw scanlines and footer
        draw_scanlines(screen)
        draw_footer(screen, self.color)
