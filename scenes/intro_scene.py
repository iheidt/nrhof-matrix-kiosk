#!/usr/bin/env python3
import time
import pygame
from scene_manager import Scene, register_scene
from utils import get_font, get_theme_font, draw_scanlines
from renderers import FrameState, Text
from theme_loader import get_theme_loader


@register_scene("IntroScene")
class IntroScene(Scene):
    """Typewriter intro sequence scene."""
    
    def __init__(self, manager):
        super().__init__(manager)
        
        # Load theme (content + layout + style)
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme('intro', theme_name='pipboy')
        
        # Extract from theme
        self.lines = self.theme['content']['lines']
        self.typewriter_speed = self.theme['content']['timing']['typewriter_speed']
        self.line_pause = self.theme['content']['timing']['line_pause']
        self.color = tuple(self.theme['style']['colors']['primary'])
        self.bg = tuple(self.theme['style']['colors']['background'])
        
        # State
        self.current_line_idx = 0
        self.current_char_idx = 0
        self.shown_text = ""
        self.completed_lines = []  # Store completed lines
        self.line_start_time = 0
        self.char_timer = 0
        self.linger_timer = 0
        self.pause_timer = 0
        self.state = "typing"  # typing, lingering, pausing, done
        
        # Load font settings from layout (already resolved by theme_loader)
        text_area = self.theme['layout']['text_area']
        typography = self.theme['style'].get('typography', {})
        
        # Font size already resolved by theme_loader ('body' → 32)
        self.base_font_size = text_area.get('font_size')
        self.font_type = text_area.get('font_type', 'primary')
        self.margin_x = 0
        self.margin_y = 0
        
        # Calculate line_height: font_size × ratio from pipboy.yaml
        # Need to find which size name this is (32 = body)
        fonts = typography.get('fonts', {})
        size_name = None
        for name, size in fonts.items():
            if size == self.base_font_size:
                size_name = name
                break
        
        if size_name:
            line_height_ratios = typography.get('line_height', {})
            ratio = line_height_ratios.get(size_name, 1.5)
            self.line_height = int(self.base_font_size * ratio)
        else:
            raise ValueError(f"Font size {self.base_font_size} not found in pipboy.yaml fonts scale")
    
    def on_enter(self):
        """Initialize intro sequence."""
        # Lines and colors already loaded from theme in __init__
        
        w, h = self.manager.screen.get_size()
        # Margins from layout or defaults
        self.margin_x = int(w * 0.08)
        self.margin_y = int(h * 0.15)
        
        # Font settings already loaded from layout in __init__
        # No hardcoded font sizes - all from layout
        
        # Reset state
        self.current_line_idx = 0
        self.current_char_idx = 0
        self.shown_text = ""
        self.completed_lines = []
        self.line_start_time = time.time()
        self.char_timer = 0
        self.linger_timer = 0
        self.pause_timer = 0
        self.state = "typing"
    
    def on_exit(self):
        """Clean up when leaving scene."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle events - allow skipping with RETURN or SPACE."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Skip to end of current line
                if self.current_line_idx < len(self.lines):
                    self.current_char_idx = len(self.lines[self.current_line_idx])
                    self.state = "lingering"
                    self.linger_timer = 0
                return True
            elif event.key == pygame.K_w:
                # Trigger wakeword for testing
                self.trigger_wakeword()
                return True
        return False
    
    def update(self, dt: float):
        """Update typewriter animation."""
        if self.current_line_idx >= len(self.lines):
            # All lines done, switch to menu
            self.manager.switch_to("MenuScene")
            return
        
        current_line = self.lines[self.current_line_idx]
        
        if self.state == "typing":
            self.char_timer += dt
            if self.char_timer >= self.typewriter_speed:
                self.char_timer = 0
                if self.current_char_idx < len(current_line):
                    self.current_char_idx += 1
                    self.shown_text = current_line[:self.current_char_idx]
                else:
                    # Line complete, start lingering
                    self.state = "lingering"
                    self.linger_timer = 0
        
        elif self.state == "lingering":
            self.linger_timer += dt
            if self.linger_timer >= self.theme['content']['timing']['line_pause']:
                self.state = "pausing"
                self.pause_timer = 0
        
        elif self.state == "pausing":
            self.pause_timer += dt
            if self.pause_timer >= 0.4:  # Pause 400ms between lines
                # Save completed line and move to next
                self.completed_lines.append(current_line)
                self.current_line_idx += 1
                self.current_char_idx = 0
                self.shown_text = ""
                self.line_start_time = time.time()
                self.state = "typing"
    
    def draw(self, screen: pygame.Surface):
        """Draw the terminal-style typewriter text."""
        # Clear screen
        screen.fill(self.bg)
        
        y_pos = self.margin_y
        
        # Draw all completed lines
        for line in self.completed_lines:
            text_with_prompt = f"> {line}"
            font = get_theme_font(self.base_font_size, self.font_type)
            img = font.render(text_with_prompt, True, self.color)
            screen.blit(img, (self.margin_x, y_pos))
            y_pos += self.line_height
        
        # Draw current line being typed
        if self.shown_text:
            text_with_prompt = f"> {self.shown_text}"
            font = get_theme_font(self.base_font_size, self.font_type)
            img = font.render(text_with_prompt, True, self.color)
            screen.blit(img, (self.margin_x, y_pos))
            
            # Add blinking cursor
            if int(time.time() * 2) % 2 == 0:  # Blink every 0.5 seconds
                cursor_x = self.margin_x + img.get_width() + 5
                cursor = font.render("_", True, self.color)
                screen.blit(cursor, (cursor_x, y_pos))
        
        # Draw overlays
        draw_scanlines(screen)
