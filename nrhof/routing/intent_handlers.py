#!/usr/bin/env python3
"""Intent handlers for application navigation and actions."""

from nrhof.core.app_context import AppContext
from nrhof.routing.intent_router import Intent, IntentRouter


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

    # Media control intents (voice-ready)
    _register_media_control_intents(intent_router)

    # System intents (voice-ready)
    _register_system_intents(intent_router, app_context)


def _register_navigation_intents(intent_router: IntentRouter):
    """Register navigation intents (go home, go back, etc.).

    All handlers use signature: handler(event_bus, **slots)
    """

    def go_home(event_bus, **slots):
        controller = intent_router.get_scene_controller()
        if controller:
            controller.switch_to("MenuScene")

    def go_back(event_bus, **slots):
        controller = intent_router.get_scene_controller()
        if controller:
            controller.go_back()

    def go_to_settings(event_bus, **slots):
        controller = intent_router.get_scene_controller()
        if controller:
            controller.switch_to("SettingsScene")

    def go_to_band_details(event_bus, band_data=None, **slots):
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
    """Register selection intents (menu options, sub-experiences).

    All handlers use signature: handler(event_bus, **slots)
    """

    # Main menu option selection
    def select_option_handler(event_bus, index, **slots):
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
    def select_sub_experience_handler(event_bus, id, **slots):
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


def _register_media_control_intents(intent_router: IntentRouter):
    """Register media control intents (pause, resume, next, volume).

    All handlers use signature: handler(event_bus, **slots)
    These are stubs ready for voice integration.
    """

    def pause(event_bus, **slots):
        """Pause current playback."""
        # TODO: Implement pause via pygame.mixer or external player control
        print("[INTENT] Pause requested (not implemented)")

    def resume(event_bus, **slots):
        """Resume current playback."""
        # TODO: Implement resume via pygame.mixer or external player control
        print("[INTENT] Resume requested (not implemented)")

    def next_track(event_bus, **slots):
        """Skip to next track."""
        # TODO: Implement next track via Spotify/Sonos API
        print("[INTENT] Next track requested (not implemented)")

    def previous_track(event_bus, **slots):
        """Go to previous track."""
        # TODO: Implement previous track via Spotify/Sonos API
        print("[INTENT] Previous track requested (not implemented)")

    def volume_up(event_bus, **slots):
        """Increase volume."""
        # TODO: Implement volume control
        print("[INTENT] Volume up requested (not implemented)")

    def volume_down(event_bus, **slots):
        """Decrease volume."""
        # TODO: Implement volume control
        print("[INTENT] Volume down requested (not implemented)")

    def set_volume(event_bus, level=None, **slots):
        """Set volume to specific level.

        Args:
            level: Volume level (0-100)
        """
        # TODO: Implement volume control
        print(f"[INTENT] Set volume to {level} requested (not implemented)")

    intent_router.register(Intent.PAUSE, pause)
    intent_router.register(Intent.RESUME, resume)
    intent_router.register(Intent.NEXT, next_track)
    intent_router.register(Intent.PREVIOUS, previous_track)
    intent_router.register(Intent.VOLUME_UP, volume_up)
    intent_router.register(Intent.VOLUME_DOWN, volume_down)
    intent_router.register(Intent.SET_VOLUME, set_volume)


def _register_system_intents(intent_router: IntentRouter, app_context: AppContext):
    """Register system intents (language change, etc.).

    All handlers use signature: handler(event_bus, **slots)
    These are stubs ready for voice integration.
    """

    def change_language(event_bus, language=None, **slots):
        """Change application language.

        Args:
            language: Language code (e.g., 'en', 'jp', 'es')
        """
        if language:
            # TODO: Implement language change via localization service
            print(f"[INTENT] Change language to {language} requested (not implemented)")
        else:
            print("[INTENT] Change language requested but no language specified")

    intent_router.register(Intent.CHANGE_LANGUAGE, change_language)
