#!/usr/bin/env python3
import os
from pathlib import Path
from scenes.scene_manager import BaseHubScene, register_scene
from routing.intent_router import Intents


@register_scene("VideoListScene")
class VideoListScene(BaseHubScene):
    """List of available videos to play."""
    
    def __init__(self, ctx):
        # Scan for video files in assets/videos/
        video_dir = Path(__file__).parent.parent / "assets" / "videos"
        video_files = []
        
        if video_dir.exists():
            # Find all MP4 files
            for i, video_file in enumerate(sorted(video_dir.glob("*.mp4")), 1):
                video_files.append({
                    "label": f"{i}. {video_file.stem}",  # Numbered list
                    "id": f"video:{video_file.name}"  # Store full filename
                })
        
        # If no videos found, show placeholder
        if not video_files:
            video_files = [
                {"label": "no videos found", "id": "none"}
            ]
        
        # Load theme for styling but use dynamic items
        from core.theme_loader import get_theme_loader
        theme_loader = get_theme_loader()
        theme = theme_loader.load_theme('video_list', theme_name='pipboy')
        
        # Initialize with theme content but override items with scanned videos
        super().__init__(
            ctx=ctx,
            content_name='video_list',
            back_intent=Intents.GO_HOME
        )
        
        # Override items with dynamically scanned videos
        self.items = video_files
