#!/usr/bin/env python3
"""Scene registry - centralized scene definitions and registration."""

import importlib
from typing import List, Tuple
from scenes.scene_manager import SceneManager
from core.app_context import AppContext


# Scene definitions: (name, module_path, class_name, eager_load)
SCENE_DEFINITIONS = [
    # Eager-loaded scenes (loaded immediately)
    ('SplashScene', 'scenes.splash_scene', 'SplashScene', True),
    
    # Lazy-loaded scenes (loaded on demand)
    ('IntroScene', 'scenes.intro_scene', 'IntroScene', False),
    ('MenuScene', 'scenes.menu_scene', 'MenuScene', False),
    ('Experience1HubScene', 'scenes.experience1_hub_scene', 'Experience1HubScene', False),
    ('Experience1SpectrumBarsScene', 'scenes.experience1_spectrum_bars', 'Experience1SpectrumBarsScene', False),
    ('Experience1WaveformScene', 'scenes.experience1_waveform', 'Experience1WaveformScene', False),
    ('Experience1LissajousScene', 'scenes.experience1_lissajous', 'Experience1LissajousScene', False),
    ('Experience2HubScene', 'scenes.experience2_hub_scene', 'Experience2HubScene', False),
    ('VideoListScene', 'scenes.video_list_scene', 'VideoListScene', False),
    ('VideoPlayerScene', 'scenes.video_player_scene', 'VideoPlayerScene', False),
]


def _make_scene_factory(module_name: str, class_name: str, app_context: AppContext):
    """Create a factory function for lazy-loading a scene.
    
    Args:
        module_name: Module path (e.g., 'scenes.intro_scene')
        class_name: Class name (e.g., 'IntroScene')
        app_context: AppContext instance
        
    Returns:
        Factory function that creates the scene when called
    """
    def factory():
        module = importlib.import_module(module_name)
        scene_class = getattr(module, class_name)
        return scene_class(app_context)
    return factory


def register_all_scenes(scene_manager: SceneManager, app_context: AppContext):
    """Register all scenes with the scene manager.
    
    Args:
        scene_manager: SceneManager instance
        app_context: AppContext instance
    """
    for name, module_path, class_name, eager_load in SCENE_DEFINITIONS:
        if eager_load:
            # Eager load: import and instantiate immediately
            module = importlib.import_module(module_path)
            scene_class = getattr(module, class_name)
            scene_instance = scene_class(app_context)
            scene_manager.register_scene(name, scene_instance)
        else:
            # Lazy load: register factory for later instantiation
            factory = _make_scene_factory(module_path, class_name, app_context)
            scene_manager.register_lazy(name, factory)


def get_preload_list() -> List[str]:
    """Get list of scene names to preload in background.
    
    Returns:
        List of scene names (excludes eager-loaded scenes)
    """
    return [
        name for name, _, _, eager_load in SCENE_DEFINITIONS
        if not eager_load
    ]