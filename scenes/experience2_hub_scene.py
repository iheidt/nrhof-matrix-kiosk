#!/usr/bin/env python3
from scene_manager import BaseHubScene, register_scene
from intent_router import Intents


@register_scene("Experience2HubScene")
class Experience2HubScene(BaseHubScene):
    """Hub menu for Experience 2 sub-experiences."""
    
    def __init__(self, ctx):
        # Initialize with theme-driven content
        super().__init__(
            ctx=ctx,
            content_name='experience2_hub',
            back_intent=Intents.GO_HOME
        )
