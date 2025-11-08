#!/usr/bin/env python3
import time

import pygame

from core.event_bus import EventType, get_event_bus
from core.localization import get_language
from core.theme_loader import get_theme_loader
from renderers import FrameState
from routing.intent_router import Intent
from scenes.scene_manager import Scene, register_scene
from ui.components import (
    MARGIN_LEFT,
    draw_button,
    draw_footer,
    draw_scanlines,
    draw_title_card_container,
)
from ui.components.widgets import draw_d20, draw_timeclock
from ui.fonts import get_theme_font


@register_scene("MenuScene")
class MenuScene(Scene):
    """Menu selection scene with 3 options."""

    def __init__(self, manager):
        super().__init__(manager)

        # Load theme (content + layout + style)
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme("menu", theme_name="pipboy")

        # Extract from theme
        self.entries = self.theme["content"]["items"]
        self.color = tuple(self.theme["style"]["colors"]["primary"])
        self.bg = tuple(self.theme["style"]["colors"]["background"])

        # Layout vars (will be calculated in on_enter)
        self.button_rects = []  # Store button rectangles for click detection
        self.button_spacing = 0
        self.button_start_y = 0
        self.settings_rect = None  # Store settings text rect for click detection

        # Wake word detection indicator
        self.wake_word_detected_time = None
        self.wake_word_indicator_duration = 2.0  # Show red dot for 2 seconds

        # Subscribe to wake word events
        event_bus = get_event_bus()
        event_bus.subscribe(EventType.WAKE_WORD_DETECTED, self._on_wake_word_detected)

    def _on_wake_word_detected(self, **kwargs):
        """Handle wake word detection event."""
        keyword = kwargs.get("keyword", "unknown")
        print(f"[MENU] Wake word detected: {keyword}")
        self.wake_word_detected_time = time.time()

    def on_enter(self):
        """Initialize menu display."""
        # Content and colors already loaded from theme in __init__

        w, h = self.manager.screen.get_size()

        # Get layout from theme
        layout = self.theme["layout"]
        self.theme["style"]

        # Get margins and calculate usable area
        margins = layout.get("margins", {})
        margin_left = margins.get("left", 50)
        margins.get("right", 50)
        margin_top = margins.get("top", 50)
        margin_bottom = margins.get("bottom", 130)

        # Calculate two-column layout
        columns = layout.get("columns", {})
        left_col_width = columns.get("left", {}).get("width", 715)
        right_col_width = columns.get("right", {}).get("width", 415)
        col_gutter = columns.get("gutter", 50)

        # Column x positions
        self.left_col_x = margin_left
        self.left_col_width = left_col_width
        self.right_col_x = margin_left + left_col_width + col_gutter
        self.right_col_width = right_col_width

        # Usable height (excluding top margin and footer)
        self.content_top = margin_top
        self.content_height = h - margin_top - margin_bottom

        # Button layout - vertical in left column
        button_config = layout.get("buttons", {})
        self.button_spacing = button_config.get("spacing", 30)
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
                # Return to intro (no transition for intro scene)
                self.manager.switch_to("IntroScene", use_transition=False)
                return True
            elif event.key == pygame.K_w:
                # Trigger wakeword for testing
                self.trigger_wakeword()
                return True
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.ctx.intent_router.emit(Intent.SELECT_OPTION, index=0)
                return True
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.ctx.intent_router.emit(Intent.SELECT_OPTION, index=1)
                return True
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.ctx.intent_router.emit(Intent.SELECT_OPTION, index=2)
                return True

        # Touch/Mouse selection - immediate on tap
        if self.is_select_event(event):
            pos = self.get_event_position(event)
            if pos:
                mx, my = pos
                # Check settings text click
                if self.settings_rect and self.settings_rect.collidepoint(mx, my):
                    self.ctx.intent_router.emit(Intent.GO_TO_SETTINGS)
                    return True
                # Check button clicks
                for i, rect in enumerate(self.button_rects):
                    if rect.collidepoint(mx, my):
                        self.ctx.intent_router.emit(Intent.SELECT_OPTION, index=i)
                        return True

        return False

    def select_option(self, index: int):
        """Public method to select an option by index (for voice commands)."""
        self.ctx.intent_router.emit(Intent.SELECT_OPTION, index=index)

    def update(self, dt: float):
        """Update menu state."""
        pass

    def draw(self, screen: pygame.Surface):
        """Draw the menu using renderer abstraction."""
        # Build frame state
        frame = FrameState(clear_color=self.bg)

        w, h = screen.get_size()

        # Get layout and style
        self.theme["layout"]
        self.theme["style"]

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
            font_type = getattr(text, "font_type", "primary")
            font = get_theme_font(text.font_size, font_type)

            color = text.color[:3]
            surface = font.render(text.content, True, color)

            # Handle alignment
            if hasattr(text, "align") and text.align == "center":
                rect = surface.get_rect(center=(int(text.position[0]), int(text.position[1])))
                screen.blit(surface, rect)
            else:
                screen.blit(surface, (int(text.position[0]), int(text.position[1])))

        # Draw title card container at top of left column

        # Get layout and style
        layout = self.theme["layout"]
        style = self.theme["style"]

        # Title card configuration from layout
        title_card_config = layout.get("title_card", {})
        title_card_title = title_card_config.get("title", "NRHOF")
        border_fade_pct = title_card_config.get("border_fade_pct", 0.9)
        border_height_pct = title_card_config.get("border_height_pct", 0.15)

        # Calculate title card position
        title_card_y = self.content_top

        # Manual adjustment: Move NRHOF card down
        title_card_y += 52  # Move down

        # Language-specific adjustment for Japanese

        if get_language() == "jp":
            title_card_y += 21  # Additional offset for Japanese to match English position

        # Calculate card height to fill remaining space (minus footer)
        footer_height = 130
        margins = layout.get("margins", {})
        margin_left = margins.get("left", MARGIN_LEFT)
        title_card_height = screen.get_height() - title_card_y - margin_left - footer_height

        # Calculate title font size to determine overlap
        title_font_size = style["typography"]["fonts"].get("title", 76)
        title_font = get_theme_font(title_font_size, "secondary")
        title_surface = title_font.render(title_card_title, True, (255, 255, 255))
        title_overlap = title_surface.get_height() // 2

        # Adjust y position so title overlaps card border
        title_card_y_adjusted = title_card_y + title_overlap

        # Japanese-specific adjustment: Move NRHOF title text down 13px in Japanese mode
        title_text_offset = 13 if get_language() == "jp" else 0

        # Draw the full-height title card container
        layout_info = draw_title_card_container(
            surface=screen,
            x=self.left_col_x,
            y=title_card_y_adjusted,
            width=self.left_col_width,
            height=title_card_height,
            title=title_card_title,
            theme={"layout": layout, "style": style},
            title_y_adjustment=title_text_offset,
            border_fade_pct=border_fade_pct,
            border_height_pct=border_height_pct,
        )

        # Content area for buttons (inside title card)
        content_y = layout_info["content_start_y"]
        content_x = self.left_col_x
        content_width = self.left_col_width
        screen.get_height() - content_y - footer_height

        # Get column configuration
        columns_config = layout.get("columns", {})

        # Draw buttons vertically inside content area
        buttons_config = layout.get("buttons", {})
        button_width = buttons_config.get("width", "67%")  # Button width override

        # Get adornment config to calculate offset
        button_config = layout.get("button", {})
        adornment_config = button_config.get("adornment", {})
        adornment_size = adornment_config.get("size", 25)
        adornment_margin = adornment_config.get("margin_left", 18)

        # Position buttons relative to content area
        total_left_spacing = adornment_margin + adornment_size + adornment_margin
        button_x = content_x + total_left_spacing

        # Start buttons at top of content area with 30px spacing
        from core.localization import t

        y = content_y + 30
        for i, entry in enumerate(self.entries):
            # Use localization key if available, otherwise fall back to label
            label_key = entry.get("label_key")
            if label_key:
                label = t(label_key)
            else:
                label = entry.get("label", f"Option {i+1}")
            button_rect = draw_button(
                surface=screen,
                x=button_x,
                y=y,
                container_width=content_width - total_left_spacing,
                text=label,
                theme={"layout": self.theme["layout"], "style": self.theme["style"]},
                width_pct=button_width,  # Override button width
            )
            self.button_rects.append(button_rect)
            y += button_rect.height + self.button_spacing

        # Right column positioning (Now Playing is now a global overlay)
        right_col_x = self.left_col_x + self.left_col_width + columns_config["gutter"]
        right_col_width = columns_config["right"]["width"]

        # Draw d20 component at top of right column, shifted 50px left
        d20_y = title_card_y_adjusted + 100  # Position below where Now Playing used to be
        d20_x = right_col_x - 25  # Shift to the left
        d20_rect = draw_d20(
            surface=screen,
            x=d20_x,
            y=d20_y,
            width=right_col_width,
            height=420,
            theme={"style": style},
        )

        # Draw timeclock component 100px below d20, extended 50px to the left
        timeclock_y = d20_rect.bottom + 40
        timeclock_settings = layout.get("timeclock", {})
        timeclock_height = timeclock_settings.get("height", 300)
        timeclock_width = right_col_width + 44  # Extend by 44px (50px - 6px border)
        timeclock_x = right_col_x - 44  # Shift 44px to the left (50px - 6px border)
        draw_timeclock(
            surface=screen,
            x=timeclock_x,
            y=timeclock_y,
            width=timeclock_width,
            height=timeclock_height,
            theme={"style": style, "layout": layout},
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
        self.settings_rect = draw_footer(screen, self.color)
