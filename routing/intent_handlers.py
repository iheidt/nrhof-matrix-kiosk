#!/usr/bin/env python3
"""Intent handlers for application navigation and actions."""

from core.app_context import AppContext
from routing.intent_router import Intent, IntentRouter


def register_all_intents(
    intent_router: IntentRouter,
    scene_controller,
    app_context: AppContext,
):
    """Register all application intents.

    Args:
        intent_router: IntentRouter instance
        scene_controller: Scene controller with switch_to() and go_back() methods
        app_context: AppContext instance
    """
    # Inject scene controller into router
    intent_router.set_scene_controller(scene_controller)

    # Navigation intents
    _register_navigation_intents(intent_router)

    # Selection intents
    _register_selection_intents(intent_router, app_context)


def _register_navigation_intents(intent_router: IntentRouter):
    """Register navigation intents (go home, go back, etc.)."""

    def go_home(**kw):
        controller = intent_router.get_scene_controller()
        if controller:
            controller.switch_to("MenuScene")

    def go_back(**kw):
        controller = intent_router.get_scene_controller()
        if controller:
            controller.go_back()

    def go_to_settings(**kw):
        controller = intent_router.get_scene_controller()
        if controller:
            controller.switch_to("SettingsScene")

    def go_to_band_details(band_data=None, **kw):
        controller = intent_router.get_scene_controller()
        if controller:
            # Ensure scene is loaded (triggers lazy loading if needed)
            controller._ensure_loaded("BandDetailsScene")
            # Get the BandDetailsScene instance from scenes dict
            scene = controller.scenes.get("BandDetailsScene")
            if scene and band_data:
                scene.set_band_data(band_data)
            controller.switch_to("BandDetailsScene")

    intent_router.register(Intent.GO_HOME, go_home)
    intent_router.register(Intent.GO_BACK, go_back)
    intent_router.register(Intent.GO_TO_SETTINGS, go_to_settings)
    intent_router.register(Intent.GO_TO_BAND_DETAILS, go_to_band_details)


def _register_selection_intents(
    intent_router: IntentRouter,
    app_context: AppContext,
):
    """Register selection intents (menu options, sub-experiences)."""

    # Main menu option selection
    def select_option_handler(index, **kw):
        controller = intent_router.get_scene_controller()
        if not controller:
            return

        if index == 0:
            # NR-38
            controller.switch_to("NR38Scene")
        elif index == 1:
            # NR-18: Not implemented yet
            print("Placeholder: NR-18 not implemented yet")
        elif index == 2:
            # Visualizer
            controller.switch_to("VisualizersScene")
        elif index == 3:
            # Fate maker: Not implemented yet
            print("Placeholder: Fate maker not implemented yet")
        else:
            print(f"Placeholder: Option {index + 1} not implemented yet")

    intent_router.register(Intent.SELECT_OPTION, select_option_handler)

    # Sub-experience selection
    def select_sub_experience_handler(id, **kw):
        controller = intent_router.get_scene_controller()
        if not controller:
            return

        if id == "spectrum_bars":
            controller.switch_to("Experience1SpectrumBarsScene")
        elif id == "waveform":
            controller.switch_to("Experience1WaveformScene")
        elif id == "lissajous":
            controller.switch_to("Experience1LissajousScene")
        else:
            print(f"Unknown sub-experience: {id}")

    intent_router.register(Intent.SELECT_SUB_EXPERIENCE, select_sub_experience_handler)
