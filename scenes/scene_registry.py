#!/usr/bin/env python3
"""Scene registry - centralized scene definitions and registration."""

from typing import List
from scenes.scene_manager import SceneManager
from scenes.scene_factory import SceneFactory, SceneDefinition
from core.app_context import AppContext


# Scene definitions using SceneDefinition objects
SCENE_DEFINITIONS = [
    # Eager-loaded scenes (loaded immediately)
    SceneDefinition('SplashScene', 'scenes.splash_scene', 'SplashScene', eager_load=True),
    
    # Lazy-loaded scenes (loaded on demand)
    SceneDefinition('IntroScene', 'scenes.intro_scene', 'IntroScene'),
    SceneDefinition('MenuScene', 'scenes.menu_scene', 'MenuScene'),
    # Visualizer scenes are now embedded in VisualizersScene, not standalone
    SceneDefinition('SettingsScene', 'scenes.settings_scene', 'SettingsScene'),
    SceneDefinition('VisualizersScene', 'scenes.visualizers_scene', 'VisualizersScene'),
]


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


def register_all_scenes(scene_manager: SceneManager, app_context: AppContext):
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


def get_preload_list() -> List[str]:
    """Get list of scene names to preload in background.
    
    Returns:
        List of scene names (excludes eager-loaded scenes)
    """
    return [
        definition.name for definition in SCENE_DEFINITIONS
        if not definition.eager_load
    ]