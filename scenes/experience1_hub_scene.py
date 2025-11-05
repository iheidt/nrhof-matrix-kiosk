#!/usr/bin/env python3
from scenes.scene_manager import BaseHubScene, register_scene
from routing.intent_router import Intents


@register_scene("Experience1HubScene")
class Experience1HubScene(BaseHubScene):
    """Hub menu for Experience 1 sub-experiences."""
    
    def __init__(self, ctx):
        # Initialize with theme-driven content
        super().__init__(
            ctx=ctx,
            content_name='experience1_hub',
            back_intent=Intents.GO_HOME
        )
