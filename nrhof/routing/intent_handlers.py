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
    _register_media_intents(intent_router, app_context)

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


def _register_media_intents(intent_router: IntentRouter, app_context: AppContext):
    """Register media control intents (pause, play, next, etc.).

    All handlers use signature: handler(event_bus, **slots)
    These handlers control Spotify/Sonos playback via WorkerRegistry.
    """

    def pause(event_bus, **slots):
        """Pause playback."""
        from nrhof.core.worker_registry import get_global_registry

        registry = get_global_registry()
        if not registry:
            print("[INTENT] Pause requested but WorkerRegistry not available")
            return

        # Get current source
        source_manager = registry.get_source_manager()
        if not source_manager:
            print("[INTENT] Pause requested but SourceManager not available")
            return

        current_source = source_manager.get_current_source()
        print(f"[INTENT] Pause requested (current source: {current_source})")

        if current_source == "spotify":
            spotify = registry.get("spotify_source")
            if spotify and hasattr(spotify, "pause_playback"):
                if spotify.pause_playback():
                    print("[INTENT] ✓ Spotify playback paused")
                else:
                    print("[INTENT] ✗ Failed to pause Spotify")
        elif current_source == "sonos":
            print("[INTENT] Sonos pause not yet implemented")
        else:
            print(f"[INTENT] No active playback to pause (source: {current_source})")

    def resume(event_bus, **slots):
        """Resume playback."""
        from nrhof.core.worker_registry import get_global_registry

        registry = get_global_registry()
        if not registry:
            print("[INTENT] Resume requested but WorkerRegistry not available")
            return

        source_manager = registry.get_source_manager()
        if not source_manager:
            print("[INTENT] Resume requested but SourceManager not available")
            return

        current_source = source_manager.get_current_source()
        print(f"[INTENT] Resume requested (current source: {current_source})")

        if current_source == "spotify":
            spotify = registry.get("spotify_source")
            if spotify and hasattr(spotify, "resume_playback"):
                if spotify.resume_playback():
                    print("[INTENT] ✓ Spotify playback resumed")
                else:
                    print("[INTENT] ✗ Failed to resume Spotify")
        elif current_source == "sonos":
            print("[INTENT] Sonos resume not yet implemented")
        else:
            print(f"[INTENT] No active playback to resume (source: {current_source})")

    def next_track(event_bus, **slots):
        """Skip to next track."""
        from nrhof.core.worker_registry import get_global_registry

        registry = get_global_registry()
        if not registry:
            print("[INTENT] Next track requested but WorkerRegistry not available")
            return

        source_manager = registry.get_source_manager()
        if not source_manager:
            print("[INTENT] Next track requested but SourceManager not available")
            return

        current_source = source_manager.get_current_source()
        print(f"[INTENT] Next track requested (current source: {current_source})")

        if current_source == "spotify":
            spotify = registry.get("spotify_source")
            if spotify and hasattr(spotify, "next_track"):
                if spotify.next_track():
                    print("[INTENT] ✓ Skipped to next track")
                else:
                    print("[INTENT] ✗ Failed to skip track")
        elif current_source == "sonos":
            print("[INTENT] Sonos next not yet implemented")
        else:
            print(f"[INTENT] No active playback to skip (source: {current_source})")

    def previous_track(event_bus, **slots):
        """Go to previous track."""
        from nrhof.core.worker_registry import get_global_registry

        registry = get_global_registry()
        if not registry:
            print("[INTENT] Previous track requested but WorkerRegistry not available")
            return

        source_manager = registry.get_source_manager()
        if not source_manager:
            print("[INTENT] Previous track requested but SourceManager not available")
            return

        current_source = source_manager.get_current_source()
        print(f"[INTENT] Previous track requested (current source: {current_source})")

        if current_source == "spotify":
            spotify = registry.get("spotify_source")
            if spotify and hasattr(spotify, "previous_track"):
                if spotify.previous_track():
                    print("[INTENT] ✓ Went to previous track")
                else:
                    print("[INTENT] ✗ Failed to go to previous track")
        elif current_source == "sonos":
            print("[INTENT] Sonos previous not yet implemented")
        else:
            print(f"[INTENT] No active playback to go back (source: {current_source})")

    def restart_track(event_bus, **slots):
        """Restart current track from beginning."""
        from nrhof.core.worker_registry import get_global_registry

        registry = get_global_registry()
        if not registry:
            print("[INTENT] Restart track requested but WorkerRegistry not available")
            return

        source_manager = registry.get_source_manager()
        if not source_manager:
            print("[INTENT] Restart track requested but SourceManager not available")
            return

        current_source = source_manager.get_current_source()
        print(f"[INTENT] Restart track requested (current source: {current_source})")

        if current_source == "spotify":
            spotify = registry.get("spotify_source")
            if spotify and hasattr(spotify, "restart_track"):
                if spotify.restart_track():
                    print("[INTENT] ✓ Restarted track from beginning")
                else:
                    print("[INTENT] ✗ Failed to restart track")
        elif current_source == "sonos":
            print("[INTENT] Sonos restart not yet implemented")
        else:
            print(f"[INTENT] No active playback to restart (source: {current_source})")

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
    intent_router.register(Intent.RESTART_TRACK, restart_track)
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

    def change_mode(event_bus, **slots):
        """Change visual mode (matrix/pink)."""
        # TODO: Implement mode switching (matrix vs pink theme)
        print("[INTENT] Change mode requested (not implemented)")

    def change_voice(event_bus, **slots):
        """Change TTS voice."""
        # TODO: Implement voice switching for TTS
        print("[INTENT] Change voice requested (not implemented)")

    def play_music_video(event_bus, **slots):
        """Play music video for current track."""
        # TODO: Implement music video playback
        print("[INTENT] Play music video requested (not implemented)")

    def stop_video(event_bus, **slots):
        """Stop music video playback."""
        # TODO: Implement video stop
        print("[INTENT] Stop video requested (not implemented)")

    def roll_fate(event_bus, **slots):
        """Roll fate in Fate Maker experience."""
        # TODO: Implement fate rolling in Fate Maker scene
        print("[INTENT] Roll fate requested (not implemented)")

    intent_router.register(Intent.CHANGE_LANGUAGE, change_language)
    intent_router.register(Intent.CHANGE_MODE, change_mode)
    intent_router.register(Intent.CHANGE_VOICE, change_voice)
    intent_router.register(Intent.PLAY_MUSIC_VIDEO, play_music_video)
    intent_router.register(Intent.STOP_VIDEO, stop_video)
    intent_router.register(Intent.ROLL_FATE, roll_fate)
