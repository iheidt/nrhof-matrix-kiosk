#!/usr/bin/env python3
import pygame
import threading
import logging
from typing import List, Dict, Any, Optional
from scenes.scene_manager import Scene, register_scene
from ui.components import (
    draw_scanlines, draw_footer, draw_title_card_container,
    MARGIN_TOP, MARGIN_LEFT, MARGIN_RIGHT
)
from ui.fonts import get_localized_font
from routing.intent_router import Intent
from core.theme_loader import get_theme_loader
from integrations.webflow_client import create_webflow_client
from integrations.webflow_cache import WebflowCache, WebflowCacheManager
from integrations.webflow_constants import NR38_LIST_UUID


@register_scene("NR38Scene")
class NR38Scene(Scene):
    """NR-38 scene."""
    
    def __init__(self, ctx):
        super().__init__(ctx)
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Load theme
        self.theme_loader = get_theme_loader()
        self.theme = self.theme_loader.load_theme('nr38', theme_name='pipboy')
        
        # Extract from theme
        self.color = tuple(self.theme['style']['colors']['primary'])
        self.bg = tuple(self.theme['style']['colors']['background'])
        
        # Layout vars
        self.nav_back_rect = None
        self.settings_rect = None  # Store settings text rect for click detection
        
        # Cache rendered surfaces to prevent re-rendering every frame
        self._nav_back_surface = None
        self._title_surface = None
        self._title_overlap = None
        self._cached_language = None  # Track language for cache invalidation
        
        # Webflow data
        self._bands: List[Dict[str, Any]] = []
        self._loading = False
        self._loaded = False
        self._cache_manager: Optional[WebflowCacheManager] = None
    
    def on_enter(self):
        """Called when scene becomes active."""
        # Initialize Webflow client and fetch bands if not already loaded
        if not self._loaded and not self._loading:
            self._loading = True
            # Fetch bands in background thread
            thread = threading.Thread(target=self._fetch_bands, daemon=True)
            thread.start()
    
    def on_exit(self):
        """Called when scene is about to be replaced."""
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle NR-38 input."""
        # ESC key to return to previous scene
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
        
        # Handle mouse clicks
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check nav_back click
            if self.nav_back_rect and self.nav_back_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_BACK)
                return True
            # Check settings click
            if self.settings_rect and self.settings_rect.collidepoint(event.pos):
                self.ctx.intent_router.emit(Intent.GO_TO_SETTINGS)
                return True
        
        return False
    
    def _fetch_bands(self):
        """Fetch NR-38 bands from cache (runs in background thread)."""
        import time
        
        try:
            # Initialize cache manager if not exists
            if self._cache_manager is None:
                # Get cache manager from app context if available
                if hasattr(self.ctx, 'webflow_cache_manager'):
                    self._cache_manager = self.ctx.webflow_cache_manager
                else:
                    # Create new cache manager
                    webflow_client = create_webflow_client(
                        self.ctx.config,
                        self.logger
                    )
                    
                    if webflow_client is None:
                        self.logger.warning("Webflow client not available")
                        self._loading = False
                        return
                    
                    cache = WebflowCache(logger=self.logger)
                    self._cache_manager = WebflowCacheManager(
                        webflow_client,
                        cache,
                        self.logger
                    )
            
            # Retry logic to wait for cache to be populated
            all_bands = None
            max_retries = 3
            retry_delay = 0.5  # seconds
            
            for attempt in range(max_retries):
                # Get bands from cache (filtered for NR-38 UUID reference)
                # The nerd-rock-list field contains a UUID reference, not a string
                all_bands = self._cache_manager.get_bands(filter_list=NR38_LIST_UUID)
                
                if all_bands:
                    break
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
            
            if all_bands:
                # Extract and format band data
                nr38_bands = []
                for band in all_bands:
                    field_data = band.get('fieldData', {})
                    name = field_data.get('name', 'Unknown')
                    rank = field_data.get('rank', 999)
                    nr38_bands.append({
                        'name': name.lower(),
                        'rank': rank
                    })
                
                # Sort by rank
                nr38_bands.sort(key=lambda x: x['rank'])
                
                # Store bands
                self._bands = nr38_bands
                self._loaded = True
                self.logger.info(f"Loaded {len(self._bands)} NR-38 bands from cache")
            else:
                self.logger.warning("No NR-38 bands in cache")
                
        except Exception as e:
            self.logger.error(f"Error loading NR-38 bands: {e}")
        finally:
            self._loading = False
    
    def update(self, dt: float):
        """Update NR-38 state."""
        pass
    
    def draw(self, screen: pygame.Surface):
        """Draw NR-38 screen."""
        # Clear screen
        screen.fill(self.bg)
        w, h = screen.get_size()
        
        # Get style and layout
        style = self.theme['style']
        layout = self.theme_loader.load_layout('menu')  # Use menu layout for margins
        
        # Get margins
        margins = layout.get('margins', {})
        margin_left = margins.get('left', MARGIN_LEFT)
        margin_right = margins.get('right', MARGIN_RIGHT)
        
        # Draw nav_back component ("<esc" in top-left corner at margin boundary)
        # Cache to prevent re-rendering every frame
        from core.localization import t, get_language
        current_language = get_language()
        if self._nav_back_surface is None or self._cached_language != current_language:
            nav_back_text = t('common.esc')
            nav_back_font = get_localized_font(style['typography']['fonts']['micro'], 'primary', nav_back_text)
            self._nav_back_surface = nav_back_font.render(nav_back_text, True, self.color)
            self._cached_language = current_language
        nav_back_x = MARGIN_LEFT
        nav_back_y = MARGIN_TOP
        screen.blit(self._nav_back_surface, (nav_back_x, nav_back_y))
        
        # Store rect for click detection
        self.nav_back_rect = pygame.Rect(
            nav_back_x,
            nav_back_y,
            self._nav_back_surface.get_width(),
            self._nav_back_surface.get_height()
        )
        
        # Calculate title card position (20px below nav_back)
        title_card_y = nav_back_y + self._nav_back_surface.get_height() + 20
        title_card_width = w - margin_left - margin_right
        
        # Calculate card height to fill remaining space (minus footer)
        footer_height = 130
        title_card_height = h - title_card_y - margin_left - footer_height  # Use margin_left as bottom margin (50px)
        
        # Get title card border settings from layout
        title_card_config = layout.get('title_card', {})
        border_fade_pct = title_card_config.get('border_fade_pct', 0.9)
        border_height_pct = title_card_config.get('border_height_pct', 0.15)
        
        # Get title font to calculate overlap (cached)
        if self._title_surface is None or self._cached_language != current_language:
            title_text = t('nr38.title')
            title_font_size = style['typography']['fonts'].get('title', 76)
            title_font = get_localized_font(title_font_size, 'secondary', title_text)
            self._title_surface = title_font.render(title_text, True, (255, 255, 255))
            self._title_overlap = self._title_surface.get_height() // 2
        title_text = t('nr38.title')  # Still need text for draw_title_card_container
        title_overlap = self._title_overlap
        
        # Adjust y position so title overlaps card border
        title_card_y_adjusted = title_card_y + title_overlap
        
        # Language-specific adjustment for Japanese
        if current_language == 'jp':
            title_card_y_adjusted += 18  # Additional offset for Japanese to match English position
        
        # Draw the full-width title card container
        layout_info = draw_title_card_container(
            surface=screen,
            x=margin_left,
            y=title_card_y_adjusted,
            width=title_card_width,
            height=title_card_height,
            title=title_text,
            theme={'layout': layout, 'style': style},
            border_fade_pct=border_fade_pct,
            border_height_pct=border_height_pct,
            content_margin=0  # Reduced margin between title and content
        )
        
        # Content area for NR-38
        content_y = layout_info['content_start_y']
        content_x = margin_left + 35 + 24  # Match title card padding
        content_width = title_card_width - (35 + 24) * 2  # Account for padding on both sides
        content_height = h - content_y - 130  # Subtract footer height
        
        # Calculate 5-column layout
        # col 1 width = 33% of container - 100px
        # col 2 width = 50px (gutter)
        # col 3 width = 33% of container - 100px
        # col 4 width = 50px (gutter)
        # col 5 width = 33% of container - 100px
        
        # Layout configuration
        line_height = 50  # Spacing between numbers (adjust this to change spacing)
        gutter_width = 50
        
        col_width = (content_width - 100) / 3  # 33% minus 100px total, divided by 3 columns
        
        col1_x = content_x
        col2_x = col1_x + col_width + gutter_width
        col3_x = col2_x + col_width + gutter_width
        
        # Font for numbers and band names
        number_font = get_localized_font(32, 'primary', '1.')
        band_font = get_localized_font(28, 'primary', 'band name')
        
        # Show loading message if still fetching
        if self._loading:
            loading_text = "Loading bands from Webflow..."
            loading_surface = band_font.render(loading_text, True, self.color)
            screen.blit(loading_surface, (content_x, content_y + 20))
        elif not self._bands:
            # Show message if no bands loaded
            error_text = "No bands available. Check Webflow connection."
            error_surface = band_font.render(error_text, True, self.color)
            screen.blit(error_surface, (content_x, content_y + 20))
        else:
            # Draw three columns with ranked bands
            # Column 1: 1-13
            for i in range(min(13, len(self._bands))):
                band = self._bands[i]
                rank = i + 1
                number_text = f"{rank}."
                band_name = band['name']
                
                # Render number
                number_surface = number_font.render(number_text, True, self.color)
                y_pos = content_y + 20 + i * line_height
                screen.blit(number_surface, (col1_x, y_pos))
                
                # Render band name (offset to the right of number)
                band_surface = band_font.render(band_name, True, self.color)
                screen.blit(band_surface, (col1_x + 50, y_pos + 2))
            
            # Column 2: 14-26
            for i in range(13, min(26, len(self._bands))):
                band = self._bands[i]
                rank = i + 1
                number_text = f"{rank}."
                band_name = band['name']
                
                number_surface = number_font.render(number_text, True, self.color)
                y_pos = content_y + 20 + (i - 13) * line_height
                screen.blit(number_surface, (col2_x, y_pos))
                
                band_surface = band_font.render(band_name, True, self.color)
                screen.blit(band_surface, (col2_x + 50, y_pos + 2))
            
            # Column 3: 27-38
            for i in range(26, min(38, len(self._bands))):
                band = self._bands[i]
                rank = i + 1
                number_text = f"{rank}."
                band_name = band['name']
                
                number_surface = number_font.render(number_text, True, self.color)
                y_pos = content_y + 20 + (i - 26) * line_height
                screen.blit(number_surface, (col3_x, y_pos))
                
                band_surface = band_font.render(band_name, True, self.color)
                screen.blit(band_surface, (col3_x + 50, y_pos + 2))
        
        # Draw scanlines and footer
        draw_scanlines(screen)
        self.settings_rect = draw_footer(screen, self.color, show_settings=True)