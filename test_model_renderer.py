#!/usr/bin/env python3
import sys

sys.path.insert(0, ".")

import numpy as np
from PIL import Image

from renderers.model_renderer import ModelRenderer

print("=== Model Renderer Test ===")

# Initialize renderer
renderer = ModelRenderer(width=512, height=512)
print("✓ Renderer initialized")

# Load D20 model
if renderer.load_model("assets/models/d20.glb"):
    print("✓ Model loaded")

    # Apply cyberpunk pink
    renderer.set_material_color("#e91e63")
    print("✓ Color applied")

    # Add emission glow
    renderer.set_emission_strength(2.0, "#e91e63")
    print("✓ Emission applied")

    # Optional: rotate it
    renderer.set_rotation(h=45, p=15, r=0)
    print("✓ Rotation set")

    # Render
    pixels = renderer.render_frame()

    if pixels:
        print("✓ Rendered successfully!")

        # Save to PNG
        arr = np.frombuffer(pixels, dtype=np.uint8).reshape((512, 512, 4))
        img = Image.fromarray(arr, "RGBA")
        img.save("/tmp/model_render.png")
        print("✓ Saved to /tmp/model_render.png")
        print("\nView with: open /tmp/model_render.png")
    else:
        print("✗ Rendering failed")

    renderer.cleanup()
else:
    print("✗ Failed to load model")
