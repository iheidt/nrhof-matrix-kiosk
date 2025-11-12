"""Webflow CMS integration for syncing track playback data."""

import logging
import os
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

import requests


@dataclass
class WebflowConfig:
    """Webflow API configuration."""

    api_token: str
    site_id: str
    collection_id_bands: str
    collection_id_albums: str
    collection_id_songs: str
    enabled: bool = True
    sync_window: float = 300.0
    retry_backoff_max: int = 300
    timeout: int = 10


class WebflowClient:
    """Client for interacting with Webflow CMS API."""

    BASE_URL = "https://api.webflow.com/v2"

    def __init__(self, config: WebflowConfig, logger: logging.Logger | None = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._lock = Lock()
        self._last_sync: dict[str, float] = {}
        self._retry_backoff: dict[str, float] = {}
        self._collection_cache: dict[str, dict[str, str]] = {}  # Cache for lookups

        if not config.api_token:
            raise ValueError("Webflow API token is required")
        if not config.site_id:
            raise ValueError("Webflow site ID is required")
        if not config.collection_id_bands:
            raise ValueError("Webflow bands collection ID is required")
        if not config.collection_id_albums:
            raise ValueError("Webflow albums collection ID is required")
        if not config.collection_id_songs:
            raise ValueError("Webflow songs collection ID is required")

        self.logger.info("Webflow client initialized")

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_token}",
            "accept": "application/json",
            "content-type": "application/json",
        }

    def _can_sync(self, track_key: str) -> bool:
        with self._lock:
            last_sync = self._last_sync.get(track_key, 0.0)
            elapsed = time.time() - last_sync
            return elapsed >= self.config.sync_window

    def _mark_synced(self, track_key: str):
        with self._lock:
            self._last_sync[track_key] = time.time()
            if track_key in self._retry_backoff:
                del self._retry_backoff[track_key]

    def _get_backoff(self, track_key: str) -> float:
        with self._lock:
            return self._retry_backoff.get(track_key, 0.0)

    def _increase_backoff(self, track_key: str):
        with self._lock:
            current = self._retry_backoff.get(track_key, 1.0)
            new_backoff = min(current * 2, self.config.retry_backoff_max)
            self._retry_backoff[track_key] = new_backoff

    def _find_or_create_band(self, band_name: str) -> str | None:
        """Find or create a band in Webflow, return its ID."""
        # Check cache first
        cache_key = f"band:{band_name}"
        if cache_key in self._collection_cache:
            return self._collection_cache[cache_key]

        # Search for existing band
        try:
            items = self.get_collection_items(self.config.collection_id_bands)
            if items:
                for item in items:
                    if item.get("fieldData", {}).get("name", "").lower() == band_name.lower():
                        band_id = item.get("id")
                        self._collection_cache[cache_key] = band_id
                        return band_id
        except Exception as e:
            self.logger.error(f"Error searching for band: {e}")

        return None

    def _find_or_create_album(self, album_name: str, band_name: str) -> str | None:
        """Find or create an album in Webflow, return its ID."""
        cache_key = f"album:{album_name}:{band_name}"
        if cache_key in self._collection_cache:
            return self._collection_cache[cache_key]

        # Search for existing album
        try:
            items = self.get_collection_items(self.config.collection_id_albums)
            if items:
                for item in items:
                    field_data = item.get("fieldData", {})
                    if (
                        field_data.get("name", "").lower() == album_name.lower()
                        and field_data.get("band", "").lower() == band_name.lower()
                    ):
                        album_id = item.get("id")
                        self._collection_cache[cache_key] = album_id
                        return album_id
        except Exception as e:
            self.logger.error(f"Error searching for album: {e}")

        return None

    def sync_track(self, track_data: dict[str, Any]) -> bool:
        """Sync track playback to Webflow songs collection.

        Args:
            track_data: Track data with fields:
                - title: Track title (required)
                - artist: Artist name (required)
                - album: Album name (optional)
                - duration_ms: Track duration in ms (optional)
        """
        if not self.config.enabled:
            return False

        title = track_data.get("title")
        artist = track_data.get("artist")
        album = track_data.get("album", "")

        if not title or not artist:
            self.logger.error("Title and artist are required for sync")
            return False

        # Create unique key for rate limiting
        track_key = f"{artist}:{title}"

        if not self._can_sync(track_key):
            return False

        backoff = self._get_backoff(track_key)
        if backoff > 0:
            return False

        try:
            # Find or note band and album references
            album_id = None
            if album:
                album_id = self._find_or_create_album(album, artist)

            # Prepare song data
            slug = f"{artist}-{title}".lower().replace(" ", "-").replace("/", "-")
            item_data = {
                "fieldData": {
                    "name": title,
                    "slug": slug,
                    "time": str(track_data.get("duration_ms", 0)),
                    "score": "0",  # Default score
                },
            }

            # Add album reference if found
            if album_id:
                item_data["fieldData"]["album"] = album_id

            # Create/update song in collection
            url = f"{self.BASE_URL}/collections/{self.config.collection_id_songs}/items"
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=item_data,
                timeout=self.config.timeout,
            )

            if response.status_code in (200, 201):
                self._mark_synced(track_key)
                self.logger.info(f"Synced track: {artist} - {title}")
                return True
            else:
                self.logger.error(f"Sync failed: {response.status_code} - {response.text}")
                self._increase_backoff(track_key)
                return False

        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout syncing track {track_key}")
            self._increase_backoff(track_key)
            return False
        except Exception as e:
            self.logger.error(f"Error syncing track {track_key}: {e}")
            self._increase_backoff(track_key)
            return False

    def get_collection_items(
        self,
        collection_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        """Fetch items from a Webflow collection.

        Args:
            collection_id: The collection ID to fetch from
            limit: Maximum number of items
            offset: Pagination offset
        """
        try:
            url = f"{self.BASE_URL}/collections/{collection_id}/items"
            params = {"limit": limit, "offset": offset}

            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.config.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            else:
                self.logger.error(f"Failed to fetch items: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching items: {e}")
            return None

    def test_connection(self) -> bool:
        """Test connection to Webflow API."""
        try:
            url = f"{self.BASE_URL}/sites/{self.config.site_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=self.config.timeout)

            if response.status_code == 200:
                self.logger.info("Webflow connection successful")
                return True
            else:
                self.logger.error(f"Connection failed: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Connection test error: {e}")
            return False


def create_webflow_client(
    config: dict[str, Any],
    logger: logging.Logger | None = None,
) -> WebflowClient | None:
    """Create Webflow client from config."""
    webflow_config = config.get("integrations", {}).get("webflow", {})

    if not webflow_config.get("enabled", False):
        return None

    api_token = os.getenv("WEBFLOW_API_TOKEN")
    site_id = os.getenv("WEBFLOW_SITE_ID")
    collection_id_bands = os.getenv("WEBFLOW_COLLECTION_ID_BANDS")
    collection_id_albums = os.getenv("WEBFLOW_COLLECTION_ID_ALBUMS")
    collection_id_songs = os.getenv("WEBFLOW_COLLECTION_ID_SONGS")

    if not all(
        [api_token, site_id, collection_id_bands, collection_id_albums, collection_id_songs],
    ):
        if logger:
            logger.warning("Webflow enabled but missing credentials in .env")
        return None

    try:
        wf_config = WebflowConfig(
            api_token=api_token,
            site_id=site_id,
            collection_id_bands=collection_id_bands,
            collection_id_albums=collection_id_albums,
            collection_id_songs=collection_id_songs,
            enabled=True,
            sync_window=webflow_config.get("sync_window", 300.0),
            retry_backoff_max=webflow_config.get("retry_backoff_max", 300),
        )

        client = WebflowClient(wf_config, logger)
        if client.test_connection():
            return client
        return None
    except Exception as e:
        if logger:
            logger.error(f"Failed to create Webflow client: {e}")
        return None
