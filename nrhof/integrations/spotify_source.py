#!/usr/bin/env python3
"""Spotify integration for Now Playing metadata and control."""

import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from nrhof.core.now_playing import Track
from nrhof.core.source_manager import SourceManager
from nrhof.workers.base import BaseWorker


class SpotifySource(BaseWorker):
    """Polls Spotify for currently playing track and updates SourceManager."""

    def __init__(self, config: dict, source_manager: SourceManager):
        """Initialize Spotify source.

        Args:
            config: Configuration dict
            source_manager: SourceManager instance
        """
        # Initialize BaseWorker FIRST (sets up self.logger)
        super().__init__(config, logger_name="spotify_source")

        self.source_manager = source_manager
        self.enabled = config.get("spotify", {}).get("enabled", False)

        # Spotify client
        self.sp: spotipy.Spotify | None = None

        # Polling settings
        self.poll_interval = config.get("spotify", {}).get("poll_interval_seconds", 2.0)

        if not self.enabled:
            self.logger.info("Spotify integration disabled in config")
            return

        # Initialize Spotify client
        try:
            self._init_spotify()
            self.logger.info("Spotify client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Spotify client: {e}")
            self.enabled = False

    def _init_spotify(self):
        """Initialize Spotify client with OAuth."""
        spotify_config = self.config.get("spotify", {})

        # Required scopes for reading playback state and controlling playback
        # Note: Spotify Free users may not have access to podcast/audiobook metadata via API
        scope = "user-read-playback-state user-read-currently-playing user-read-playback-position user-modify-playback-state"

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
            self.logger.info("Spotify source not started (disabled)")
            return

        # Call BaseWorker.start() which handles threading
        super().start()

    def _worker_loop(self):
        """Main polling loop (BaseWorker implementation)."""
        self.logger.info("Spotify poll loop started")

        while self._running:
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
                self.logger.error(f"Error polling Spotify: {type(e).__name__}: {e}")
                # Uncomment for full traceback during debugging:
                # import traceback
                # self.logger.error(f"Traceback: {traceback.format_exc()}")

            # Sleep
            time.sleep(self.poll_interval)

        # Loop exits when self._running = False (BaseWorker.stop() logs 'stopped')

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
            self.logger.error(f"Failed to parse Spotify playback: {e}")
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
            self.logger.error(f"Error getting current track: {e}")

        return None

    # ===== Playback Control Methods =====

    def next_track(self) -> bool:
        """Skip to next track.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.sp:
            self.logger.warning("Spotify not enabled, cannot skip track")
            return False

        try:
            self.sp.next_track()
            self.logger.info("Spotify: Skipped to next track")
            return True
        except Exception as e:
            self.logger.error(f"Failed to skip track: {e}")
            return False

    def previous_track(self) -> bool:
        """Go to previous track.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.sp:
            self.logger.warning("Spotify not enabled, cannot go to previous track")
            return False

        try:
            self.sp.previous_track()
            self.logger.info("Spotify: Went to previous track")
            return True
        except Exception as e:
            self.logger.error(f"Failed to go to previous track: {e}")
            return False

    def pause_playback(self) -> bool:
        """Pause current playback.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.sp:
            self.logger.warning("Spotify not enabled, cannot pause")
            return False

        try:
            self.sp.pause_playback()
            self.logger.info("Spotify: Paused playback")
            return True
        except Exception as e:
            self.logger.error(f"Failed to pause playback: {e}")
            return False

    def resume_playback(self) -> bool:
        """Resume/play current playback.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.sp:
            self.logger.warning("Spotify not enabled, cannot resume")
            return False

        try:
            self.sp.start_playback()
            self.logger.info("Spotify: Resumed playback")
            return True
        except Exception as e:
            self.logger.error(f"Failed to resume playback: {e}")
            return False

    def restart_track(self) -> bool:
        """Restart current track from beginning.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.sp:
            self.logger.warning("Spotify not enabled, cannot restart track")
            return False

        try:
            # Seek to position 0 (start of track)
            self.sp.seek_track(0)
            self.logger.info("Spotify: Restarted track from beginning")
            return True
        except Exception as e:
            self.logger.error(f"Failed to restart track: {e}")
            return False

    def set_volume(self, volume_percent: int) -> bool:
        """Set volume to specific level.

        Args:
            volume_percent: Volume level (0-100)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.sp:
            self.logger.warning("Spotify not enabled, cannot set volume")
            return False

        try:
            # Clamp volume to 0-100
            volume_percent = max(0, min(100, volume_percent))
            self.sp.volume(volume_percent)
            self.logger.info(f"Spotify: Set volume to {volume_percent}%")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set volume: {e}")
            return False

    def increase_volume(self, step: int = 10) -> bool:
        """Increase volume by step amount.

        Args:
            step: Amount to increase (default: 10%)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.sp:
            self.logger.warning("Spotify not enabled, cannot increase volume")
            return False

        try:
            # Get current volume
            playback = self.sp.current_playback()
            if not playback or not playback.get("device"):
                self.logger.warning("Cannot increase volume: No active device")
                return False

            current_volume = playback["device"].get("volume_percent", 50)
            new_volume = min(100, current_volume + step)

            self.sp.volume(new_volume)
            self.logger.info(f"Spotify: Increased volume to {new_volume}% (was {current_volume}%)")
            return True
        except Exception as e:
            self.logger.error(f"Failed to increase volume: {e}")
            return False

    def decrease_volume(self, step: int = 10) -> bool:
        """Decrease volume by step amount.

        Args:
            step: Amount to decrease (default: 10%)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.sp:
            self.logger.warning("Spotify not enabled, cannot decrease volume")
            return False

        try:
            # Get current volume
            playback = self.sp.current_playback()
            if not playback or not playback.get("device"):
                self.logger.warning("Cannot decrease volume: No active device")
                return False

            current_volume = playback["device"].get("volume_percent", 50)
            new_volume = max(0, current_volume - step)

            self.sp.volume(new_volume)
            self.logger.info(f"Spotify: Decreased volume to {new_volume}% (was {current_volume}%)")
            return True
        except Exception as e:
            self.logger.error(f"Failed to decrease volume: {e}")
            return False
