#!/usr/bin/env python3
"""
Real-time 3D model renderer using Panda3D.
Supports GLB/GLTF models with PBR-style materials, emission/glow, and rotation.
"""

import os
from typing import Optional
import numpy as np
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    loadPrcFileData, GraphicsOutput, Texture, WindowProperties,
    FrameBufferProperties, GraphicsPipe,
    LColor, AmbientLight, DirectionalLight, Spotlight
)

class ModelRenderer:
    """
    Real-time 3D model renderer.
    Renders GLB/GLTF models with color and emission effects.
    """
    
    def __init__(self, width: int = 512, height: int = 512):
        """
        Initialize model renderer.
        
        Args:
            width: Render width in pixels
            height: Render height in pixels
        """
        self.width = width
        self.height = height
        
        # Configure Panda3D for offscreen rendering
        loadPrcFileData('', f'win-size {width} {height}')
        loadPrcFileData('', 'window-type offscreen')
        loadPrcFileData('', 'framebuffer-hardware true')
        loadPrcFileData('', 'framebuffer-software false')
        loadPrcFileData('', 'sync-video false')
        loadPrcFileData('', 'show-frame-rate-meter false')
        loadPrcFileData('', 'notify-level error')
        
        # Initialize ShowBase
        self.app = ShowBase()
        
        # Set up offscreen buffer
        self._setup_offscreen_buffer()
        
        # Set up camera
        self._setup_camera()
        
        # Set up lighting
        self._setup_lighting()
        
        # Model reference
        self.model = None
        self.base_color = (1.0, 1.0, 1.0)
        self.rotation = 0.0
        self.spotlight_np = None  # Store spotlight reference
        
    def _setup_offscreen_buffer(self):
        """Create offscreen buffer for rendering to texture."""
        fb_props = FrameBufferProperties()
        fb_props.setRgbColor(True)
        fb_props.setRgbaBits(8, 8, 8, 8)
        fb_props.setDepthBits(24)
        
        win_props = WindowProperties.size(self.width, self.height)
        
        self.buffer = self.app.graphicsEngine.makeOutput(
            self.app.pipe,
            'offscreen_buffer',
            -100,
            fb_props,
            win_props,
            GraphicsPipe.BFRefuseWindow
        )
        
        self.texture = Texture()
        self.buffer.addRenderTexture(self.texture, GraphicsOutput.RTMCopyRam)
        self.display_region = self.buffer.makeDisplayRegion()
        self.display_region.setCamera(self.app.cam)
        
    def _setup_camera(self):
        """Position camera to view model."""
        self.app.cam.setPos(0, -4, 0)
        self.app.cam.lookAt(0, 0, 0)
        
    def _setup_lighting(self):
        """Set up scene lighting matching online sandbox (3 directional lights + ambient)."""
        # High ambient light (environment brightness = 1, intensity = 3)
        ambient = AmbientLight('ambient')
        ambient.setColor(LColor(2.0, 2.0, 2.0, 1))  # Bright ambient for visibility
        ambient_np = self.app.render.attachNewNode(ambient)
        self.app.render.setLight(ambient_np)
        
        # Directional Light 1 - Main key light from top-right
        dir1 = DirectionalLight('dir1')
        dir1.setColor(LColor(1.5, 1.5, 1.5, 1))
        dir1.setShadowCaster(True, 512, 512)  # Enable shadows
        dir1_np = self.app.render.attachNewNode(dir1)
        dir1_np.setHpr(45, -45, 0)  # Top-right
        self.app.render.setLight(dir1_np)
        
        # Directional Light 2 - Fill light from left
        dir2 = DirectionalLight('dir2')
        dir2.setColor(LColor(0.8, 0.8, 0.8, 1))
        dir2_np = self.app.render.attachNewNode(dir2)
        dir2_np.setHpr(-90, -30, 0)  # Left side
        self.app.render.setLight(dir2_np)
        
        # Directional Light 3 - Rim light from back
        dir3 = DirectionalLight('dir3')
        dir3.setColor(LColor(0.6, 0.6, 0.6, 1))
        dir3_np = self.app.render.attachNewNode(dir3)
        dir3_np.setHpr(180, -20, 0)  # Back
        self.app.render.setLight(dir3_np)
        
        # Store main light for color updates (use dir1 as spotlight equivalent)
        self.spotlight_np = dir1_np
        self.spotlight = dir1
        
    def load_model(self, path: str) -> bool:
        """Load a 3D model from file.
        
        Args:
            path: Path to model file (GLB, GLTF, BAM, EGG, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(path):
                print(f"Error: Model not found: {path}")
                return False
            
            # Debug: Show file info
            import time
            file_size = os.path.getsize(path)
            file_mtime = os.path.getmtime(path)
            file_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_mtime))
            print(f"Loading model: {path}")
            print(f"  Size: {file_size:,} bytes")
            print(f"  Modified: {file_time_str}")
            
            # Clear model cache to ensure fresh load
            from panda3d.core import ModelPool
            ModelPool.releaseAllModels()
            
            # Load model using Panda3D's loader
            self.model = self.app.loader.loadModel(path)
            
            if self.model:
                self.model.removeNode()
            
            self.model = self.app.loader.loadModel(path)
            if not self.model:
                return False
            
            self.model.reparentTo(self.app.render)
            
            # Apply PBR-like material settings (matching sandbox: metalness 0.24, glossiness 0.45)
            # Use color scale to simulate metalness and glossiness
            self.model.setColorScale(8.0, 8.0, 8.0, 1.0)  # Moderate brightness for PBR look
            self.model.setColor(1.0, 1.0, 1.0, 1.0)  # Neutral base
            
            # Enable shader for better material response
            from panda3d.core import ShaderAttrib
            self.model.setShaderAuto()
            
            # Center and scale to fill frame
            bounds = self.model.getTightBounds()
            if bounds:
                center = (bounds[0] + bounds[1]) / 2
                self.model.setPos(-center)
                size = (bounds[1] - bounds[0]).length()
                if size > 0:
                    # Scale larger to fill more of the frame
                    self.model.setScale(2.5 / size)
            
            print(f"✓ Model loaded: {path}")
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def set_material_color(self, hex_color: str):
        """Set base color."""
        if not self.model:
            return
        
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        
        self.base_color = (r, g, b)
        self.model.setColor(r, g, b, 1.0)
    
    def set_emission_strength(self, strength: float, hex_color: Optional[str] = None):
        """Set emission/glow strength."""
        if not self.model:
            return
        
        if hex_color:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
        else:
            r, g, b = self.base_color
        
        self.model.setColor(
            min(r * (1.0 + strength), 2.0),
            min(g * (1.0 + strength), 2.0),
            min(b * (1.0 + strength), 2.0),
            1.0
        )
    
    def set_spotlight_color(self, hex_color: str):
        """Set spotlight color."""
        if not hasattr(self, 'spotlight'):
            return
        
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        
        self.spotlight.setColor(LColor(r, g, b, 1))
    
    def set_rotation(self, h: float = 0, p: float = 0, r: float = 0):
        """Set model rotation (heading, pitch, roll in degrees)."""
        if self.model:
            self.model.setHpr(h, p, r)
    
    def render_frame(self) -> Optional[bytes]:
        """Render current frame to pixel buffer."""
        try:
            self.app.graphicsEngine.renderFrame()
            
            if self.texture.mightHaveRamImage():
                data = self.texture.getRamImageAs('RGBA')
                arr = np.frombuffer(data, dtype=np.uint8)
                arr = arr.reshape((self.height, self.width, 4))
                arr = np.flipud(arr)
                return arr.tobytes()
            
            return None
            
        except Exception as e:
            print(f"Error rendering: {e}")
            return None
    
    def cleanup(self):
        """Clean up resources."""
        if self.model:
            self.model.removeNode()
        if hasattr(self, 'app'):
            self.app.destroy()