#!/usr/bin/env python3
"""Intent handlers for application navigation and actions."""

from routing.intent_router import IntentRouter, Intent
from scenes.scene_manager import SceneManager
from core.app_context import AppContext

# Backward compatibility alias
Intents = Intent


def register_all_intents(intent_router: IntentRouter, scene_manager: SceneManager, app_context: AppContext):
    """Register all application intents.
    
    Args:
        intent_router: IntentRouter instance
        scene_manager: SceneManager instance
        app_context: AppContext instance
    """
    # Navigation intents
    _register_navigation_intents(intent_router, scene_manager)
    
    # Selection intents
    _register_selection_intents(intent_router, scene_manager, app_context)


def _register_navigation_intents(intent_router: IntentRouter, scene_manager: SceneManager):
    """Register navigation intents (go home, go back, etc.)."""
    intent_router.register(Intents.GO_HOME, lambda **kw: scene_manager.switch_to("MenuScene"))
    intent_router.register(Intents.GO_BACK, lambda **kw: scene_manager.go_back())
    intent_router.register(Intents.GO_TO_SETTINGS, lambda **kw: scene_manager.switch_to("SettingsScene"))


def _register_selection_intents(intent_router: IntentRouter, scene_manager: SceneManager, app_context: AppContext):
    """Register selection intents (menu options, sub-experiences)."""
    
    # Main menu option selection
    def select_option_handler(index, **kw):
        if index == 0:
            # NR-38: Not implemented yet
            print(f"Placeholder: NR-38 not implemented yet")
        elif index == 1:
            # NR-18: Not implemented yet
            print(f"Placeholder: NR-18 not implemented yet")
        elif index == 2:
            # Visualizer
            scene_manager.switch_to("VisualizersScene")
        elif index == 3:
            # Fate maker: Not implemented yet
            print(f"Placeholder: Fate maker not implemented yet")
        else:
            print(f"Placeholder: Option {index+1} not implemented yet")
    
    intent_router.register(Intents.SELECT_OPTION, select_option_handler)
    
    # Sub-experience selection
    def select_sub_experience_handler(id, **kw):
        if id == "spectrum_bars":
            scene_manager.switch_to("Experience1SpectrumBarsScene")
        elif id == "waveform":
            scene_manager.switch_to("Experience1WaveformScene")
        elif id == "lissajous":
            scene_manager.switch_to("Experience1LissajousScene")
        else:
            print(f"Unknown sub-experience: {id}")
    
    intent_router.register(Intents.SELECT_SUB_EXPERIENCE, select_sub_experience_handler)