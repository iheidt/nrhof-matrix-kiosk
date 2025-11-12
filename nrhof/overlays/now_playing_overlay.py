"""Now Playing overlay for NRHOF.

Provides a global overlay that displays the currently playing track
in the top-right corner of the screen.
"""

import time

import pygame

from nrhof.core.localization import t
from nrhof.core.now_playing import get_now_playing_state
from nrhof.core.theme_loader import get_theme_loader
from nrhof.ui.components.marquee import MarqueeText
from nrhof.ui.components.now_playing import draw_now_playing

# Global state for Now Playing overlay
_now_playing_marquee = None
_last_track_id = None
_last_progress_time = None
_last_progress_ms = None

# Fade transition tracking
_playback_state_start_time = None
_is_in_playback_state = False
_fade_delay = 1.0  # Delay before starting fade to dim (seconds)
_fade_back_delay = 0.3  # Delay before fading back to primary (seconds)
_fade_duration = 1.0  # Fade duration (seconds) - increased for smoother transition


def draw_now_playing_overlay(screen: pygame.Surface, cfg: dict):
    """Draw Now Playing widget as a global overlay in top-right corner.

    Args:
        screen: Pygame surface to draw on
        cfg: Application config
    """
    global _now_playing_marquee, _last_track_id, _last_progress_time, _last_progress_ms
    global \
        _playback_state_start_time, \
        _is_in_playback_state, \
        _fade_delay, \
        _fade_duration, \
        _fade_back_delay

    # Get theme
    theme_loader = get_theme_loader()
    style = theme_loader.load_style("pipboy")

    # Position in top-right with 50px margins
    margin_top = 110
    margin_right = 40
    widget_width = 416

    screen_width = screen.get_width()
    x = screen_width - widget_width - margin_right  # Extends 39px more to the left
    y = margin_top

    # Get current track
    now_playing = get_now_playing_state()
    track = now_playing.get_track()

    # Determine title based on source
    if track:
        if track.source == "spotify":
            device = track.device_name if track.device_name else "unknown"
            device_formatted = (
                device.upper()
                .replace("-", ".")
                .replace("'", "")
                .replace("'", "")
                .replace("'", "")
                .replace(chr(8217), "")
            )
            now_playing_title = f"SPOTIFY . {device_formatted}"
        elif track.source == "sonos":
            room = track.sonos_room if track.sonos_room else "unknown"
            room_formatted = (
                room.upper()
                .replace("-", ".")
                .replace("'", "")
                .replace("'", "")
                .replace("'", "")
                .replace(chr(8217), "")
            )
            now_playing_title = f"SONOS . {room_formatted}"
        elif track.source == "vinyl":
            now_playing_title = "RECORD PLAYER"
        else:
            now_playing_title = "NOW PLAYING"

        # Truncate title
        if len(now_playing_title) > 22:
            now_playing_title = now_playing_title[:19] + "..."
    else:
        now_playing_title = "NOW PLAYING"

    # Format track info
    if track:
        artist = track.artist.lower() if track.artist else "unknown artist"
        title = track.title.lower() if track.title else "unknown song"
        song_line = f"{artist} • {title}"

        if track.source == "sonos" and track.sonos_room:
            album_line = f"{track.sonos_room.lower()}"
            if track.sonos_grouped_rooms:
                album_line += f" + {len(track.sonos_grouped_rooms)} more"
        else:
            album_line = track.album.lower() if track.album else f"via {track.source}"
    else:
        song_line = t("now_playing.listening")
        album_line = t("now_playing.none_playing")

    # Initialize marquee if needed
    max_text_width = widget_width - 40 - (24 * 2)
    if _now_playing_marquee is None:
        _now_playing_marquee = MarqueeText(song_line, max_text_width, scroll_speed=50.0, gap=100)

    # Get playback progress with client-side interpolation
    progress_ms = None
    duration_ms = None
    is_playing = False
    fade_amount = 0.0

    if track:
        duration_ms = track.duration_ms
        is_playing = track.is_playing

        track_id = f"{track.title}_{track.artist}_{track.source}"

        # Track change detection
        if track_id != _last_track_id:
            _last_track_id = track_id
            _last_progress_time = None
            _last_progress_ms = None
            if _now_playing_marquee:
                _now_playing_marquee.reset(song_line)

        # Progress interpolation
        if track.progress_ms is not None:
            current_time = time.time()

            if _last_progress_time is None:
                _last_progress_time = current_time
                _last_progress_ms = track.progress_ms

            time_delta = current_time - _last_progress_time

            if abs(track.progress_ms - _last_progress_ms) > 2000:
                _last_progress_ms = track.progress_ms
                _last_progress_time = current_time

            if is_playing:
                progress_ms = _last_progress_ms + int(time_delta * 1000)
            else:
                progress_ms = _last_progress_ms

            if duration_ms and progress_ms > duration_ms:
                progress_ms = duration_ms

        # Track playback state changes for fade transition
        current_time_fade = time.time()
        if is_playing and not _is_in_playback_state:
            # Just started playing
            _is_in_playback_state = True
            _playback_state_start_time = current_time_fade
        elif not is_playing and _is_in_playback_state:
            # Just stopped playing
            _is_in_playback_state = False
            _playback_state_start_time = current_time_fade

        # Calculate fade amount (0.0 = primary, 1.0 = dim)
        if _playback_state_start_time is not None:
            elapsed = current_time_fade - _playback_state_start_time

            if is_playing:
                # Fading to dim (playing state)
                if elapsed < _fade_delay:
                    # Still in delay period, stay at primary
                    fade_amount = 0.0
                else:
                    # Fade from primary to dim
                    fade_progress = min(1.0, (elapsed - _fade_delay) / _fade_duration)
                    fade_amount = fade_progress
            else:
                # Fading back to primary (stopped state) - with delay for smoother transition
                if elapsed < _fade_back_delay:
                    # Stay at dim during delay period
                    fade_amount = 1.0
                else:
                    # Fade from dim back to primary
                    fade_progress = min(1.0, (elapsed - _fade_back_delay) / _fade_duration)
                    fade_amount = 1.0 - fade_progress  # Reverse: 1.0 -> 0.0
    else:
        # No track - trigger fade back to primary if we were in playback state
        if _is_in_playback_state:
            _is_in_playback_state = False
            _playback_state_start_time = time.time()
        elif _playback_state_start_time is not None:
            # Continue fade animation with delay
            elapsed = time.time() - _playback_state_start_time
            if elapsed < _fade_back_delay:
                # Stay at dim during delay period
                fade_amount = 1.0
            else:
                # Fade from dim back to primary
                fade_progress = min(1.0, (elapsed - _fade_back_delay) / _fade_duration)
                fade_amount = 1.0 - fade_progress

            # Reset state after fade completes
            if elapsed >= (_fade_back_delay + _fade_duration):
                _playback_state_start_time = None

    # Draw the widget
    draw_now_playing(
        surface=screen,
        x=x,
        y=y,
        width=widget_width,
        title=now_playing_title,
        line1=song_line,
        line2=album_line,
        theme={"style": style},
        marquee=_now_playing_marquee,
        progress_ms=progress_ms,
        duration_ms=duration_ms,
        is_playing=is_playing,
        fade_amount=fade_amount,
    )
