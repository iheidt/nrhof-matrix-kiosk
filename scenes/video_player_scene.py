#!/usr/bin/env python3
import pygame
from pathlib import Path
from scene_manager import Scene, register_scene
from intent_router import Intents
from renderers import FrameState, Video, Text


@register_scene("VideoPlayerScene")
class VideoPlayerScene(Scene):
    """Fullscreen video player."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        self.movie = None
        self.movie_screen = None
        self.playing = False
        self.video_finished = False
        self.cap = None
        self.use_opencv = False
        self.current_frame = None
        self.frame_time = 0
        self.video_fps = 30  # Default FPS
    
    def on_enter(self):
        """Load and start playing the video."""
        # Get video filename from app context
        video_filename = getattr(self.ctx, 'selected_video', None)
        
        if not video_filename:
            print("No video file specified")
            return
        
        video_path = Path(__file__).parent.parent / "assets" / "videos" / video_filename
        
        if not video_path.exists():
            print(f"Video not found: {video_path}")
            return
        
        try:
            # Initialize pygame.movie (if available)
            # Note: pygame.movie is deprecated, we'll use a workaround
            # For now, we'll use a simple approach with external player
            
            # Try to use pygame's video support
            # This requires pygame to be built with ffmpeg support
            self.movie = pygame.movie.Movie(str(video_path))
            
            # Get screen size
            screen_size = self.manager.screen.get_size()
            
            # Create a surface for the movie
            self.movie_screen = pygame.Surface(screen_size).convert()
            
            # Set the display surface
            self.movie.set_display(self.movie_screen)
            
            # Start playing
            self.movie.play()
            self.playing = True
            self.video_finished = False
            
        except AttributeError:
            # pygame.movie not available, use alternative approach
            print("pygame.movie not available, using alternative video player")
            self._play_with_opencv(video_path)
    
    def _play_with_opencv(self, video_path: Path):
        """Alternative video playback using OpenCV (if available)."""
        try:
            import cv2
            self.cap = cv2.VideoCapture(str(video_path))
            # Get video FPS
            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if self.video_fps == 0:
                self.video_fps = 30  # Fallback
            self.playing = True
            self.video_finished = False
            self.use_opencv = True
            self.frame_time = 0
            print(f"Video FPS: {self.video_fps}")
        except ImportError:
            print("OpenCV not available. Install with: pip install opencv-python")
            self.playing = False
            self.video_finished = True
    
    def on_exit(self):
        """Clean up video resources."""
        if hasattr(self, 'movie') and self.movie:
            self.movie.stop()
            self.movie = None
        
        if hasattr(self, 'cap'):
            self.cap.release()
    
    def handle_event(self, event: pygame.event.Event):
        """Handle input events."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_BACKSPACE:
                # Stop video and go back
                self.ctx.intent_router.emit(Intents.GO_HOME)
                return True
            elif event.key == pygame.K_SPACE:
                # Pause/resume
                if self.movie and self.playing:
                    self.movie.pause()
                    self.playing = False
                elif self.movie:
                    self.movie.play()
                    self.playing = True
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Click anywhere to go back
            self.ctx.intent_router.emit(Intents.GO_HOME)
            return True
        
        return False
    
    def update(self, dt: float):
        """Update video playback."""
        # Update frame timing for OpenCV playback
        if self.use_opencv and self.cap and self.cap.isOpened():
            self.frame_time += dt
            frame_duration = 1.0 / self.video_fps
            
            # Only read a new frame if enough time has passed
            if self.frame_time >= frame_duration:
                self.frame_time = 0
                ret, frame = self.cap.read()
                if ret:
                    # Store the frame for drawing
                    self.current_frame = frame
                else:
                    # Video finished
                    self.video_finished = True
                    self.ctx.intent_router.emit(Intents.GO_HOME)
        
        elif self.movie and not self.movie.get_busy():
            # Movie finished
            self.video_finished = True
            self.ctx.intent_router.emit(Intents.GO_HOME)
    
    def draw(self, screen: pygame.Surface):
        """Draw the video frame using renderer abstraction."""
        # Load theme colors
        from theme_loader import get_theme_loader
        theme_loader = get_theme_loader()
        style = theme_loader.load_style('pipboy')
        
        # Clear screen
        screen.fill(tuple(style['colors']['background']))
        
        screen_size = screen.get_size()
        
        if self.use_opencv and self.current_frame is not None:
            # Convert OpenCV frame to pygame surface
            import cv2
            import numpy as np
            
            frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            frame = np.rot90(frame)
            frame_surface = pygame.surfarray.make_surface(frame)
            
            # Scale to fit screen
            frame_surface = pygame.transform.scale(frame_surface, screen_size)
            
            # Draw directly (video frames are already surfaces)
            screen.blit(frame_surface, (0, 0))
        
        elif self.movie_screen:
            # Draw pygame.movie frame
            screen.blit(self.movie_screen, (0, 0))
        
        else:
            # Show error message using renderer abstraction
            from utils import get_font
            
            font = get_font(48)
            text = font.render("Video player not available", True, tuple(style['colors']['primary']))
            text_rect = text.get_rect(center=(screen_size[0] // 2, screen_size[1] // 2))
            screen.blit(text, text_rect)
            
            hint_font = get_font(24)
            hint_text = hint_font.render("Press ESC to go back", True, tuple(style['colors']['secondary']))
            hint_rect = hint_text.get_rect(center=(screen_size[0] // 2, screen_size[1] // 2 + 50))
            screen.blit(hint_text, hint_rect)
