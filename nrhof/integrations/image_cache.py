"""Image cache manager for downloading and caching images from URLs."""

import hashlib
import io
import re
from pathlib import Path
from threading import Lock
from typing import Any

import pygame
import requests

from nrhof.core.logging_utils import setup_logger

try:
    import cairosvg

    HAS_SVG_SUPPORT = True
except ImportError:
    HAS_SVG_SUPPORT = False


class ImageCache:
    """Manages local cache of images downloaded from URLs."""

    def __init__(
        self,
        cache_dir: str = "runtime/image_cache",
        logger=None,
    ):
        """Initialize image cache.

        Args:
            cache_dir: Directory to store cached images
            logger: Optional logger instance
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or setup_logger(__name__)
        self._memory_cache: dict[str, pygame.Surface] = {}  # In-memory cache
        self._svg_cache: dict[str, bytes] = {}  # Cache SVG content for re-rendering
        self._lock = Lock()

    def _get_cache_path(self, url: str, fill_color: tuple[int, int, int] | None = None) -> Path:
        """Get cache file path for a URL.

        Args:
            url: Image URL
            fill_color: Optional RGB tuple (affects cache key for SVGs)

        Returns:
            Path to cached file
        """
        # Use hash of URL as filename to avoid filesystem issues
        # Include fill_color in hash for SVGs to cache different colored versions
        cache_key = url
        if fill_color and url.lower().endswith(".svg"):
            cache_key = f"{url}:color:{fill_color[0]:02x}{fill_color[1]:02x}{fill_color[2]:02x}"

        url_hash = hashlib.md5(cache_key.encode()).hexdigest()
        # Extract extension from URL if possible
        ext = ".png"  # Default
        if "." in url:
            url_ext = url.split(".")[-1].split("?")[0].lower()
            if url_ext in ["jpg", "jpeg", "png", "gif", "webp", "svg"]:
                # SVG files will be converted to PNG, so always use .png extension
                ext = ".png" if url_ext == "svg" else f".{url_ext}"
        return self.cache_dir / f"{url_hash}{ext}"

    def get_image(
        self,
        url: str,
        max_size: tuple[int, int] | None = None,
        fill_color: tuple[int, int, int] | None = None,
    ) -> pygame.Surface | None:
        """Get image from cache or download it.

        Args:
            url: Image URL to fetch
            max_size: Optional (width, height) to scale image
            fill_color: Optional RGB tuple to recolor SVG fills (e.g., (0, 255, 0))

        Returns:
            Pygame surface with image, or None if failed
        """
        if not url:
            return None

        # Check memory cache first (include fill_color in cache key)
        cache_key = f"{url}:{max_size}:{fill_color}"
        with self._lock:
            if cache_key in self._memory_cache:
                return self._memory_cache[cache_key]

        # Check disk cache (include fill_color for SVGs)
        cache_path = self._get_cache_path(url, fill_color)
        if cache_path.exists():
            try:
                surface = pygame.image.load(str(cache_path))
                # Convert to RGBA for proper alpha transparency
                surface = surface.convert_alpha()
                if max_size:
                    surface = self._scale_image(surface, max_size)
                with self._lock:
                    self._memory_cache[cache_key] = surface
                return surface
            except Exception as e:
                self.logger.error(f"Error loading cached image {cache_path}: {e}")
                # Delete corrupted cache file
                cache_path.unlink(missing_ok=True)

        # Download image
        try:
            self.logger.info(f"Downloading image from {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Check if this is an SVG file
            is_svg = url.lower().endswith(".svg") or "image/svg" in response.headers.get(
                "content-type", ""
            )

            if is_svg:
                if not HAS_SVG_SUPPORT:
                    self.logger.error(
                        "SVG file detected but cairosvg not installed. Install with: pip install cairosvg"
                    )
                    return None

                # Store SVG content for potential re-rendering
                with self._lock:
                    self._svg_cache[url] = response.content

                # Convert SVG to PNG at high resolution for quality
                try:
                    self.logger.info("Converting SVG to PNG...")

                    # Optionally recolor SVG
                    svg_content = response.content
                    if fill_color:
                        svg_text = svg_content.decode("utf-8", errors="ignore")
                        hex_color = f"#{fill_color[0]:02x}{fill_color[1]:02x}{fill_color[2]:02x}"

                        # Add default fill to root SVG element only if it doesn't already have one
                        # This handles SVGs where child elements don't have explicit fill attributes
                        if not re.search(r"<svg[^>]*?\sfill=", svg_text):
                            svg_text = re.sub(
                                r"<svg([^>]*?)>", f'<svg\\1 fill="{hex_color}">', svg_text, count=1
                            )

                        # Replace all fill attributes (including currentColor, color names, hex, rgb, etc.)
                        svg_text = re.sub(r'fill="[^"]+"', f'fill="{hex_color}"', svg_text)
                        svg_text = re.sub(r"fill='[^']+'", f"fill='{hex_color}'", svg_text)

                        # Replace fill: style properties
                        svg_text = re.sub(r'fill:\s*[^;"\'}]+', f"fill:{hex_color}", svg_text)

                        # Replace stroke colors too (for outlined logos)
                        svg_text = re.sub(r'stroke="[^"]+"', f'stroke="{hex_color}"', svg_text)
                        svg_text = re.sub(r"stroke='[^']+'", f"stroke='{hex_color}'", svg_text)
                        svg_text = re.sub(r'stroke:\s*[^;"\'}]+', f"stroke:{hex_color}", svg_text)

                        svg_content = svg_text.encode("utf-8")
                        self.logger.info(f"Recolored SVG to {hex_color}")

                    # Render preserving aspect ratio (only constrain height, let width scale)
                    png_data = cairosvg.svg2png(
                        bytestring=svg_content,
                        output_height=max_size[1],  # Only set height to preserve aspect ratio
                        background_color="transparent",  # Ensure transparent background
                    )

                    # Save high-res PNG to cache
                    with open(cache_path, "wb") as f:
                        f.write(png_data)

                    # Load into pygame from PNG data
                    surface = pygame.image.load(io.BytesIO(png_data))
                    # Convert to RGBA for proper alpha transparency
                    surface = surface.convert_alpha()
                except Exception as e:
                    self.logger.error(f"Error converting SVG to PNG: {e}")
                    return None
            else:
                # Save raster image to cache
                with open(cache_path, "wb") as f:
                    f.write(response.content)

                # Load into pygame
                surface = pygame.image.load(str(cache_path))
                # Convert to RGBA for proper alpha transparency
                surface = surface.convert_alpha()

            if max_size:
                surface = self._scale_image(surface, max_size)
            with self._lock:
                self._memory_cache[cache_key] = surface
            self.logger.info(f"Cached image: {cache_path}")
            return surface

        except Exception as e:
            self.logger.error(f"Error downloading image from {url}: {e}")
            return None

    def _scale_image(
        self,
        surface: pygame.Surface,
        max_size: tuple[int, int],
    ) -> pygame.Surface:
        """Scale image to fit within max_size while preserving aspect ratio.

        Args:
            surface: Original surface
            max_size: (max_width, max_height)

        Returns:
            Scaled surface
        """
        orig_width, orig_height = surface.get_size()
        max_width, max_height = max_size

        # Calculate scale factor to fit within max_size
        scale_x = max_width / orig_width
        scale_y = max_height / orig_height
        scale = min(scale_x, scale_y)

        # Only scale down, never up
        if scale >= 1.0:
            return surface

        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)

        return pygame.transform.smoothscale(surface, (new_width, new_height))

    def is_cached(self, url: str) -> bool:
        """Check if an image is already cached on disk.

        Args:
            url: Image URL

        Returns:
            True if image is cached
        """
        if not url:
            return False
        cache_path = self._get_cache_path(url, fill_color=None)
        return cache_path.exists()

    def clear_memory_cache(self):
        """Clear in-memory cache to free RAM."""
        with self._lock:
            self._memory_cache.clear()
            self._svg_cache.clear()
        self.logger.debug("Cleared image memory cache")

    def clear_disk_cache(self):
        """Clear disk cache."""
        for cache_file in self.cache_dir.glob("*"):
            cache_file.unlink()
        self.logger.info("Cleared image disk cache")

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache info
        """
        disk_files = list(self.cache_dir.glob("*"))
        total_size = sum(f.stat().st_size for f in disk_files if f.is_file())

        with self._lock:
            memory_count = len(self._memory_cache)
            svg_count = len(self._svg_cache)

        return {
            "disk_files": len(disk_files),
            "disk_size_mb": total_size / (1024 * 1024),
            "memory_cached": memory_count,
            "svg_cached": svg_count,
        }
