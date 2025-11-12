#!/usr/bin/env python3
"""D20 3D widget component with physics simulation."""

import os
import threading
import time
from pathlib import Path

import pygame
from pygame import Surface

from ..icons import load_icon

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
                from nrhof.renderers.model_renderer import ModelRenderer

                print(f"Initializing 3D renderer (version {_d20_renderer_version})...")
                renderer = ModelRenderer(width=512, height=512)

                # Load D20 model
                # Go up from nrhof/ui/components/d20.py to project root
                model_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
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
        # Go up from nrhof/ui/components/d20.py to project root
        d20_path = Path(__file__).parent.parent.parent.parent / "assets" / "images" / "d20.svg"
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
            Path(__file__).parent.parent.parent.parent
            / "assets"
            / "images"
            / "speech_synthesizer.svg"
        )
        if speech_path.exists():
            speech_surface = load_icon(speech_path, (width, speech_height), fill_color=dim_color)
            if speech_surface:
                speech_rect = speech_surface.get_rect()
                speech_x = x + (width - speech_rect.width) // 2
                surface.blit(speech_surface, (speech_x, speech_y))

    return pygame.Rect(x, y, width, height)
