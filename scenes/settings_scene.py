#!/usr/bin/env python3
import pygame

from core.theme_loader import get_theme_loader
from routing.intent_router import Intent
from scenes.scene_manager import Scene, register_scene
from ui.components import (
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    draw_footer,
    draw_scanlines,
    draw_status,
    draw_title_card_container,
)
from ui.fonts import render_mixed_text


@register_scene("SettingsScene")
class SettingsScene(Scene):
    """Settings configuration scene."""

    def __init__(self, ctx):
        super().__init__(ctx)

        # Load theme
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme("settings", theme_name="pipboy")

        # Extract from theme
        self.color = tuple(self.theme["style"]["colors"]["primary"])
        self.bg = tuple(self.theme["style"]["colors"]["background"])

        # Layout vars
        self.nav_back_rect = None
        self.settings_rect = None  # Store settings text rect for click detection
        self.lang_left_rect = None
        self.lang_right_rect = None
        self.power_down_rect = None  # Store power down button rect for click detection

    def on_enter(self):
        """Called when scene becomes active."""
        super().on_enter()  # Take memory snapshot

    def on_exit(self):
        """Called when scene is about to be replaced."""
        super().on_exit()  # Call parent cleanup (event handlers, caches, GC)

    def handle_event(self, event: pygame.event.Event):
        """Handle settings input."""
        # ESC or click nav_back to return to previous scene
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
            elif event.key == pygame.K_w:
                # Trigger wakeword for testing
                self.trigger_wakeword()
                return True

        # Click nav_back or language toggle (ignore scroll wheel events)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 2, 3):
            if self.nav_back_rect and self.nav_back_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
            # Check power down button click
            if self.power_down_rect and self.power_down_rect.collidepoint(event.pos):
                # Shut down the app
                import sys

                pygame.quit()
                sys.exit(0)
                return True
            # Toggle language - check which side was clicked
            if self.lang_left_rect and self.lang_left_rect.collidepoint(event.pos):
                from core.localization import set_language

                set_language("en")
                return True
            if self.lang_right_rect and self.lang_right_rect.collidepoint(event.pos):
                from core.localization import set_language

                set_language("jp")
                return True

        return False

    def update(self, dt: float):
        """Update settings state."""
        pass

    def draw(self, screen: pygame.Surface):
        """Draw settings screen."""
        # Clear screen
        screen.fill(self.bg)
        w, h = screen.get_size()

        # Get style and layout
        style = self.theme["style"]
        layout = self.theme_loader.load_layout("menu")  # Use menu layout for margins

        # Get margins
        margins = layout.get("margins", {})
        margin_left = margins.get("left", MARGIN_LEFT)
        margin_right = margins.get("right", MARGIN_RIGHT)

        # Draw nav_back component ("<esc" in top-left corner at margin boundary)
        from core.localization import t

        nav_back_text = t("common.esc")
        nav_back_surface = render_mixed_text(
            nav_back_text,
            style["typography"]["fonts"]["micro"],
            "primary",
            self.color,
        )
        nav_back_x = MARGIN_LEFT
        nav_back_y = MARGIN_TOP
        screen.blit(nav_back_surface, (nav_back_x, nav_back_y))

        # Store rect for click detection
        self.nav_back_rect = pygame.Rect(
            nav_back_x,
            nav_back_y,
            nav_back_surface.get_width(),
            nav_back_surface.get_height(),
        )

        # Calculate title card position (20px below nav_back)
        title_card_y = nav_back_y + nav_back_surface.get_height() + 20
        title_card_width = w - margin_left - margin_right

        # Calculate card height to fill remaining space (minus footer)
        footer_height = 130
        title_card_height = (
            h - title_card_y - margin_left - footer_height
        )  # Use margin_left as bottom margin (50px)

        # Get title card border settings from layout
        title_card_config = layout.get("title_card", {})
        border_fade_pct = title_card_config.get("border_fade_pct", 0.9)
        border_height_pct = title_card_config.get("border_height_pct", 0.15)

        # Get title font to calculate overlap
        title_text = t("settings.title")
        title_font_size = style["typography"]["fonts"].get("title", 76)
        title_surface = render_mixed_text(title_text, title_font_size, "secondary", (255, 255, 255))
        title_overlap = title_surface.get_height() // 2

        # Adjust y position so title overlaps card border
        title_card_y_adjusted = title_card_y + title_overlap

        # Draw the full-width title card container
        layout_info = draw_title_card_container(
            surface=screen,
            x=margin_left,
            y=title_card_y_adjusted,
            width=title_card_width,
            height=title_card_height,
            title=title_text,
            theme={"layout": layout, "style": style},
            border_fade_pct=border_fade_pct,
            border_height_pct=border_height_pct,
        )

        # Content area for settings controls
        content_y = layout_info["content_start_y"]
        content_x = margin_left
        content_width = title_card_width
        h - content_y - 130  # Subtract footer height

        # Draw language toggle button inside content area
        from core.localization import get_language
        from ui.components.buttons import draw_toggle_button

        # Get current language
        current_lang = get_language()

        # Calculate button position inside content area
        button_config = layout.get("button", {})
        adornment_config = button_config.get("adornment", {})
        adornment_size = adornment_config.get("size", 25)
        adornment_margin = adornment_config.get("margin_left", 18)

        # Position with same spacing as menu (adornment space reserved but not drawn)
        # Offset from content_x instead of margin_left
        total_left_spacing = adornment_margin + adornment_size + adornment_margin
        button_x = content_x + total_left_spacing
        button_y = content_y + 30  # 30px from top of content area

        # Toggle width accounts for left and right spacing
        toggle_width = content_width - total_left_spacing - total_left_spacing
        selected_side = "left" if current_lang == "en" else "right"

        self.lang_left_rect, self.lang_right_rect = draw_toggle_button(
            surface=screen,
            x=button_x,
            y=button_y,
            width=toggle_width,
            left_text=t("settings.language_english"),
            right_text=t("settings.language_japanese"),
            selected=selected_side,
            theme={"layout": layout, "style": style},
        )

        # Draw scanlines, status, and footer
        draw_scanlines(screen)
        draw_status(screen, self.color)
        # Display "power down" text in footer instead of "settings"
        power_down_text = t("settings.power_down")
        self.power_down_rect = draw_footer(
            screen,
            self.color,
            show_settings=False,
            custom_text=power_down_text,
        )
