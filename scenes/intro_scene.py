#!/usr/bin/env python3
import time
import pygame
from scene_manager import Scene, register_scene
from utils import get_font, get_theme_font, draw_scanlines, draw_footer
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
        self.base_font_size = 32  # Smaller, more terminal-like
        self.margin_x = 0
        self.margin_y = 0
        self.line_height = 0
    
    def on_enter(self):
        """Initialize intro sequence."""
        # Lines and colors already loaded from theme in __init__
        
        w, h = self.manager.screen.get_size()
        # Match menu margins (approximately 8% from screenshot)
        self.margin_x = int(w * 0.08)
        self.margin_y = int(h * 0.12)  # Top margin
        self.base_font_size = max(28, int(h * 0.04))  # Terminal-sized font
        self.line_height = int(self.base_font_size * 1.5)  # Line spacing
        
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
        
        # Draw all completed lines (use primary font - IBM Plex Mono)
        for line in self.completed_lines:
            text_with_prompt = f"> {line}"
            font = get_theme_font(self.base_font_size, 'primary')
            img = font.render(text_with_prompt, True, self.color)
            screen.blit(img, (self.margin_x, y_pos))
            y_pos += self.line_height
        
        # Draw current line being typed
        if self.shown_text:
            text_with_prompt = f"> {self.shown_text}"
            font = get_theme_font(self.base_font_size, 'primary')
            img = font.render(text_with_prompt, True, self.color)
            screen.blit(img, (self.margin_x, y_pos))
            
            # Add blinking cursor
            if int(time.time() * 2) % 2 == 0:  # Blink every 0.5 seconds
                cursor_x = self.margin_x + img.get_width() + 5
                cursor = font.render("_", True, self.color)
                screen.blit(cursor, (cursor_x, y_pos))
        
        # Draw overlays
        draw_scanlines(screen)
        draw_footer(screen, self.color)
