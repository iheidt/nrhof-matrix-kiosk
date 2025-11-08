#!/usr/bin/env python3
"""Spotify integration for Now Playing metadata and control."""

import threading
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from core.logger import get_logger
from core.now_playing import Track
from core.source_manager import SourceManager

logger = get_logger("spotify_source")


class SpotifySource:
    """Polls Spotify for currently playing track and updates SourceManager."""

    def __init__(self, config: dict, source_manager: SourceManager):
        """Initialize Spotify source.

        Args:
            config: Configuration dict
            source_manager: SourceManager instance
        """
        self.config = config
        self.source_manager = source_manager
        self.enabled = config.get("spotify", {}).get("enabled", False)

        # Initialize state
        self.running = False
        self.thread: threading.Thread | None = None
        self.sp: spotipy.Spotify | None = None

        # Polling settings
        self.poll_interval = config.get("spotify", {}).get("poll_interval_seconds", 2.0)

        if not self.enabled:
            logger.info("Spotify integration disabled in config")
            return

        # Initialize Spotify client
        try:
            self._init_spotify()
            logger.info("Spotify client initialized")
        except Exception as e:
            logger.error("Failed to initialize Spotify client", error=str(e))
            self.enabled = False

    def _init_spotify(self):
        """Initialize Spotify client with OAuth."""
        spotify_config = self.config.get("spotify", {})

        # Required scopes for reading playback state (including podcasts/audiobooks)
        # Note: Spotify Free users may not have access to podcast/audiobook metadata via API
        scope = "user-read-playback-state user-read-currently-playing user-read-playback-position"

        auth_manager = SpotifyOAuth(
            client_id=spotify_config.get("client_id"),
            client_secret=spotify_config.get("client_secret"),
            redirect_uri=spotify_config.get("redirect_uri", "http://127.0.0.1:8888/callback"),
            scope=scope,
            cache_path=spotify_config.get("cache_path", ".spotify_cache"),
        )

        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    def start(self):
        """Start polling Spotify."""
        if not self.enabled:
            logger.info("Spotify source not started (disabled)")
            return

        if self.running:
            logger.warning("Spotify source already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info("Spotify polling started")

    def stop(self):
        """Stop polling Spotify."""
        if not self.running:
            return

        logger.info("Stopping Spotify source...")
        self.running = False

        if self.thread:
            self.thread.join(timeout=5.0)

        logger.info("Spotify source stopped")

    def _poll_loop(self):
        """Main polling loop."""
        logger.info("Spotify poll loop started")

        while self.running:
            try:
                # Get current playback - use currently_playing() for podcast/audiobook support
                currently_playing = self.sp.currently_playing()

                if currently_playing:
                    is_playing = currently_playing.get("is_playing", False)
                    item = currently_playing.get("item")

                    if is_playing and item:
                        # Merge device info from current_playback if needed
                        playback_state = self.sp.current_playback()
                        if playback_state:
                            currently_playing["device"] = playback_state.get("device")
                            currently_playing["progress_ms"] = playback_state.get("progress_ms")

                        track = self._parse_playback(currently_playing)
                        if track:
                            self.source_manager.set_from("spotify", track)
                    else:
                        # Paused or no item
                        self.source_manager.set_from("spotify", None)
                else:
                    # No playback data
                    self.source_manager.set_from("spotify", None)

            except Exception as e:
                logger.error(f"Error polling Spotify: {type(e).__name__}: {e}")
                # Uncomment for full traceback during debugging:
                # import traceback
                # logger.error(f"Traceback: {traceback.format_exc()}")

            # Sleep
            time.sleep(self.poll_interval)

        logger.info("Spotify poll loop ended")

    def _parse_playback(self, playback: dict) -> Track | None:
        """Parse Spotify playback response into Track.

        Args:
            playback: Spotify playback response

        Returns:
            Track or None
        """
        try:
            item = playback.get("item")
            if not item:
                return None

            # Detect content type
            item_type = item.get("type", "track")

            # Parse based on content type
            if item_type == "episode":
                # Podcast episode
                title = item.get("name", "Unknown")
                show_info = item.get("show", {})
                artist = show_info.get("name", "Unknown Podcast")  # Use show name as artist
                album = None
                show_name = show_info.get("name")
                publisher = show_info.get("publisher")
                content_type = "podcast"

                # Images from show
                images = show_info.get("images", [])

            elif item_type == "audiobook":
                # Audiobook
                title = item.get("name", "Unknown")
                authors = item.get("authors", [])
                artist = authors[0].get("name", "Unknown Author") if authors else "Unknown Author"
                album = None
                show_name = None
                publisher = item.get("publisher")
                content_type = "audiobook"

                # Images from audiobook
                images = item.get("images", [])

            else:
                # Music track (default)
                title = item.get("name", "Unknown")
                artists = item.get("artists", [])
                artist = artists[0].get("name", "Unknown") if artists else "Unknown"
                album_info = item.get("album", {})
                album = album_info.get("name")
                show_name = None
                publisher = None
                content_type = "music"

                # Images from album
                images = album_info.get("images", [])

            # Common fields
            spotify_id = item.get("id")
            duration_ms = item.get("duration_ms")
            image_url = images[0].get("url") if images else None

            # Additional fields
            release_date = item.get("release_date")
            is_playing = playback.get("is_playing")
            progress_ms = playback.get("progress_ms")
            device_name = playback.get("device", {}).get("name")
            device_type = playback.get("device", {}).get("type")
            device_volume = playback.get("device", {}).get("volume_percent")
            context_type = playback.get("context", {}).get("type")
            context_uri = playback.get("context", {}).get("uri")

            # Image sizes
            image_large = None
            image_medium = None
            image_small = None
            for image in images:
                if image.get("height") == 640:
                    image_large = image.get("url")
                elif image.get("height") == 300:
                    image_medium = image.get("url")
                elif image.get("height") == 64:
                    image_small = image.get("url")

            return Track(
                title=title,
                artist=artist,
                album=album,
                confidence=1.0,
                source="spotify",
                spotify_id=spotify_id,
                duration_ms=duration_ms,
                content_type=content_type,
                show_name=show_name,
                publisher=publisher,
                image_url=image_url,
                image_large=image_large,
                image_medium=image_medium,
                image_small=image_small,
                release_date=release_date,
                is_playing=is_playing,
                progress_ms=progress_ms,
                device_name=device_name,
                device_type=device_type,
                device_volume=device_volume,
                context_type=context_type,
                context_uri=context_uri,
            )

        except Exception as e:
            logger.error("Failed to parse Spotify playback", error=str(e))
            return None

    def get_current_track(self) -> Track | None:
        """Get current track synchronously (for testing/debugging).

        Returns:
            Current track or None
        """
        if not self.enabled or not self.sp:
            return None

        try:
            playback = self.sp.current_playback()
            if playback and playback.get("is_playing"):
                return self._parse_playback(playback)
        except Exception as e:
            logger.error("Error getting current track", error=str(e))

        return None
