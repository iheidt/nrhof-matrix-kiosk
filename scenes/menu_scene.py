#!/usr/bin/env python3
import pygame
import time
from pathlib import Path
from scenes.scene_manager import Scene, register_scene
from utils import get_font, get_theme_font, draw_scanlines, draw_footer, render_text, load_icon, launch_command, draw_now_playing, draw_d20, draw_timeclock, ROOT
from routing.intent_router import Intents
from renderers import FrameState, Shape, Text, Image
from core.theme_loader import get_theme_loader
from core.app_state import get_app_state
from core.now_playing import get_now_playing_state
from core.event_bus import get_event_bus, EventType
from ui.components.widgets import MarqueeText


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
        # Marquee for now playing text
        self.now_playing_marquee = None
        
        # Progress tracking for smooth interpolation
        self.last_track_id = None
        self.last_progress_ms = None
        self.last_progress_update_time = None
        
        # Fade transition tracking
        self.playback_state_start_time = None
        self.is_in_playback_state = False
        self.fade_delay = 1.0  # Delay before starting fade (seconds)
        self.fade_duration = 0.5  # Fade duration (seconds)
        
        # Wake word detection indicator
        self.wake_word_detected_time = None
        self.wake_word_indicator_duration = 2.0  # Show red dot for 2 seconds
        
        # Subscribe to wake word events
        event_bus = get_event_bus()
        event_bus.subscribe(EventType.WAKE_WORD_DETECTED, self._on_wake_word_detected)
    
    def _on_wake_word_detected(self, **kwargs):
        """Handle wake word detection event."""
        keyword = kwargs.get('keyword', 'unknown')
        print(f"[MENU] Wake word detected: {keyword}")
        self.wake_word_detected_time = time.time()
    
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
        
        # Draw title card at top of left column
        from utils import draw_title_card, draw_button
        from ui.components.widgets import draw_timeclock, draw_d20, draw_now_playing, MarqueeText
        
        # Get layout and style
        layout = self.theme['layout']
        style = self.theme['style']
        
        # Title card configuration from layout
        title_card_config = layout.get('title_card', {})
        title_card_height = title_card_config.get('height', 120)
        title_card_title = title_card_config.get('title', 'NRHOF')
        title_card_margin_bottom = title_card_config.get('margin_bottom', 70)
        title_card_fade_pct = title_card_config.get('border_fade_pct', 0.33)
        
        # Calculate title font size to determine overlap
        title_font_size = style['typography']['fonts'].get('title', 76)
        title_font = get_theme_font(title_font_size, 'secondary')
        title_surface = title_font.render(title_card_title, True, (255, 255, 255))
        title_overlap = title_surface.get_height() // 2
        
        # Adjust card y position so title top respects margin
        title_card_y = self.content_top + title_overlap
        
        title_card_rect = draw_title_card(
            surface=screen,
            x=self.left_col_x,
            y=title_card_y,
            width=self.left_col_width,
            height=title_card_height,
            title=title_card_title,
            theme={'layout': layout, 'style': style},
            border_fade_pct=title_card_fade_pct
        )
        
        # Get column configuration
        columns_config = layout.get('columns', {})
        
        # Draw buttons vertically in left column (below title card)
        buttons_config = layout.get('buttons', {})
        button_width = buttons_config.get('width', '67%')  # Button width override
        
        # Get adornment config to calculate offset
        button_config = layout.get('button', {})
        adornment_config = button_config.get('adornment', {})
        adornment_size = adornment_config.get('size', 25)
        adornment_margin = adornment_config.get('margin_left', 18)
        
        # Offset button x to account for adornment (so adornment stays within margin)
        button_x = self.left_col_x + adornment_size + adornment_margin
        
        # Start buttons below title card with configured spacing
        from core.localization import t
        y = title_card_y + title_card_height + title_card_margin_bottom
        for i, entry in enumerate(self.entries):
            # Use localization key if available, otherwise fall back to label
            label_key = entry.get('label_key')
            if label_key:
                label = t(label_key)
            else:
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
        
        # Draw now playing component in right column
        right_col_x = self.left_col_x + self.left_col_width + columns_config['gutter']
        right_col_width = columns_config['right']['width']
        
        # Get current track from NowPlayingState
        now_playing = get_now_playing_state()
        track = now_playing.get_track()
        
        # Determine title based on source
        if track:
            if track.source == 'spotify':
                # SPOTIFY . DEVICE NAME
                device = track.device_name if track.device_name else "unknown"
                device_formatted = device.upper().replace('-', '.')
                now_playing_title = f"SPOTIFY . {device_formatted}"
            elif track.source == 'sonos':
                # SONOS . ROOM NAME
                room = track.sonos_room if track.sonos_room else "unknown"
                room_formatted = room.upper().replace('-', '.')
                now_playing_title = f"SONOS . {room_formatted}"
            elif track.source == 'vinyl':
                # RECORD PLAYER
                now_playing_title = "RECORD PLAYER"
            else:
                now_playing_title = "NOW PLAYING"
            
            # Truncate title to prevent overlap with circle (max ~30 chars)
            if len(now_playing_title) > 30:
                now_playing_title = now_playing_title[:27] + "..."
        else:
            now_playing_title = "NOW PLAYING"
        
        if track:
            # Format based on content type with emojis and lowercase
            if track.content_type == 'podcast':
                show = track.show_name.lower() if track.show_name else "unknown podcast"
                title = track.title.lower() if track.title else "unknown episode"
                song_line = f"{show} • {title}"
                album_line = f"podcast • {track.publisher.lower()}" if track.publisher else "podcast"
            elif track.content_type == 'audiobook':
                title = track.title.lower() if track.title else "unknown title"
                author = track.artist.lower() if track.artist else "unknown author"
                song_line = f"{title} • {author}"
                album_line = f"audiobook • {track.publisher.lower()}" if track.publisher else "audiobook"
            else:
                # Music (default)
                artist = track.artist.lower() if track.artist else "unknown artist"
                title = track.title.lower() if track.title else "unknown song"
                song_line = f"{artist} • {title}"
                
                # Show Sonos room if available, otherwise album
                if track.source == 'sonos' and track.sonos_room:
                    album_line = f"{track.sonos_room.lower()}"
                    if track.sonos_grouped_rooms:
                        album_line += f" + {len(track.sonos_grouped_rooms)} more"
                else:
                    album_line = track.album.lower() if track.album else f"via {track.source}"
        else:
            song_line = "listening"
            album_line = "none playing"
        
        # Initialize marquee if needed
        bg_width = right_col_width - 40
        max_text_width = bg_width - (24 * 2)  # 24px padding on each side
        if self.now_playing_marquee is None:
            self.now_playing_marquee = MarqueeText(song_line, max_text_width, scroll_speed=50.0, gap=100)
        
        # Get playback progress info with client-side interpolation
        progress_ms = None
        duration_ms = None
        is_playing = False
        
        if track:
            duration_ms = track.duration_ms
            is_playing = track.is_playing
            
            # Create a unique track ID for comparison
            track_id = f"{track.title}_{track.artist}_{track.source}"
            
            # Check if track changed
            if track_id != self.last_track_id:
                # New track, reset progress tracking
                self.last_track_id = track_id
                self.last_progress_ms = track.progress_ms
                self.last_progress_update_time = time.time()
                progress_ms = track.progress_ms
            elif track.progress_ms is not None and track.progress_ms != self.last_progress_ms:
                # Progress updated from API - always reset to new position
                # This handles both normal updates and scrubs
                self.last_progress_ms = track.progress_ms
                self.last_progress_update_time = time.time()
                progress_ms = track.progress_ms
            elif is_playing and self.last_progress_ms is not None and self.last_progress_update_time is not None:
                # Interpolate progress client-side for smooth animation
                elapsed_ms = (time.time() - self.last_progress_update_time) * 1000
                progress_ms = self.last_progress_ms + int(elapsed_ms)
                
                # Clamp to duration
                if duration_ms and progress_ms > duration_ms:
                    progress_ms = duration_ms
            else:
                # Not playing or no previous data
                progress_ms = track.progress_ms
        else:
            # No track, reset tracking
            self.last_track_id = None
            self.last_progress_ms = None
            self.last_progress_update_time = None
        
        # Track playback state changes for fade transition
        if is_playing and not self.is_in_playback_state:
            # Just started playing
            self.is_in_playback_state = True
            self.playback_state_start_time = time.time()
        elif not is_playing and self.is_in_playback_state:
            # Just stopped playing
            self.is_in_playback_state = False
            self.playback_state_start_time = time.time()
        
        # Calculate fade amount (0.0 = primary, 1.0 = dim)
        fade_amount = 0.0
        if self.playback_state_start_time is not None:
            elapsed = time.time() - self.playback_state_start_time
            
            if is_playing:
                # Fading to dim (playing state)
                if elapsed < self.fade_delay:
                    # Still in delay period, stay at primary
                    fade_amount = 0.0
                else:
                    # Fade from primary to dim
                    fade_progress = min(1.0, (elapsed - self.fade_delay) / self.fade_duration)
                    fade_amount = fade_progress
            else:
                # Fading back to primary (stopped state) - no delay, immediate fade
                fade_progress = min(1.0, elapsed / self.fade_duration)
                fade_amount = 1.0 - fade_progress  # Reverse: 1.0 -> 0.0
        
        # Pass border_y directly to align with title card top border (adjusted up by 6px)
        now_playing_rect = draw_now_playing(
            surface=screen,
            x=right_col_x,
            y=0,  # Not used when border_y is provided
            width=right_col_width,
            title=now_playing_title,
            line1=song_line,
            line2=album_line,
            theme={'style': style},
            border_y=title_card_y - 6,  # Move entire component up 6px
            marquee=self.now_playing_marquee,
            progress_ms=progress_ms,
            duration_ms=duration_ms,
            is_playing=is_playing,
            fade_amount=fade_amount
        )
        
        # Draw d20 component (includes speech_synthesizer inside) 100px below now playing, shifted 50px left
        d20_y = now_playing_rect.bottom + 110
        d20_x = right_col_x - 25  # Shift 50px to the left
        d20_rect = draw_d20(
            surface=screen,
            x=d20_x,
            y=d20_y,
            width=right_col_width,
            height=420,
            theme={'style': style}
        )
        
        # Draw timeclock component 100px below d20, extended 50px to the left
        timeclock_y = d20_rect.bottom + 40
        timeclock_settings = layout.get('timeclock', {})
        timeclock_height = timeclock_settings.get('height', 300)
        timeclock_width = right_col_width + 50  # Extend by 50px
        timeclock_x = right_col_x - 50  # Shift 50px to the left
        draw_timeclock(
            surface=screen,
            x=timeclock_x,
            y=timeclock_y,
            width=timeclock_width,
            height=timeclock_height,
            theme={'style': style, 'layout': layout}
        )
        
        # Draw wake word indicator (red dot in top-right corner)
        if self.wake_word_detected_time is not None:
            elapsed = time.time() - self.wake_word_detected_time
            if elapsed < self.wake_word_indicator_duration:
                # Draw pulsing red dot
                pulse = 0.5 + 0.5 * abs((elapsed % 0.5) - 0.25) / 0.25  # Pulse between 0.5 and 1.0
                dot_radius = int(15 * pulse)
                dot_x = screen.get_width() - 30
                dot_y = 30
                pygame.draw.circle(screen, (255, 0, 0), (dot_x, dot_y), dot_radius)
                # Draw outer ring
                pygame.draw.circle(screen, (255, 100, 100), (dot_x, dot_y), dot_radius + 3, 2)
            else:
                # Clear the indicator after duration
                self.wake_word_detected_time = None
        
        # Draw scanlines and footer
        draw_scanlines(screen)
        draw_footer(screen, self.color)
