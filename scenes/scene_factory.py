#!/usr/bin/env python3
"""Scene factory for creating and managing scene instances."""

import importlib
import threading
from typing import Dict, Optional, Callable
from core.app_context import AppContext


class SceneDefinition:
    """Definition of a scene for factory creation."""
    
    def __init__(self, name: str, module_path: str, class_name: str, eager_load: bool = False):
        """Initialize scene definition.
        
        Args:
            name: Scene name for registration
            module_path: Python module path (e.g., 'scenes.menu_scene')
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
        self._definitions: Dict[str, SceneDefinition] = {}
        self._instances: Dict[str, 'Scene'] = {}
        self._factories: Dict[str, Callable] = {}
        self._lock = threading.Lock()
    
    def register_definition(self, definition: SceneDefinition):
        """Register a scene definition.
        
        Args:
            definition: SceneDefinition instance
        """
        self._definitions[definition.name] = definition
    
    def register_definitions(self, definitions: list):
        """Register multiple scene definitions.
        
        Args:
            definitions: List of SceneDefinition instances
        """
        for definition in definitions:
            self.register_definition(definition)
    
    def create(self, scene_name: str) -> 'Scene':
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
    
    def _create_instance(self, definition: SceneDefinition) -> 'Scene':
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
    
    def preload(self, scene_names: list):
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
    
    def preload_async(self, scene_names: list):
        """Preload scenes asynchronously in a background thread.
        
        Args:
            scene_names: List of scene names to preload
        """
        thread = threading.Thread(target=self.preload, args=(scene_names,), daemon=True)
        thread.start()
    
    def get_cached_scenes(self) -> list:
        """Get list of currently cached scene names.
        
        Returns:
            List of scene names that are currently cached
        """
        return list(self._instances.keys())
    
    def clear_cache(self, scene_name: Optional[str] = None):
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