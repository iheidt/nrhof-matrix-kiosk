#!/usr/bin/env python3
import pygame
from pathlib import Path
from scene_manager import Scene, register_scene
from utils import get_font, draw_scanlines, draw_footer, render_text, load_icon, launch_command, ROOT
from intent_router import Intents
from renderers import FrameState, Shape, Text, Image


@register_scene("MenuScene")
class MenuScene(Scene):
    """Menu selection scene with 3 options."""
    
    def __init__(self, manager):
        super().__init__(manager)
        self.color = (140, 255, 140)
        self.bg = (0, 0, 0)
        self.icons = []
        self.entries = []
        self.title = ""
        
        # Layout vars
        self.margin = 0
        self.gutter = 0
        self.card_w = 0
        self.card_h = 0
        self.top = 0
        self.icon_pad = 0
        self.icon_size = (0, 0)
        self.title_font_size = 28
        self.item_font_size = 22
    
    def on_enter(self):
        """Initialize menu display."""
        from utils import get_matrix_green
        cfg = self.manager.config
        self.color = get_matrix_green(cfg)
        self.title = cfg["menu"].get("title", "Select an option:")
        self.entries = cfg["menu"].get("entries", [])
        
        w, h = self.manager.screen.get_size()
        self.title_font_size = max(28, int(h * 0.05))
        self.item_font_size = max(22, int(h * 0.035))
        
        # Layout 3 columns
        self.margin = int(w * 0.08)
        self.gutter = int(w * 0.04)
        self.card_w = (w - self.margin * 2 - self.gutter * 2) // 3
        self.card_h = int(h * 0.45)
        self.top = int(h * 0.25)
        
        self.icon_pad = int(self.card_w * 0.1)
        self.icon_size = (self.card_w - 2 * self.icon_pad, int(self.card_h * 0.55))
        
        # Load icons
        self.icons = []
        for e in self.entries:
            icon_path = ROOT / e.get("icon", "")
            self.icons.append(load_icon(icon_path, self.icon_size))
    
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
                for i in range(3):
                    x = self.margin + i * (self.card_w + self.gutter)
                    rect = pygame.Rect(x, self.top, self.card_w, self.card_h)
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
        
        # Title text
        frame.add_text(Text.create(
            content=self.title,
            x=self.margin,
            y=int(h * 0.12),
            color=self.color,
            font_size=self.title_font_size,
            mono=True
        ))
        
        # Draw menu cards
        for i, e in enumerate(self.entries):
            x = self.margin + i * (self.card_w + self.gutter)
            
            # Card background
            frame.add_shape(Shape.rect(
                x=x,
                y=self.top,
                w=self.card_w,
                h=self.card_h,
                color=(5, 5, 5),
                thickness=0
            ))
            
            # Card border
            frame.add_shape(Shape.rect(
                x=x,
                y=self.top,
                w=self.card_w,
                h=self.card_h,
                color=(40, 100, 40),
                thickness=2
            ))
            
            # Icon area
            icon = self.icons[i] if i < len(self.icons) else None
            icon_x = x + self.icon_pad
            icon_y = self.top + self.icon_pad
            
            if icon:
                frame.add_image(Image.create(
                    surface=icon,
                    x=icon_x,
                    y=icon_y
                ))
            else:
                # Placeholder frame
                frame.add_shape(Shape.rect(
                    x=icon_x,
                    y=icon_y,
                    w=self.icon_size[0],
                    h=self.icon_size[1],
                    color=(20, 60, 20),
                    thickness=2
                ))
                # Placeholder text
                frame.add_text(Text.create(
                    content=e.get("label", f"Option {i+1}"),
                    x=icon_x + 8,
                    y=icon_y + self.icon_size[1] // 2 - 12,
                    color=self.color,
                    font_size=self.item_font_size,
                    mono=True
                ))
            
            # Label at bottom
            label = e.get("label", f"Option {i+1}")
            frame.add_text(Text.create(
                content=label,
                x=x + self.icon_pad,
                y=self.top + self.card_h - self.icon_pad - self.item_font_size,
                color=self.color,
                font_size=self.item_font_size,
                mono=True
            ))
        
        # Render frame state (backward compat)
        self._render_frame_compat(screen, frame)
        
        # Draw scanlines and footer (still using utils for now)
        draw_scanlines(screen)
        draw_footer(screen, self.color)
    
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
            font = get_font(text.font_size, mono=(text.font_family == "monospace"))
            color = text.color[:3]
            surface = font.render(text.content, True, color)
            screen.blit(surface, (int(text.position[0]), int(text.position[1])))
