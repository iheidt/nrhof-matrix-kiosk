#!/usr/bin/env python3
"""Widget components - timeclock, d20, now playing."""

import os
import time
from pathlib import Path

import pygame
from pygame import Surface

from ..components.primary_card import draw_card
from ..icons import load_icon

# Font cache to prevent reloading on every frame (with max size limit)
_font_cache = {}
_FONT_CACHE_MAX_SIZE = 20  # Reasonable limit for widget fonts


def evict_widget_font_cache():
    """Clear the widget font cache.

    This should be called during scene cleanup to prevent memory leaks.
    Clears the _font_cache dict (maxsize=20) used by timeclock and now_playing widgets.
    """
    global _font_cache
    _font_cache.clear()


class MarqueeText:
    """Manages scrolling text animation for text that's too long to fit."""

    def __init__(self, text: str, max_width: int, scroll_speed: float = 50.0, gap: int = 100):
        """Initialize marquee text.

        Args:
            text: Text to scroll
            max_width: Maximum width before scrolling
            scroll_speed: Pixels per second to scroll
            gap: Gap in pixels between end and start of loop
        """
        self.text = text
        self.max_width = max_width
        self.scroll_speed = scroll_speed
        self.gap = gap

        self.offset = 0.0
        self.last_update = time.time()

    def update(self, text_width: int) -> tuple[int, bool]:
        """Update scroll position and return current offset.

        Args:
            text_width: Actual rendered width of the text

        Returns:
            Tuple of (current x offset, should_draw_second_copy)
        """
        current_time = time.time()

        # If text fits, no scrolling needed
        if text_width <= self.max_width:
            return 0, False

        # Calculate delta time
        dt = current_time - self.last_update
        self.last_update = current_time

        # Update offset (scroll left = increase offset)
        self.offset += self.scroll_speed * dt

        # Loop when text has scrolled completely off screen
        loop_point = text_width + self.gap
        if self.offset >= loop_point:
            self.offset -= loop_point

        # Determine if we need to draw a second copy for seamless loop
        draw_second = self.offset > 0

        return int(self.offset), draw_second

    def reset(self, new_text: str = None):
        """Reset marquee to beginning.

        Args:
            new_text: Optional new text to display
        """
        if new_text is not None:
            self.text = new_text
        self.offset = 0.0
        self.last_update = time.time()


def draw_timeclock(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    theme: dict = None,
) -> pygame.Rect:
    """Draw timeclock component with card border and live time/date.

    Args:
        surface: Surface to draw on
        x: X position
        y: Y position
        width: Card width
        height: Card height
        theme: Theme dict with style

    Returns:
        Rect of the component
    """
    if theme is None:
        theme = {}
    style = theme.get("style", {})
    layout = theme.get("layout", {})

    # Get colors
    primary_color = tuple(style.get("colors", {}).get("primary", (255, 20, 147)))
    dim_color_hex = style["colors"].get("dim", "#2C405B")
    if isinstance(dim_color_hex, str) and dim_color_hex.startswith("#"):
        dim_color = tuple(int(dim_color_hex[i : i + 2], 16) for i in (1, 3, 5))
    else:
        dim_color = (
            tuple(dim_color_hex) if isinstance(dim_color_hex, list | tuple) else (44, 64, 91)
        )

    # Get timeclock settings from layout
    timeclock_settings = layout.get("timeclock", {})
    border_fade_pct = timeclock_settings.get("border_fade_pct", 0.9)
    border_height_pct = timeclock_settings.get("border_height_pct", 1.0)

    # Draw card border with fade (top solid, bottom/sides fade)
    draw_card(
        surface,
        x,
        y,
        width,
        height,
        theme=theme,
        border_solid="top",
        border_fade_pct=border_fade_pct,
        border_height_pct=border_height_pct,
    )

    # Get current time and date
    from datetime import datetime

    now = datetime.now()

    # Format time
    from core.localization import t
    from ui.fonts import get_localized_font

    # Get localized AM/PM
    hour = now.hour
    if hour < 12:
        ampm = t("common.am")
    else:
        ampm = t("common.pm")

    time_str = now.strftime("%I:%M")  # 05:30 (with leading zero)

    # Load fonts with localization support
    # AM/PM: Miland 30px (maps to Dela Gothic One for Japanese)
    ampm_font = get_localized_font(30, "secondary", ampm)

    # Time: IBM Plex Semibold Italic 124px (display size) - cached
    time_cache_key = "timeclock_time_124"
    if time_cache_key not in _font_cache:
        # Evict oldest entry if cache is full
        if len(_font_cache) >= _FONT_CACHE_MAX_SIZE:
            _font_cache.pop(next(iter(_font_cache)))
        time_font_path = (
            Path(__file__).parent.parent.parent
            / "assets"
            / "fonts"
            / "IBMPlexMono-SemiBoldItalic.ttf"
        )
        _font_cache[time_cache_key] = pygame.font.Font(str(time_font_path), 124)
    time_font = _font_cache[time_cache_key]

    # Render text
    ampm_surface = ampm_font.render(ampm, True, dim_color)
    time_surface = time_font.render(time_str, True, primary_color)

    # Layout with 24px top padding
    padding = 24

    # AM/PM right-justified with padding
    ampm_x = x + width - padding - ampm_surface.get_width()
    ampm_y = y + padding
    surface.blit(ampm_surface, (ampm_x, ampm_y))

    # Time centered horizontally, 10px below AM/PM, moved up 48px
    time_x = x + (width - time_surface.get_width()) // 2
    time_y = ampm_y + ampm_surface.get_height() - 25
    surface.blit(time_surface, (time_x, time_y))

    return pygame.Rect(x, y, width, height)


# Global 3D renderer instance (initialized once)
_d20_renderer = None
_d20_init_attempted = False  # Prevent repeated init attempts on failure
_d20_renderer_version = 2  # Increment to force reload with new settings
# North star - the ideal state to return to (spins around vertical axis like a planet)
_d20_north_star_h = 0.0  # Target heading (no rotation around Y)
_d20_north_star_p = 20.0  # Target pitch (tilted to show "north pole")
_d20_north_star_r = 0.0  # Target roll (this will spin)
_d20_north_star_spin = 30.0  # Target spin velocity around Z-axis (degrees/sec)
# Current state
_d20_rotation_h = 0.0  # Current heading (yaw)
_d20_rotation_p = 20.0  # Current pitch (tilted)
_d20_rotation_r = 0.0  # Current roll (spins around vertical)
_d20_velocity_h = 0.0  # Angular velocity heading
_d20_velocity_p = 0.0  # Angular velocity pitch
_d20_velocity_r = 30.0  # Angular velocity roll (spinning around vertical)
_d20_last_update = None  # Last update time
_d20_drag_start = None  # Mouse drag start position
_d20_drag_last_pos = None  # Last mouse position during drag
_d20_drag_last_time = None  # Last time during drag
_d20_bounds = None  # D20 display bounds for hit testing
_d20_is_dragging = False  # Currently being dragged
_d20_last_interaction = None  # Time of last user interaction


def draw_d20(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    height: int = 300,
    theme: dict = None,
) -> pygame.Rect:
    """Draw 3D rendered d20 component with speech_synthesizer below it.

    Args:
        surface: Surface to draw on
        x: X position
        y: Y position
        width: Container width
        height: Container height (default 300px)
        theme: Theme dict with style

    Returns:
        Rect of the component
    """
    global _d20_renderer, _d20_init_attempted
    global _d20_rotation_h, _d20_rotation_p, _d20_rotation_r
    global _d20_velocity_h, _d20_velocity_p, _d20_velocity_r
    global _d20_north_star_h, _d20_north_star_p, _d20_north_star_r, _d20_north_star_spin
    global _d20_last_update, _d20_drag_start, _d20_drag_last_pos, _d20_drag_last_time
    global _d20_bounds, _d20_is_dragging, _d20_last_interaction
    import time

    if theme is None:
        theme = {}
    style = theme.get("style", {})

    # Get primary color for d20
    primary_color = tuple(style.get("colors", {}).get("primary", (255, 20, 147)))
    primary_hex = "#{:02x}{:02x}{:02x}".format(*primary_color)

    # Get dim color for speech synthesizer
    dim_hex = style["colors"].get("dim", "#2C405B")
    if isinstance(dim_hex, str) and dim_hex.startswith("#"):
        dim_color = tuple(int(dim_hex[i : i + 2], 16) for i in (1, 3, 5))
    else:
        dim_color = tuple(dim_hex) if isinstance(dim_hex, list | tuple) else (44, 64, 91)

    # Calculate space for d20 (leaving room for speech synth + margin)
    speech_height = 40
    margin = 20
    d20_available_height = height - speech_height - margin

    # Initialize 3D renderer if needed (only try once per version)
    if _d20_renderer is None and not _d20_init_attempted:
        _d20_init_attempted = True

        # Initialize in background thread to avoid blocking main thread
        def _init_renderer():
            global _d20_renderer
            try:
                from renderers.model_renderer import ModelRenderer

                print(f"Initializing 3D renderer (version {_d20_renderer_version})...")
                renderer = ModelRenderer(width=512, height=512)

                # Load D20 model
                model_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "models",
                    "d21.glb",
                )
                if os.path.exists(model_path):
                    renderer.load_model(model_path)
                    renderer.set_rotation(h=45, p=15, r=0)  # Nice viewing angle
                    _d20_renderer = renderer  # Only set if successful
                    print("✓ 3D renderer initialized successfully")
                else:
                    print(f"Warning: D20 model not found at {model_path}")
            except Exception as e:
                print(f"Warning: Could not initialize 3D renderer: {e}")

        import threading

        thread = threading.Thread(target=_init_renderer, daemon=True)
        thread.start()

    # Render 3D D20 or fall back to SVG
    d20_surface = None

    if _d20_renderer is not None:
        try:
            import numpy as np

            # Physics-based rotation system
            current_time = time.time()
            if _d20_last_update is None:
                _d20_last_update = current_time
            dt = current_time - _d20_last_update
            _d20_last_update = current_time

            # Handle mouse/touch input
            mouse_buttons = pygame.mouse.get_pressed()
            mouse_pos = pygame.mouse.get_pos()

            # Check if mouse is over D20 and handle drag
            if _d20_bounds and _d20_bounds.collidepoint(mouse_pos):
                if mouse_buttons[0]:  # Left click/touch
                    if not _d20_is_dragging:
                        # Start drag
                        _d20_drag_start = mouse_pos
                        _d20_drag_last_pos = mouse_pos
                        _d20_drag_last_time = current_time
                        _d20_is_dragging = True
                        _d20_last_interaction = current_time
                        # Zero out velocity when grabbed
                        _d20_velocity_h *= 0.3  # Dampen existing velocity
                        _d20_velocity_p *= 0.3
                        _d20_velocity_r *= 0.3
                    else:
                        # Continue drag - direct manipulation
                        if _d20_drag_last_pos:
                            dx = mouse_pos[0] - _d20_drag_last_pos[0]
                            dy = mouse_pos[1] - _d20_drag_last_pos[1]

                            # Apply rotation based on drag delta
                            # Horizontal drag affects heading and roll (combined)
                            _d20_rotation_h += dx * 0.3
                            _d20_rotation_r += dx * 0.3
                            # Vertical drag affects pitch
                            _d20_rotation_p -= dy * 0.5

                            # Calculate velocity for momentum on release
                            time_delta = current_time - _d20_drag_last_time
                            if time_delta > 0:
                                _d20_velocity_h = (dx * 0.3) / time_delta
                                _d20_velocity_r = (dx * 0.3) / time_delta
                                _d20_velocity_p = (-dy * 0.5) / time_delta

                            _d20_drag_last_pos = mouse_pos
                            _d20_drag_last_time = current_time
                else:
                    if _d20_is_dragging:
                        # Just released - apply momentum
                        # Velocity is already set from drag
                        _d20_is_dragging = False
                        _d20_drag_start = None
                        _d20_drag_last_pos = None
                        _d20_last_interaction = current_time
            else:
                if _d20_is_dragging:
                    # Released outside bounds
                    _d20_is_dragging = False
                    _d20_drag_start = None
                    _d20_drag_last_pos = None
                    _d20_last_interaction = current_time

            # Physics simulation when not dragging - Pixar-quality smooth rotation
            if not _d20_is_dragging:
                # Apply velocity to rotation (integrate)
                _d20_rotation_h += _d20_velocity_h * dt
                _d20_rotation_p += _d20_velocity_p * dt
                _d20_rotation_r += _d20_velocity_r * dt

                # Very gentle damping (space-like environment)
                damping = 0.995  # Almost no damping for floaty feel
                _d20_velocity_h *= damping
                _d20_velocity_p *= damping
                _d20_velocity_r *= damping

                # Calculate time since last interaction
                time_since_interaction = (
                    current_time - _d20_last_interaction if _d20_last_interaction else 999
                )

                # Helper function for shortest angle difference
                def angle_diff(current, target):
                    diff = (target - current + 180) % 360 - 180
                    return diff

                # North star attractor with ease-in-out
                attractor_delay = 2.0  # Wait 2 seconds
                attractor_ramp = 4.0  # Ramp up over 4 seconds

                if time_since_interaction > attractor_delay:
                    # Smooth ease-in-out curve (Pixar principle: slow in, slow out)
                    t = min(1.0, (time_since_interaction - attractor_delay) / attractor_ramp)
                    # Cubic ease-in-out
                    if t < 0.5:
                        ease = 2 * t * t
                    else:
                        ease = 1 - pow(-2 * t + 2, 2) / 2

                    attractor_strength = ease * 0.15  # Gentle max strength

                    # Apply spring forces toward north star (heading and pitch only)
                    h_diff = angle_diff(_d20_rotation_h, _d20_north_star_h)
                    p_diff = angle_diff(_d20_rotation_p, _d20_north_star_p)

                    # Gentle spring: F = -k * x - c * v (spring + damping)
                    spring_k = attractor_strength * 2.0
                    spring_c = attractor_strength * 0.5

                    _d20_velocity_h += (h_diff * spring_k - _d20_velocity_h * spring_c) * dt
                    _d20_velocity_p += (p_diff * spring_k - _d20_velocity_p * spring_c) * dt

                    # Guide roll velocity toward target spin (very gentle)
                    velocity_diff = _d20_north_star_spin - _d20_velocity_r
                    _d20_velocity_r += velocity_diff * attractor_strength * dt
                else:
                    # Free spinning phase - minimal stabilization
                    # Only stabilize heading and pitch if they drift too far
                    h_diff = angle_diff(_d20_rotation_h, _d20_north_star_h)
                    p_diff = angle_diff(_d20_rotation_p, _d20_north_star_p)

                    # Very weak stabilization (only if drifting significantly)
                    if abs(h_diff) > 30.0:
                        _d20_velocity_h += h_diff * 0.05 * dt
                    if abs(p_diff) > 30.0:
                        _d20_velocity_p += p_diff * 0.05 * dt

                    # Maintain roll spin - gentle acceleration if slowing down
                    if abs(_d20_velocity_r) < 25.0:
                        target_spin = (
                            _d20_north_star_spin if _d20_velocity_r >= 0 else -_d20_north_star_spin
                        )
                        accel = (target_spin - _d20_velocity_r) * 0.3
                        _d20_velocity_r += accel * dt

            # Keep angles in 0-360 range
            _d20_rotation_h %= 360.0
            _d20_rotation_p %= 360.0
            _d20_rotation_r %= 360.0

            # Set emission matching sandbox (0.41 intensity with theme color)
            _d20_renderer.set_emission_strength(
                2.5,
                primary_hex,
            )  # Moderate glow (scaled from 0.41)
            _d20_renderer.set_spotlight_color(primary_hex)  # Match main light to theme

            # Update rotation
            _d20_renderer.set_rotation(h=_d20_rotation_h, p=_d20_rotation_p, r=_d20_rotation_r)

            # Render EVERY frame (no caching)
            pixels = _d20_renderer.render_frame()

            if pixels:
                # Convert to pygame surface with proper alpha
                arr = np.frombuffer(pixels, dtype=np.uint8).reshape((512, 512, 4))

                # Create surface with per-pixel alpha
                d20_surface = pygame.Surface((512, 512), pygame.SRCALPHA)

                # Use surfarray to set pixels with alpha
                pygame.surfarray.pixels_alpha(d20_surface)[:] = arr[:, :, 3].swapaxes(0, 1)
                rgb_array = arr[:, :, :3].swapaxes(0, 1)
                pygame.surfarray.pixels3d(d20_surface)[:] = rgb_array

                # Scale to fit available height
                scale_factor = d20_available_height / 512
                new_size = (int(512 * scale_factor), int(512 * scale_factor))
                d20_surface = pygame.transform.smoothscale(d20_surface, new_size)

        except Exception as e:
            print(f"Warning: 3D rendering failed: {e}")
            d20_surface = None

    # Fallback to SVG if 3D rendering failed
    if d20_surface is None:
        d20_path = Path(__file__).parent.parent.parent / "assets" / "images" / "d20.svg"
        if d20_path.exists():
            d20_surface = load_icon(
                d20_path,
                (width, d20_available_height),
                fill_color=primary_color,
            )

    if d20_surface:
        # Center the d20 horizontally at top of container
        d20_rect = d20_surface.get_rect()
        d20_x = x + (width - d20_rect.width) // 2
        d20_y = y
        surface.blit(d20_surface, (d20_x, d20_y))

        # Store bounds for hit testing
        _d20_bounds = pygame.Rect(d20_x, d20_y, d20_rect.width, d20_rect.height)

        # Draw speech_synthesizer below d20 with 30px margin
        speech_y = d20_y + d20_rect.height + margin
        speech_path = (
            Path(__file__).parent.parent.parent / "assets" / "images" / "speech_synthesizer.svg"
        )
        if speech_path.exists():
            speech_surface = load_icon(speech_path, (width, speech_height), fill_color=dim_color)
            if speech_surface:
                speech_rect = speech_surface.get_rect()
                speech_x = x + (width - speech_rect.width) // 2
                surface.blit(speech_surface, (speech_x, speech_y))

    return pygame.Rect(x, y, width, height)


def draw_now_playing(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    title: str = "NOW PLAYING",
    line1: str = "",
    line2: str = "",
    theme: dict = None,
    border_y: int = None,
    marquee: MarqueeText = None,
    progress_ms: int = None,
    duration_ms: int = None,
    is_playing: bool = False,
    fade_amount: float = 0.0,
) -> pygame.Rect:
    """Draw a 'Now Playing' component with title, border, and two body lines.

    Args:
        surface: Pygame surface to draw on
        x, y: Component position (top-left)
        width: Component width
        title: Title text (default: "NOW PLAYING")
        line1: First body line (song/artist)
        line2: Second body line (rank info)
        theme: Dict with 'layout' and 'style' keys
        border_y: Optional override for border Y position
        marquee: Optional MarqueeText instance for line1 scrolling

    Returns:
        pygame.Rect of the entire component
    """
    from core.theme_loader import get_theme_loader

    # Load theme if not provided
    if theme is None:
        theme_loader = get_theme_loader()
        style = theme_loader.load_style("pipboy")
    else:
        style = theme.get("style", theme)

    # Colors
    primary_color = tuple(style["colors"].get("primary", (233, 30, 99)))
    dim_color = tuple(style["colors"].get("dim", (100, 100, 100)))  # Dim/muted color
    title_color = primary_color
    bg_color_hex = "#1797CD"
    # Convert hex to RGB with 33% alpha
    bg_r = int(bg_color_hex[1:3], 16)
    bg_g = int(bg_color_hex[3:5], 16)
    bg_b = int(bg_color_hex[5:7], 16)
    bg_alpha = int(255 * 0.33)

    # Border
    border_width = 6

    # Calculate progress percentage
    progress_pct = 0.0
    if is_playing and progress_ms is not None and duration_ms and duration_ms > 0:
        progress_pct = min(1.0, progress_ms / duration_ms)

    # Animate border color fade (primary -> dim when playing)
    # Interpolate between primary and dim based on fade_amount
    if fade_amount > 0:
        # Linear interpolation between colors
        border_color = tuple(
            int(primary_color[i] + (dim_color[i] - primary_color[i]) * fade_amount)
            for i in range(3)
        )
    else:
        border_color = primary_color

    # Fonts - cached to prevent loading every frame
    # Title: Compadre Extended (label_font), label size (16)
    title_font_size = style["typography"]["fonts"].get("label", 16)
    title_cache_key = f"now_playing_title_{title_font_size}"
    if title_cache_key not in _font_cache:
        # Evict oldest entry if cache is full
        if len(_font_cache) >= _FONT_CACHE_MAX_SIZE:
            _font_cache.pop(next(iter(_font_cache)))
        title_font_path = (
            Path(__file__).parent.parent.parent / "assets" / "fonts" / "Compadre-Extended.otf"
        )
        _font_cache[title_cache_key] = pygame.font.Font(str(title_font_path), title_font_size)
    title_font = _font_cache[title_cache_key]

    # Line 1: IBM Plex Mono Italic, body size (48)
    line1_font_size = style["typography"]["fonts"].get("body", 48)
    line1_cache_key = f"now_playing_line1_{line1_font_size}"
    if line1_cache_key not in _font_cache:
        # Evict oldest entry if cache is full
        if len(_font_cache) >= _FONT_CACHE_MAX_SIZE:
            _font_cache.pop(next(iter(_font_cache)))
        line1_font_path = (
            Path(__file__).parent.parent.parent / "assets" / "fonts" / "IBMPlexMono-Italic.ttf"
        )
        _font_cache[line1_cache_key] = pygame.font.Font(str(line1_font_path), line1_font_size)
    line1_font = _font_cache[line1_cache_key]

    # Render title
    title_surface = title_font.render(title, True, title_color)
    title_height = title_surface.get_height()

    # Calculate component dimensions
    padding = 24  # Internal padding

    # If border_y parameter is provided, use it directly and calculate title_y backwards
    if border_y is not None:
        calculated_border_y = border_y
        title_y = border_y - title_height - 6  # 6px gap between title and border
    else:
        title_y = y
        calculated_border_y = title_y + title_height + 6  # 6px gap between title and border

    content_y = calculated_border_y + border_width  # Content starts immediately after border

    # Calculate background width (40px narrower from right)
    bg_width = width - 40
    max_text_width = bg_width - (padding * 2)

    # Render line1 (with marquee support)
    line1_surface = None
    line1_offset = 0
    draw_second_copy = False

    if line1:
        # Render full text with localization support
        from ui.fonts import render_localized_text

        # Use render_localized_text with automatic font detection
        # English chars use IBM Plex Mono Italic, Japanese chars use Noto Sans JP
        line1_surface = render_localized_text(
            line1,
            line1_font_size,
            "primary",
            title_color,
        )
        line1_width = line1_surface.get_width()

        # Use marquee if text is too wide and marquee is provided
        if marquee and line1_width > max_text_width:
            # Update marquee text if changed
            if marquee.text != line1:
                marquee.reset(line1)
            line1_offset, draw_second_copy = marquee.update(line1_width)
            line1_offset = -line1_offset  # Negative for left scroll
        elif line1_width > max_text_width:
            # No marquee provided, truncate with ellipsis
            truncated = line1
            while (
                truncated
                and render_localized_text(
                    truncated + "...",
                    line1_font_size,
                    "primary",
                    title_color,
                    english_font=line1_font,
                ).get_width()
                > max_text_width
            ):
                truncated = truncated[:-1]
            line1_surface = render_localized_text(
                truncated + "...",
                line1_font_size,
                "primary",
                title_color,
                english_font=line1_font,
            )

    # Fixed content height (set to match Japanese text height for consistency)
    # This prevents the container from resizing when switching between English and Japanese
    top_padding = 5
    bottom_padding = 22
    # Use fixed height based on maximum text height (Japanese characters)
    # This ensures the box doesn't shift in size during state transitions
    content_height = (
        top_padding + 58 + bottom_padding
    )  # 5 + 58 (max Japanese text height) + 13 = 76

    # Total component height
    total_height = (calculated_border_y - title_y) + border_width + content_height

    # Draw background box (with alpha) - 40px narrower from right
    bg_surface = pygame.Surface((bg_width, content_height), pygame.SRCALPHA)
    bg_surface.fill((bg_r, bg_g, bg_b, bg_alpha))
    surface.blit(bg_surface, (x, content_y))

    # Draw border (secondary color when playing)
    pygame.draw.rect(surface, border_color, (x, calculated_border_y, width, border_width), 0)

    # Draw progress bar overlay (primary color) if playing
    if is_playing:
        # Calculate progress width (stop before circle starts)
        circle_size = 80
        circle_left_edge = x + width - circle_size  # Where circle actually starts
        max_progress_width = circle_left_edge - x
        progress_width = int(max_progress_width * progress_pct)

        # Draw primary progress bar on top of dim border
        if progress_width > 0:
            pygame.draw.rect(
                surface,
                primary_color,
                (x, calculated_border_y, progress_width, border_width),
                0,
            )

    # Draw title
    surface.blit(title_surface, (x, title_y))

    # Draw body lines with explicit top padding
    text_x = x + padding
    if line1_surface:
        # Use explicit top padding (20px)
        text_y = content_y + top_padding
    else:
        text_y = content_y + top_padding

    if line1_surface:
        # Create a clipping rect for marquee scrolling
        clip_rect = pygame.Rect(text_x, text_y, max_text_width, line1_surface.get_height())
        surface.set_clip(clip_rect)

        # Draw first copy
        surface.blit(line1_surface, (text_x + line1_offset, text_y))

        # Draw second copy for seamless loop if needed
        if draw_second_copy and marquee:
            second_x = text_x + line1_offset + line1_surface.get_width() + marquee.gap
            surface.blit(line1_surface, (second_x, text_y))

        surface.set_clip(None)  # Reset clipping

    # Draw circle element (80x80px) aligned with border
    circle_size = 80
    circle_border = 6
    circle_x = x + width - (circle_size // 2)  # Right edge, half overlapping
    circle_y = (
        calculated_border_y - (circle_size // 2) + (border_width // 2) + 40
    )  # Centered on border, moved down 40px

    # Draw outer circle (border) - use same color as top border
    pygame.draw.circle(surface, border_color, (circle_x, circle_y), circle_size // 2, 0)

    # Draw inner circle (background fill)
    bg_color_solid = tuple(style["colors"].get("background", (0, 0, 0)))
    inner_radius = (circle_size // 2) - circle_border
    pygame.draw.circle(surface, bg_color_solid, (circle_x, circle_y), inner_radius, 0)

    # Load and draw SVG icon (40x40px)
    icon_path = Path(__file__).parent.parent.parent / "assets" / "images" / "icon_happysad.svg"
    if icon_path.exists():
        icon_surface = load_icon(icon_path, (40, 40), fill_color=title_color)
        if icon_surface:
            icon_x = circle_x - 20  # Center 40px icon
            icon_y = circle_y - 20
            surface.blit(icon_surface, (icon_x, icon_y))
        else:
            print(f"Warning: Failed to load icon from {icon_path}")
    else:
        print(f"Warning: Icon not found at {icon_path}")

    return pygame.Rect(x, y, width, total_height)
