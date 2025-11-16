"""LLM to Rhino intent mapping.

Maps LLM high-level intent labels → Rhino's canonical intent names.
These canonical names MUST match those defined in Rhino context and IntentRouter.
"""

LLM_INTENT_MAP = {
    # Music control
    "PAUSE": "pausePlayback",
    "RESUME": "resumePlayback",
    "PLAY": "resumePlayback",
    "STOP": "pausePlayback",
    "NEXT": "nextTrack",
    "SKIP": "nextTrack",
    "PREVIOUS": "previousTrack",
    "BACK": "previousTrack",
    "RESTART": "restartTrack",
    # Volume control
    "VOLUME_UP": "increaseVolume",
    "LOUDER": "increaseVolume",
    "VOLUME_DOWN": "decreaseVolume",
    "QUIETER": "decreaseVolume",
    # Navigation
    "HOME": "goHome",
    "MENU": "goHome",
    "SETTINGS": "goToSettings",
    "CONFIG": "goToSettings",
    "BACK_NAV": "goBack",
    "NR38": "goToNR38",
    "NR18": "goToNR18",
    "VISUALIZERS": "goToVisualizers",
    "FATEMAKER": "goToFateMaker",
    # Video control
    "PLAY_VIDEO": "playMusicVideo",
    "STOP_VIDEO": "stopVideo",
    # System
    "CHANGE_LANGUAGE": "changeLanguage",
    "CHANGE_MODE": "changeMode",
    "CHANGE_VOICE": "changeVoice",
    # Dice roller
    "ROLL": "rollFate",
}
