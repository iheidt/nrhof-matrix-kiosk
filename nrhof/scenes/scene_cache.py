#!/usr/bin/env python3
"""Scene caching and lazy loading functionality."""

import threading
import time
from collections.abc import Callable


class SceneCache:
    """Manages scene instances with lazy loading support."""

    def __init__(self):
        """Initialize scene cache."""
        self.scenes: dict[str, any] = {}  # Loaded scene instances
        self.lazy_factories: dict[str, Callable] = {}  # Lazy-load factories
        self.paused_scenes: dict[str, any] = {}  # Paused but not destroyed scenes

    def register(self, name: str, scene):
        """Register a scene instance.

        Args:
            name: Scene name
            scene: Scene instance
        """
        self.scenes[name] = scene

    def register_lazy(self, name: str, factory: Callable):
        """Register a lazy-loaded scene factory.

        Args:
            name: Scene name
            factory: Callable that returns a Scene instance when called
        """
        self.lazy_factories[name] = factory

    def ensure_loaded(self, name: str):
        """Ensure a scene is loaded, instantiating from factory if needed.

        Args:
            name: Scene name to ensure is loaded
        """
        # Already loaded
        if name in self.scenes:
            return

        # Load from lazy factory
        if name in self.lazy_factories:
            factory = self.lazy_factories[name]
            scene = factory()
            self.register(name, scene)
            return

        # Not found anywhere - will raise error in caller

    def get(self, name: str):
        """Get a scene by name.

        Args:
            name: Scene name

        Returns:
            Scene instance or None if not found
        """
        return self.scenes.get(name)

    def pause(self, name: str, scene):
        """Pause a scene (keep it loaded but inactive).

        Args:
            name: Scene name
            scene: Scene instance to pause
        """
        self.paused_scenes[name] = scene

    def resume(self, name: str):
        """Resume a paused scene.

        Args:
            name: Scene name

        Returns:
            Paused scene instance or None if not paused
        """
        return self.paused_scenes.pop(name, None)

    def is_paused(self, name: str) -> bool:
        """Check if a scene is paused.

        Args:
            name: Scene name

        Returns:
            True if scene is paused
        """
        return name in self.paused_scenes

    def preload_lazy(
        self,
        names: list,
        progress_cb: Callable[[int, int], None] | None = None,
        sleep_between: float = 0.0,
    ) -> threading.Thread:
        """Preload lazy scenes in a background thread.

        Args:
            names: List of scene names to preload
            progress_cb: Optional callback(done, total) called after each scene loads
            sleep_between: Optional delay between loading each scene

        Returns:
            Thread object (already started)
        """

        def _preload_worker():
            total = len(names)
            for i, name in enumerate(names):
                self.ensure_loaded(name)
                if progress_cb:
                    progress_cb(i + 1, total)
                if sleep_between > 0:
                    time.sleep(sleep_between)

        thread = threading.Thread(
            target=_preload_worker,
            daemon=True,
            name="scene_preload_worker",
        )
        thread.start()
        return thread

    def clear(self):
        """Clear all cached scenes."""
        self.scenes.clear()
        self.paused_scenes.clear()
