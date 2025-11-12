"""Consolidated scene registry - definitions, factory, and registration."""

import importlib
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from nrhof.core.app_context import AppContext

if TYPE_CHECKING:
    from nrhof.scenes.scene_manager import Scene, SceneManager


class SceneDefinition:
    """Definition of a scene for factory creation."""

    def __init__(self, name: str, module_path: str, class_name: str, eager_load: bool = False):
        """Initialize scene definition.

        Args:
            name: Scene name for registration
            module_path: Python module path (e.g., 'nrhof.scenes.menu_scene')
            class_name: Class name within the module
            eager_load: Whether to load immediately or lazily
        """
        self.name = name
        self.module_path = module_path
        self.class_name = class_name
        self.eager_load = eager_load


class SceneFactory:
    """Factory for creating and caching scene instances.

    Responsibilities:
    - Lazy loading of scene classes
    - Instance caching to avoid recreating scenes
    - Background preloading for performance
    - Dependency injection via AppContext
    """

    def __init__(self, app_context: AppContext):
        """Initialize scene factory.

        Args:
            app_context: Application context for dependency injection
        """
        self._app_context = app_context
        self._definitions: dict[str, SceneDefinition] = {}
        self._instances: dict[str, "Scene"] = {}
        self._factories: dict[str, Callable] = {}
        self._lock = threading.Lock()

    def register_definition(self, definition: SceneDefinition):
        """Register a scene definition.

        Args:
            definition: SceneDefinition instance
        """
        self._definitions[definition.name] = definition

    def register_definitions(self, definitions: list[SceneDefinition]):
        """Register multiple scene definitions.

        Args:
            definitions: List of SceneDefinition instances
        """
        for definition in definitions:
            self.register_definition(definition)

    def create(self, scene_name: str) -> "Scene":
        """Create or retrieve a scene instance.

        Uses caching to avoid recreating scenes. Thread-safe.

        Args:
            scene_name: Name of the scene to create

        Returns:
            Scene instance

        Raises:
            KeyError: If scene name not registered
            ImportError: If scene module cannot be imported
            AttributeError: If scene class not found in module
        """
        # Check cache first (fast path, no lock needed for read)
        if scene_name in self._instances:
            return self._instances[scene_name]

        # Acquire lock for creation
        with self._lock:
            # Double-check after acquiring lock
            if scene_name in self._instances:
                return self._instances[scene_name]

            # Get definition
            if scene_name not in self._definitions:
                raise KeyError(f"Scene '{scene_name}' not registered in factory")

            definition = self._definitions[scene_name]

            # Create instance
            instance = self._create_instance(definition)

            # Cache instance
            self._instances[scene_name] = instance

            return instance

    def _create_instance(self, definition: SceneDefinition) -> "Scene":
        """Create a scene instance from definition.

        Args:
            definition: SceneDefinition to instantiate

        Returns:
            Scene instance
        """
        # Import module
        module = importlib.import_module(definition.module_path)

        # Get class
        scene_class = getattr(module, definition.class_name)

        # Instantiate with app context
        return scene_class(self._app_context)

    def preload(self, scene_names: list[str]):
        """Preload scenes in the background.

        Args:
            scene_names: List of scene names to preload
        """
        for scene_name in scene_names:
            if scene_name not in self._instances:
                try:
                    self.create(scene_name)
                except Exception as e:
                    print(f"Warning: Failed to preload scene '{scene_name}': {e}")

    def preload_async(self, scene_names: list[str]):
        """Preload scenes asynchronously in a background thread.

        Args:
            scene_names: List of scene names to preload
        """
        thread = threading.Thread(
            target=self.preload,
            args=(scene_names,),
            daemon=True,
            name="scene_preload_async",
        )
        thread.start()

    def get_cached_scenes(self) -> list[str]:
        """Get list of currently cached scene names.

        Returns:
            List of scene names that are currently cached
        """
        return list(self._instances.keys())

    def clear_cache(self, scene_name: str | None = None):
        """Clear cached scene instances.

        Args:
            scene_name: Specific scene to clear, or None to clear all
        """
        with self._lock:
            if scene_name:
                self._instances.pop(scene_name, None)
            else:
                self._instances.clear()

    def create_factory(self, scene_name: str) -> Callable:
        """Create a factory function for lazy scene creation.

        This is for backward compatibility with the old factory pattern.

        Args:
            scene_name: Name of the scene

        Returns:
            Factory function that creates the scene when called
        """
        if scene_name in self._factories:
            return self._factories[scene_name]

        def factory():
            return self.create(scene_name)

        self._factories[scene_name] = factory
        return factory


# ============================================================================
# Scene Definitions
# ============================================================================

SCENE_DEFINITIONS = [
    # Eager-loaded scenes (loaded immediately)
    SceneDefinition("SplashScene", "nrhof.scenes.splash_scene", "SplashScene", eager_load=True),
    # Lazy-loaded scenes (loaded on demand)
    SceneDefinition("IntroScene", "nrhof.scenes.intro_scene", "IntroScene"),
    SceneDefinition("MenuScene", "nrhof.scenes.menu_scene", "MenuScene"),
    SceneDefinition("NR38Scene", "nrhof.scenes.nr38_scene", "NR38Scene"),
    SceneDefinition("BandDetailsScene", "nrhof.scenes.band_details_scene", "BandDetailsScene"),
    SceneDefinition("SettingsScene", "nrhof.scenes.settings_scene", "SettingsScene"),
    SceneDefinition("VisualizersScene", "nrhof.scenes.visualizers_scene", "VisualizersScene"),
]


# ============================================================================
# Registration Functions
# ============================================================================


def create_scene_factory(app_context: AppContext) -> SceneFactory:
    """Create and configure the scene factory.

    Args:
        app_context: AppContext instance

    Returns:
        Configured SceneFactory instance
    """
    factory = SceneFactory(app_context)
    factory.register_definitions(SCENE_DEFINITIONS)
    return factory


def register_all_scenes(scene_manager: "SceneManager", app_context: AppContext):
    """Register all scenes with the scene manager using SceneFactory.

    Args:
        scene_manager: SceneManager instance
        app_context: AppContext instance
    """
    # Create scene factory
    factory = create_scene_factory(app_context)

    # Register scenes
    for definition in SCENE_DEFINITIONS:
        if definition.eager_load:
            # Eager load: create instance immediately
            scene_instance = factory.create(definition.name)
            scene_manager.register_scene(definition.name, scene_instance)
        else:
            # Lazy load: register factory for later instantiation
            scene_factory = factory.create_factory(definition.name)
            scene_manager.register_lazy(definition.name, scene_factory)


def get_preload_list() -> list[str]:
    """Get list of scene names to preload in background.

    Returns:
        List of scene names (excludes eager-loaded scenes)
    """
    return [definition.name for definition in SCENE_DEFINITIONS if not definition.eager_load]
