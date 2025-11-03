#!/usr/bin/env python3
from scene_manager import BaseHubScene, register_scene
from intent_router import Intents


@register_scene("Experience1HubScene")
class Experience1HubScene(BaseHubScene):
    """Hub menu for Experience 1 sub-experiences."""
    
    def __init__(self, ctx):
        # Define sub-experience items
        items = [
            {"label": "1. spectrum bars", "id": "spectrum_bars"},
            {"label": "2. waveform", "id": "waveform"},
            {"label": "3. lissajous", "id": "lissajous"}
        ]
        
        # Initialize with title, items, and back intent
        super().__init__(
            ctx=ctx,
            title="experience 1",
            items=items,
            back_intent=Intents.GO_HOME
        )
