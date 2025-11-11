#!/usr/bin/env python3
"""Sonos integration using local network discovery."""

import re
import time

import soco
from soco.discovery import discover

from core.now_playing import Track
from core.source_manager import SourceManager
from workers.base import BaseWorker


class SonosSource(BaseWorker):
    """Polls Sonos speakers for currently playing track and updates SourceManager."""

    def __init__(self, config: dict, source_manager: SourceManager):
        """Initialize Sonos source.

        Args:
            config: Configuration dict
            source_manager: SourceManager instance
        """
        # Initialize BaseWorker FIRST (sets up self.logger)
        super().__init__(config, logger_name="sonos_source")

        self.source_manager = source_manager
        self.enabled = config.get("sonos", {}).get("enabled", False)

        # Sonos speaker
        self.speaker: soco.SoCo | None = None

        # Polling settings
        self.poll_interval = config.get("sonos", {}).get("poll_interval_seconds", 2.0)
        self.target_room = config.get("sonos", {}).get("target_room")  # Optional: specific room

        if not self.enabled:
            self.logger.info("Sonos integration disabled in config")
            return

        # Spotify integration for progress tracking
        self.spotify_client = None
        self._init_spotify()

        # Discover Sonos speakers
        try:
            self._discover_speaker()
            if self.speaker:
                self.logger.info("Sonos speaker discovered", room=self.speaker.player_name)
            else:
                self.logger.warning("No Sonos speakers found on network")
                self.enabled = False
        except Exception as e:
            self.logger.error("Failed to discover Sonos speakers", error=str(e))
            self.enabled = False

    def _init_spotify(self):
        """Initialize Spotify client for progress tracking."""
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            spotify_config = self.config.get("spotify", {})
            if not spotify_config.get("enabled"):
                return

            client_id = spotify_config.get("client_id")
            client_secret = spotify_config.get("client_secret")
            redirect_uri = spotify_config.get("redirect_uri", "http://127.0.0.1:8888/callback")

            if client_id and client_secret:
                auth_manager = SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    scope="user-read-playback-state",
                    cache_path=".spotify_cache_sonos",
                )
                self.spotify_client = spotipy.Spotify(auth_manager=auth_manager)
                self.logger.info("Spotify client initialized for Sonos progress tracking")
        except Exception as e:
            self.logger.warning("Could not initialize Spotify for Sonos", error=str(e))

    def _discover_speaker(self):
        """Discover Sonos speakers on local network."""
        self.logger.info("Discovering Sonos speakers...")
        try:
            speakers = discover(timeout=10)
        except Exception as e:
            self.logger.error("Sonos discovery failed", error=str(e))
            return

        if not speakers:
            return

        # Log all discovered speakers
        room_names = [s.player_name for s in speakers]
        self.logger.info("Sonos speakers found", count=len(speakers), rooms=room_names)

        # If target room specified, find it
        if self.target_room:
            for speaker in speakers:
                if speaker.player_name.lower() == self.target_room.lower():
                    self.speaker = speaker
                    self.logger.info("Using target Sonos room", room=speaker.player_name)
                    return
            self.logger.warning("Target room not found", target=self.target_room)

        # Find first actively playing speaker
        for speaker in speakers:
            try:
                transport_info = speaker.get_current_transport_info()
                if transport_info.get("current_transport_state") == "PLAYING":
                    self.speaker = speaker
                    self.logger.info(
                        "Using actively playing Sonos speaker", room=speaker.player_name
                    )
                    return
            except Exception:
                # Optional: consider logging here, e.g., self.logger.debug("sonos parsing failed", exc_info=True)
                continue

        # Fallback to coordinator
        for speaker in speakers:
            if speaker.is_coordinator:
                self.speaker = speaker
                self.logger.info(
                    "No active Sonos playback, using coordinator", room=speaker.player_name
                )
                return

        # Final fallback to any speaker
        self.speaker = list(speakers)[0]
        self.logger.info("Using first Sonos speaker", room=self.speaker.player_name)

    def start(self):
        """Start polling Sonos."""
        if not self.enabled:
            self.logger.info("Sonos source not started (disabled)")
            return

        # Call BaseWorker.start() which handles threading
        super().start()

    def _worker_loop(self):
        """Main polling loop (BaseWorker implementation)."""
        self.logger.info("Sonos poll loop started")

        while self._running:
            try:
                # If target room is set, stick to that speaker
                if self.target_room:
                    # Get current playback from target speaker
                    track_info = self.speaker.get_current_track_info()
                    transport_info = self.speaker.get_current_transport_info()

                    transport_state = transport_info.get("current_transport_state")
                    is_playing = transport_state == "PLAYING"

                    if is_playing and track_info:
                        track = self._parse_track_info(track_info, is_playing)
                        if track:
                            # Try to get progress from Spotify if playing Spotify
                            self._enrich_with_spotify_progress(track, track_info)
                            self.source_manager.set_from("sonos", track)
                    else:
                        self.source_manager.set_from("sonos", None)
                else:
                    # Dynamic mode: find any actively playing speaker
                    active_track = None
                    speakers = discover(timeout=2)

                    if speakers:
                        for speaker in speakers:
                            try:
                                transport_info = speaker.get_current_transport_info()
                                if transport_info.get("current_transport_state") == "PLAYING":
                                    track_info = speaker.get_current_track_info()
                                    if track_info:
                                        # Temporarily set speaker for parsing
                                        old_speaker = self.speaker
                                        self.speaker = speaker
                                        active_track = self._parse_track_info(
                                            track_info,
                                            is_playing=True,
                                        )
                                        self.speaker = old_speaker

                                        if active_track:
                                            # Try to get progress from Spotify if playing Spotify
                                            self._enrich_with_spotify_progress(
                                                active_track,
                                                track_info,
                                            )
                                            break
                            except Exception:
                                # Optional: consider logging here, e.g., logger.debug("sonos parsing failed", exc_info=True)
                                continue

                    if active_track:
                        self.source_manager.set_from("sonos", active_track)
                    else:
                        self.source_manager.set_from("sonos", None)

            except Exception as e:
                self.logger.error("Error polling Sonos", error=str(e))

            # Sleep until next poll
            time.sleep(self.poll_interval)

        self.logger.info("Sonos poll loop ended")

    def _parse_track_info(self, track_info: dict, is_playing: bool = True) -> Track | None:
        """Parse Sonos track info into Track.

        Args:
            track_info: Sonos track info dict
            is_playing: Whether the track is currently playing

        Returns:
            Track or None
        """
        try:
            title = track_info.get("title", "Unknown")
            artist = track_info.get("artist", "Unknown")
            album = track_info.get("album")
            duration = track_info.get("duration")  # Format: "0:03:45"

            # Convert duration to milliseconds
            duration_ms = None
            if duration:
                try:
                    parts = duration.split(":")
                    if len(parts) == 3:
                        h, m, s = parts
                        duration_ms = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000
                except Exception:
                    # Optional: consider logging here, e.g., logger.debug("sonos parsing failed", exc_info=True)
                    pass

            # Get position (progress) from Sonos
            position = track_info.get("position")  # Format: "0:03:45"
            progress_ms = None
            if position:
                try:
                    parts = position.split(":")
                    if len(parts) == 3:
                        h, m, s = parts
                        progress_ms = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000
                except Exception:
                    # Optional: consider logging here, e.g., logger.debug("sonos parsing failed", exc_info=True)
                    pass

            # Get album art URL
            album_art = track_info.get("album_art")
            if album_art and not album_art.startswith("http"):
                # Make it absolute URL
                album_art = f"http://{self.speaker.ip_address}:1400{album_art}"

            # Get room info
            room_name = self.speaker.player_name
            volume = self.speaker.volume

            # Get grouped rooms
            grouped_rooms = []
            try:
                group = self.speaker.group
                if group:
                    grouped_rooms = [
                        member.player_name
                        for member in group.members
                        if member.player_name != room_name
                    ]
            except Exception:
                # Optional: consider logging here, e.g., logger.debug("sonos parsing failed", exc_info=True)
                pass

            return Track(
                title=title,
                artist=artist,
                album=album,
                confidence=1.0,
                source="sonos",
                duration_ms=duration_ms,
                progress_ms=progress_ms,
                image_url=album_art,
                is_playing=is_playing,
                sonos_room=room_name,
                sonos_volume=volume,
                sonos_grouped_rooms=grouped_rooms if grouped_rooms else None,
            )

        except Exception as e:
            self.logger.error("Failed to parse Sonos track info", error=str(e))
            return None

    def _enrich_with_spotify_progress(self, track: Track, track_info: dict):
        """Enrich track with Spotify progress if playing from Spotify.

        Args:
            track: Track object to enrich
            track_info: Sonos track info dict
        """
        if not self.spotify_client:
            return

        try:
            # Check if this is a Spotify track
            # Sonos metadata includes URI like: x-sonos-spotify:spotify%3atrack%3a...
            track_info.get("metadata", "")
            uri = track_info.get("uri", "")

            # Extract Spotify track ID from URI or metadata
            spotify_id = None

            # Try to extract from URI
            if "spotify" in uri.lower():
                # Format: x-sonos-spotify:spotify%3atrack%3a{track_id}
                # Match after %3atrack%3a or :track:
                match = re.search(r"track(?:%3a|:)([a-zA-Z0-9]+)", uri, re.IGNORECASE)
                if match:
                    spotify_id = match.group(1)

            if not spotify_id:
                return

            # Get current playback from Spotify API
            playback = self.spotify_client.current_playback()
            if playback and playback.get("item"):
                item = playback["item"]
                item_id = item.get("id")
                # Verify it's the same track
                if item_id == spotify_id:
                    track.progress_ms = playback.get("progress_ms")
                    track.is_playing = playback.get("is_playing", True)
                    track.spotify_id = spotify_id
                    self.logger.debug(
                        "Enriched Sonos track with Spotify progress",
                        progress_ms=track.progress_ms,
                        spotify_id=spotify_id,
                    )

        except Exception as e:
            self.logger.debug("Could not enrich with Spotify progress", error=str(e))
