#!/usr/bin/env python3
import pygame
import math
from scene_manager import Scene, register_scene
from utils import draw_scanlines, draw_footer, draw_back_arrow, MARGIN_TOP, MARGIN_LEFT, MARGIN_RIGHT, MARGIN_BOTTOM, get_font, get_matrix_green
from intent_router import Intents
from sprites.exp2_silhouettes import SILH_LEAD_GUITAR_A


@register_scene("Experience2SilhouetteParallaxScene")
class Experience2SilhouetteParallaxScene(Scene):
    """Silhouette parallax scene with ASCII characters and scrolling background."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        self.color = (140, 255, 140)
        self.bg = (0, 0, 0)
        
        # Parallax background
        self.bg_scroll_x = 0
        self.bg_scroll_speed = 0.5  # pixels per frame
        
        # Characters (silhouettes)
        self.characters = []
        
        # Time for animation
        self.time = 0
        self.back_arrow_rect = None
    
    def on_enter(self):
        """Initialize parallax scene."""
        self.color = get_matrix_green(self.manager.config)
        
        w, h = self.manager.screen.get_size()
        
        # Calculate usable area respecting all margins
        usable_width = w - MARGIN_LEFT - MARGIN_RIGHT
        usable_height = h - MARGIN_TOP - MARGIN_BOTTOM
        
        # Create 3 silhouette characters
        # Character 1: Lead guitar sprite (centered)
        # Characters 2-3: Placeholder blocky shapes
        self.characters = [
            {
                "type": "sprite",
                "sprite": SILH_LEAD_GUITAR_A,
                "x": MARGIN_LEFT + usable_width * 0.5,  # Centered horizontally
                "y": MARGIN_TOP + usable_height * 0.7,
                "bob_offset": 0,
                "bob_speed": 0.8,
                "bob_amplitude": 2
            },
            {
                "type": "placeholder",
                "x": MARGIN_LEFT + usable_width * 0.25,
                "y": MARGIN_TOP + usable_height * 0.65,
                "width": 90,
                "height": 140,
                "bob_offset": 1.5,
                "bob_speed": 0.6,
                "bob_amplitude": 1.5
            },
            {
                "type": "placeholder",
                "x": MARGIN_LEFT + usable_width * 0.75,
                "y": MARGIN_TOP + usable_height * 0.75,
                "width": 75,
                "height": 110,
                "bob_offset": 3,
                "bob_speed": 0.7,
                "bob_amplitude": 2.5
            }
        ]
        
        self.bg_scroll_x = 0
        self.time = 0
    
    def on_exit(self):
        """Clean up scene."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        # Handle common events (ESC, back arrow, wakeword)
        return self.handle_common_events(event, Intents.GO_HOME, self.back_arrow_rect)
    
    def update(self, dt: float):
        """Update parallax animation."""
        self.time += dt
        
        # Update background scroll
        self.bg_scroll_x += self.bg_scroll_speed
        
        # Wrap background scroll
        if self.bg_scroll_x > 50:
            self.bg_scroll_x = 0
    
    def draw(self, screen: pygame.Surface):
        """Draw the parallax scene."""
        screen.fill(self.bg)
        w, h = screen.get_size()
        
        # Draw scrolling ASCII gradient background pattern
        self._draw_background(screen, w, h)
        
        # Draw silhouette characters with bob animation
        self._draw_characters(screen)
        
        # Draw back arrow
        self.back_arrow_rect = draw_back_arrow(screen, self.color)
        
        draw_scanlines(screen)
        draw_footer(screen, self.color)
    
    def _draw_background(self, screen: pygame.Surface, w: int, h: int):
        """Draw scrolling ASCII gradient background."""
        # ASCII characters for gradient effect
        gradient_chars = ['.', ':', '-', '=', '+', '*', '#', '@']
        
        char_size = 20
        font = get_font(char_size, mono=True)
        
        # Calculate how many columns we need
        cols = (w // char_size) + 2
        rows = h // char_size
        
        for row in range(rows):
            for col in range(cols):
                # Calculate position with scroll offset
                x = col * char_size - int(self.bg_scroll_x)
                y = row * char_size
                
                # Create gradient pattern based on position
                gradient_index = ((col + row) % len(gradient_chars))
                char = gradient_chars[gradient_index]
                
                # Dim the background
                dim_color = tuple(c // 4 for c in self.color)
                
                text = font.render(char, True, dim_color)
                screen.blit(text, (x, y))
    
    def _draw_characters(self, screen: pygame.Surface):
        """Draw silhouette characters with bob animation."""
        for char in self.characters:
            # Calculate bob offset
            bob_y = math.sin(self.time * char["bob_speed"] + char["bob_offset"]) * char["bob_amplitude"]
            
            if char.get("type") == "sprite":
                # Draw sprite-based character
                self._draw_sprite_silhouette(screen, char, bob_y)
            else:
                # Draw placeholder blocky character
                x = int(char["x"] - char["width"] // 2)
                y = int(char["y"] - char["height"] + bob_y)
                self._draw_ascii_silhouette(screen, x, y, char["width"], char["height"])
    
    def _draw_ascii_silhouette(self, screen: pygame.Surface, x: int, y: int, width: int, height: int):
        """Draw a blocky ASCII character silhouette."""
        # Use block characters to create silhouette
        block_char = '█'
        char_size = 8
        font = get_font(char_size, mono=True)
        
        # Draw filled rectangle using ASCII blocks
        cols = width // char_size
        rows = height // char_size
        
        for row in range(rows):
            for col in range(cols):
                char_x = x + col * char_size
                char_y = y + row * char_size
                
                # Create simple humanoid shape (wider at shoulders, narrower at waist)
                col_ratio = col / cols
                row_ratio = row / rows
                
                # Simple silhouette logic: skip some blocks to create shape
                if row_ratio < 0.2:
                    # Head - narrower
                    if col_ratio < 0.3 or col_ratio > 0.7:
                        continue
                elif row_ratio < 0.4:
                    # Shoulders - wider
                    pass
                elif row_ratio < 0.7:
                    # Torso - medium
                    if col_ratio < 0.2 or col_ratio > 0.8:
                        continue
                else:
                    # Legs - split
                    if 0.4 < col_ratio < 0.6:
                        continue
                
                text = font.render(block_char, True, self.color)
                screen.blit(text, (char_x, char_y))
    
    def _draw_sprite_silhouette(self, screen: pygame.Surface, char: dict, bob_y: float):
        """Draw a sprite-based silhouette character.
        
        Args:
            screen: Pygame surface to draw on
            char: Character dict with sprite data
            bob_y: Vertical bob offset
        """
        sprite = char["sprite"]
        char_size = 8
        font = get_font(char_size, mono=True)
        
        # Calculate sprite dimensions
        sprite_height = len(sprite)
        sprite_width = max(len(row) for row in sprite) if sprite else 0
        
        pixel_height = sprite_height * char_size
        pixel_width = sprite_width * char_size
        
        # Center the sprite horizontally at char["x"]
        start_x = int(char["x"] - pixel_width // 2)
        start_y = int(char["y"] - pixel_height + bob_y)
        
        # Render each character in the sprite
        for row_idx, row in enumerate(sprite):
            for col_idx, ch in enumerate(row):
                if ch != ' ':  # Only draw non-space characters
                    x = start_x + col_idx * char_size
                    y = start_y + row_idx * char_size
                    text = font.render(ch, True, self.color)
                    screen.blit(text, (x, y))
