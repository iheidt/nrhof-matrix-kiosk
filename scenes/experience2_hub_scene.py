#!/usr/bin/env python3
from scene_manager import BaseHubScene, register_scene
from intent_router import Intents


@register_scene("Experience2HubScene")
class Experience2HubScene(BaseHubScene):
    """Hub menu for Experience 2 sub-experiences."""
    
    def __init__(self, ctx):
        # Define sub-experience items
        items = [
            {"label": "1. videos", "id": "video_list"}
        ]
        
        # Initialize with title, items, and back intent
        super().__init__(
            ctx=ctx,
            title="experience 2",
            items=items,
            back_intent=Intents.GO_HOME
        )
