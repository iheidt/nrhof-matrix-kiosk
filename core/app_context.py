#!/usr/bin/env python3


class AppContext:
    """Central context object containing all app-level dependencies."""
    
    def __init__(self, config, scene_manager, voice_router, voice_engine, intent_router):
        """Initialize app context with all dependencies.
        
        Args:
            config: Application configuration dict
            scene_manager: SceneManager instance
            voice_router: VoiceRouter instance
            voice_engine: VoiceEngine instance
            intent_router: IntentRouter instance
        """
        self.config = config
        self.scene_manager = scene_manager
        self.voice_router = voice_router
        self.voice_engine = voice_engine
        self.intent_router = intent_router
