#!/usr/bin/env python3
import os
from pathlib import Path
from scene_manager import BaseHubScene, register_scene
from intent_router import Intents


@register_scene("VideoListScene")
class VideoListScene(BaseHubScene):
    """List of available videos to play."""
    
    def __init__(self, ctx):
        # Scan for video files in assets/videos/
        video_dir = Path(__file__).parent.parent / "assets" / "videos"
        video_files = []
        
        if video_dir.exists():
            # Find all MP4 files
            for video_file in sorted(video_dir.glob("*.mp4")):
                video_files.append({
                    "label": video_file.stem,  # Filename without extension
                    "id": f"video:{video_file.name}"  # Store full filename
                })
        
        # If no videos found, show placeholder
        if not video_files:
            video_files = [
                {"label": "no videos found", "id": "none"}
            ]
        
        # Initialize with title, items, and back intent
        super().__init__(
            ctx=ctx,
            title="videos",
            items=video_files,
            back_intent=Intents.GO_HOME
        )
