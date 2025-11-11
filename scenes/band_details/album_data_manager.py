#!/usr/bin/env python3
"""Album data manager for fetching and caching album data from Webflow."""
import hashlib
import json
import logging
import time
from pathlib import Path

from integrations.webflow_constants import ALBUM_TYPE_UUIDS


class AlbumDataManager:
    """Manages album data fetching, caching, and filtering."""

    def __init__(
        self,
        logger: logging.Logger,
        albums_cache_file: Path,
        albums_cache_ttl_hours: int,
        images_cache_dir: Path,
    ):
        self.logger = logger
        self.albums_cache_file = albums_cache_file
        self.albums_cache_ttl_hours = albums_cache_ttl_hours
        self.images_cache_dir = images_cache_dir
        self.albums_by_type = {}

    def load_albums_from_cache_file(self):
        """Load all albums from disk cache if available and not expired."""
        try:
            if not self.albums_cache_file.exists():
                return None

            with open(self.albums_cache_file) as f:
                cache_data = json.load(f)

            cache_timestamp = cache_data.get("timestamp", 0)
            cache_age_hours = (time.time() - cache_timestamp) / 3600

            if cache_age_hours > self.albums_cache_ttl_hours:
                return None

            return cache_data.get("albums", [])

        except Exception as e:
            self.logger.error(f"Error loading albums cache: {e}")
            return None

    def save_albums_to_cache_file(self, albums):
        """Save all albums to disk cache."""
        try:
            self.albums_cache_file.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                "timestamp": time.time(),
                "ttl_hours": self.albums_cache_ttl_hours,
                "albums": albums,
            }

            with open(self.albums_cache_file, "w") as f:
                json.dump(cache_data, f)

        except Exception as e:
            self.logger.error(f"Error saving albums cache: {e}")

    def fetch_albums_for_band(self, band_id: str, album_type: str, webflow_cache_manager):
        """Fetch albums from Webflow for the given band and type."""
        if not band_id:
            self.logger.warning("No band ID set, cannot fetch albums")
            return

        self.logger.info(f"Fetching albums for band_id={band_id}, type={album_type}")

        if album_type in self.albums_by_type and len(self.albums_by_type[album_type]) > 0:
            self.logger.info(f"Using cached albums for type: {album_type}")
            return

        cached_albums = self.load_albums_from_cache_file()
        if cached_albums:
            albums = cached_albums
        else:
            albums = self._fetch_from_webflow(webflow_cache_manager)
            if not albums:
                return

        filtered_albums = self._filter_and_sort_albums(albums, band_id, album_type)
        self.albums_by_type[album_type] = filtered_albums
        self.logger.info(f"Fetched {len(filtered_albums)} albums for type: {album_type}")

    def _fetch_from_webflow(self, webflow_cache_manager):
        """Fetch all albums from Webflow with pagination."""
        try:
            if not webflow_cache_manager:
                self.logger.warning("Webflow cache manager not available")
                return None

            webflow_client = webflow_cache_manager.client
            if not webflow_client:
                self.logger.warning("Webflow client not available")
                return None

            all_albums = []
            offset = 0
            limit = 100

            while True:
                albums_batch = webflow_client.get_collection_items(
                    webflow_client.config.collection_id_albums, limit=limit, offset=offset
                )
                if not albums_batch:
                    break
                all_albums.extend(albums_batch)
                if len(albums_batch) < limit:
                    break
                offset += limit

            if not all_albums:
                self.logger.warning("No albums fetched from Webflow")
                return None

            self.logger.info(f"Fetched {len(all_albums)} total albums from Webflow")
            self.save_albums_to_cache_file(all_albums)
            return all_albums

        except Exception as e:
            self.logger.error(f"Error fetching albums: {e}")
            return None

    def _filter_and_sort_albums(self, albums, band_id, album_type):
        """Filter albums by band and type, then sort by year."""
        filtered_albums = []

        for album in albums:
            field_data = album.get("fieldData", {})
            album_band_id = field_data.get("band")

            if album_band_id != band_id:
                continue

            album_type_uuid = field_data.get("type", "")
            mapped_type = ALBUM_TYPE_UUIDS.get(album_type_uuid, "etc")

            if mapped_type == album_type:
                filtered_albums.append(album)

        def get_year(album):
            year_str = album.get("fieldData", {}).get("year", "9999")
            try:
                return int(year_str) if year_str else 9999
            except (ValueError, TypeError):
                return 9999

        filtered_albums.sort(key=get_year)
        return filtered_albums

    def get_image_cache_path(self, url: str) -> Path:
        """Get the cache file path for a given image URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.images_cache_dir / f"{url_hash}.png"
