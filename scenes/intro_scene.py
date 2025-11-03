#!/usr/bin/env python3
import time
import pygame
from scene_manager import Scene, register_scene
from utils import get_font, draw_scanlines, draw_footer


@register_scene("IntroScene")
class IntroScene(Scene):
    """Typewriter intro sequence scene."""
    
    def __init__(self, manager):
        super().__init__(manager)
        self.lines = []
        self.color = (140, 255, 140)
        self.bg = (0, 0, 0)
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
        from utils import get_matrix_green
        cfg = self.manager.config
        self.lines = cfg.get("intro_texts", [])
        self.color = get_matrix_green(cfg)
        
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
            if self.char_timer >= 0.045:  # 45ms per character
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
            if self.linger_timer >= 1.2:  # Linger for 1.2 seconds
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
        screen.fill(self.bg)
        
        font = get_font(self.base_font_size)
        y_pos = self.margin_y
        
        # Draw all completed lines
        for line in self.completed_lines:
            text_with_prompt = f"> {line}"
            img = font.render(text_with_prompt, True, self.color)
            screen.blit(img, (self.margin_x, y_pos))
            y_pos += self.line_height
        
        # Draw current line being typed
        if self.shown_text:
            text_with_prompt = f"> {self.shown_text}"
            img = font.render(text_with_prompt, True, self.color)
            screen.blit(img, (self.margin_x, y_pos))
            
            # Add blinking cursor
            if int(time.time() * 2) % 2 == 0:  # Blink every 0.5 seconds
                cursor_x = self.margin_x + img.get_width() + 5
                cursor = font.render("_", True, self.color)
                screen.blit(cursor, (cursor_x, y_pos))
        
        draw_scanlines(screen)
        draw_footer(screen, self.color)
