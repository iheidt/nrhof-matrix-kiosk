#!/usr/bin/env python3
"""Intent handlers for application navigation and actions."""

from routing.intent_router import IntentRouter, Intents
from scenes.scene_manager import SceneManager
from core.app_context import AppContext


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
    """Register navigation intents (go home, go to hub, etc.)."""
    intent_router.register(Intents.GO_HOME, lambda **kw: scene_manager.switch_to("MenuScene"))
    intent_router.register(Intents.GO_TO_EXPERIENCE1_HUB, lambda **kw: scene_manager.switch_to("Experience1HubScene"))
    intent_router.register(Intents.GO_TO_EXPERIENCE2_HUB, lambda **kw: scene_manager.switch_to("Experience2HubScene"))


def _register_selection_intents(intent_router: IntentRouter, scene_manager: SceneManager, app_context: AppContext):
    """Register selection intents (menu options, sub-experiences)."""
    
    # Main menu option selection
    def select_option_handler(index, **kw):
        if index == 0:
            # NR-38: Music video (was Experience 2)
            scene_manager.switch_to("Experience2HubScene")
        elif index == 1:
            # NR-18: Not implemented yet
            print(f"Placeholder: NR-18 not implemented yet")
        elif index == 2:
            # Visualizer (was Experience 1)
            scene_manager.switch_to("Experience1HubScene")
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
        elif id == "video_list":
            scene_manager.switch_to("VideoListScene")
        elif id.startswith("video:"):
            # Extract filename from id (format: "video:filename.mp4")
            filename = id.split(":", 1)[1]
            # Store filename in app context for the video player to pick up
            app_context.selected_video = filename
            scene_manager.switch_to("VideoPlayerScene")
        else:
            print(f"Unknown sub-experience: {id}")
    
    intent_router.register(Intents.SELECT_SUB_EXPERIENCE, select_sub_experience_handler)