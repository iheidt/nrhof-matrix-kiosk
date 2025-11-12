"""Webflow CMS cache manager with pagination and local storage."""

import json
import logging
import time
from pathlib import Path
from threading import Lock
from typing import Any


class WebflowCache:
    """Manages local cache of Webflow CMS data with pagination support."""

    def __init__(
        self,
        cache_dir: str = "runtime/webflow_cache",
        logger: logging.Logger | None = None,
    ):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
            logger: Optional logger instance
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
        self._lock = Lock()

        # Cache metadata
        self._metadata_file = self.cache_dir / "metadata.json"
        self._metadata: dict[str, Any] = self._load_metadata()

    def _load_metadata(self) -> dict[str, Any]:
        """Load cache metadata from disk."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file) as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading cache metadata: {e}")
        return {"collections": {}, "last_refresh": 0, "etags": {}}

    def _save_metadata(self):
        """Save cache metadata to disk."""
        try:
            with open(self._metadata_file, "w") as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving cache metadata: {e}")

    def get_collection(self, collection_name: str) -> list[dict[str, Any]] | None:
        """Get cached collection data.

        Args:
            collection_name: Name of collection (e.g., 'bands', 'albums', 'songs')

        Returns:
            List of collection items, or None if not cached
        """
        cache_file = self.cache_dir / f"{collection_name}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)
                self.logger.debug(f"Loaded {len(data)} items from {collection_name} cache")
                return data
        except Exception as e:
            self.logger.error(f"Error loading {collection_name} cache: {e}")
            return None

    def set_collection(
        self,
        collection_name: str,
        items: list[dict[str, Any]],
        etag: str | None = None,
    ):
        """Save collection data to cache.

        Args:
            collection_name: Name of collection
            items: List of collection items
            etag: Optional ETag for conditional requests
        """
        with self._lock:
            cache_file = self.cache_dir / f"{collection_name}.json"

            try:
                with open(cache_file, "w") as f:
                    json.dump(items, f, indent=2)

                # Update metadata
                self._metadata["collections"][collection_name] = {
                    "count": len(items),
                    "updated": time.time(),
                }
                if etag:
                    self._metadata["etags"][collection_name] = etag

                self._save_metadata()
                self.logger.info(f"Cached {len(items)} items for {collection_name}")
            except Exception as e:
                self.logger.error(f"Error caching {collection_name}: {e}")

    def get_etag(self, collection_name: str) -> str | None:
        """Get stored ETag for collection.

        Args:
            collection_name: Name of collection

        Returns:
            ETag string, or None if not available
        """
        return self._metadata.get("etags", {}).get(collection_name)

    def is_stale(self, max_age_seconds: float = 86400) -> bool:
        """Check if cache is stale.

        Args:
            max_age_seconds: Maximum cache age in seconds (default: 24 hours)

        Returns:
            True if cache should be refreshed
        """
        last_refresh = self._metadata.get("last_refresh", 0)
        age = time.time() - last_refresh
        return age > max_age_seconds

    def mark_refreshed(self):
        """Mark cache as freshly refreshed."""
        with self._lock:
            self._metadata["last_refresh"] = time.time()
            self._save_metadata()

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache information.

        Returns:
            Dictionary with cache stats
        """
        return {
            "collections": self._metadata.get("collections", {}),
            "last_refresh": self._metadata.get("last_refresh", 0),
            "age_seconds": time.time() - self._metadata.get("last_refresh", 0),
        }

    def clear(self, collection_name: str | None = None):
        """Clear cache.

        Args:
            collection_name: Specific collection to clear, or None for all
        """
        with self._lock:
            if collection_name:
                cache_file = self.cache_dir / f"{collection_name}.json"
                if cache_file.exists():
                    cache_file.unlink()
                if collection_name in self._metadata.get("collections", {}):
                    del self._metadata["collections"][collection_name]
                if collection_name in self._metadata.get("etags", {}):
                    del self._metadata["etags"][collection_name]
                self.logger.info(f"Cleared cache for {collection_name}")
            else:
                # Clear all
                for cache_file in self.cache_dir.glob("*.json"):
                    if cache_file.name != "metadata.json":
                        cache_file.unlink()
                self._metadata = {"collections": {}, "last_refresh": 0, "etags": {}}
                self.logger.info("Cleared all cache")

            self._save_metadata()


class WebflowCacheManager:
    """High-level manager for Webflow CMS data with automatic refresh."""

    def __init__(
        self,
        webflow_client,
        cache: WebflowCache,
        logger: logging.Logger | None = None,
    ):
        """Initialize cache manager.

        Args:
            webflow_client: WebflowClient instance
            cache: WebflowCache instance
            logger: Optional logger instance
        """
        self.client = webflow_client
        self.cache = cache
        self.logger = logger or logging.getLogger(__name__)
        self._refreshing = False

    def _fetch_all_pages(self, collection_id: str, collection_name: str) -> list[dict[str, Any]]:
        """Fetch all pages of a collection with pagination.

        Args:
            collection_id: Webflow collection ID
            collection_name: Human-readable collection name for logging

        Returns:
            List of all items across all pages
        """
        all_items = []
        offset = 0
        limit = 100

        while True:
            self.logger.debug(f"Fetching {collection_name} page (offset={offset})")
            items = self.client.get_collection_items(collection_id, limit=limit, offset=offset)

            if not items:
                break

            all_items.extend(items)

            # If we got fewer items than the limit, we've reached the end
            if len(items) < limit:
                break

            offset += limit

        self.logger.info(f"Fetched {len(all_items)} total items for {collection_name}")
        return all_items

    def refresh_all(self, force: bool = False) -> bool:
        """Refresh all collections from Webflow.

        Args:
            force: Force refresh even if cache is fresh

        Returns:
            True if refresh was successful
        """
        if self._refreshing:
            self.logger.debug("Refresh already in progress")
            return False

        if not force and not self.cache.is_stale():
            self.logger.debug("Cache is fresh, skipping refresh")
            return True

        self._refreshing = True

        try:
            self.logger.info("Starting Webflow cache refresh...")

            # Fetch bands (38 items, 1 page)
            bands = self._fetch_all_pages(self.client.config.collection_id_bands, "bands")
            if bands:
                self.cache.set_collection("bands", bands)

            # Fetch songs (10 items, 1 page)
            songs = self._fetch_all_pages(self.client.config.collection_id_songs, "songs")
            if songs:
                self.cache.set_collection("songs", songs)

            # Fetch albums (487 items, ~5 pages)
            albums = self._fetch_all_pages(self.client.config.collection_id_albums, "albums")
            if albums:
                self.cache.set_collection("albums", albums)

            # Mark cache as refreshed
            self.cache.mark_refreshed()

            self.logger.info("Webflow cache refresh complete")
            return True

        except Exception as e:
            self.logger.error(f"Error refreshing Webflow cache: {e}")
            return False
        finally:
            self._refreshing = False

    def get_bands(self, filter_list: str | None = None) -> list[dict[str, Any]]:
        """Get bands from cache.

        Args:
            filter_list: Optional filter by nerd-rock-list field (e.g., 'NR-38')

        Returns:
            List of band items
        """
        bands = self.cache.get_collection("bands") or []

        if filter_list:
            bands = [
                band
                for band in bands
                if band.get("fieldData", {}).get("nerd-rock-list") == filter_list
            ]

        return bands

    def get_albums(self) -> list[dict[str, Any]]:
        """Get albums from cache."""
        return self.cache.get_collection("albums") or []

    def get_songs(self) -> list[dict[str, Any]]:
        """Get songs from cache."""
        return self.cache.get_collection("songs") or []

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache information."""
        return self.cache.get_cache_info()
