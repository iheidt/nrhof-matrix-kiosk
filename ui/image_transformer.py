#!/usr/bin/env python3
"""
Image transformation utilities for creating matrix-style effects.
"""

import random
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pygame
import requests
from PIL import Image, ImageDraw, ImageFont


# Helper functions
def hex_rgb(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def posterize01(x: np.ndarray, stops=(0.0, 0.18, 0.38, 0.58, 0.75, 0.90, 1.0)):
    """Snap each value to nearest stop for crisp contrast (brighter bias)."""
    x = np.clip(x, 0.0, 1.0)
    stops_arr = np.array(stops, dtype=np.float32)
    idx = np.abs(x[..., None] - stops_arr).argmin(axis=-1)
    return stops_arr[idx]


# Default colors (glowing pink style) - can be overridden with theme colors
DEFAULT_BRIGHT = (255, 128, 171)  # Bright glowing pink (#FF80AB)
DEFAULT_DIM = (236, 64, 122)  # Mid-tone pink (#EC407A) for contrast
DEFAULT_BG = (196, 243, 255)  # Very dark background

# Katakana glyphs ordered light → dark → empty
GLYPHS = ["･", "ﾂ", "ﾈ", "ｿ", "ﾘ", "ﾒ", "ﾓ", "ﾛ", "ﾛ", " "]  # light → dark → empty

# Per-image contrast stretch using percentiles
CONTRAST_PCT_LOW = 1.0  # percentile for black point
CONTRAST_PCT_HIGH = 99.0  # percentile for white point
GAMMA_MID = 1.30  # midtone bias
HIGHLIGHT_PUSH = 1.55  # extra boost for brights
BLOOM_THRESHOLD = 0.99  # portion of normalized luma considered "hot"
BLOOM_BLUR_PX = 3  # Gaussian sigma for bloom blur (in glyph pixels)
BLOOM_STRENGTH = 0.05  # how strong the bloom layer screens back

# Flicker disabled - parameters removed

# Adaptive background suppression
K_BG = 3  # KMeans clusters
SAMPLE_PX = 20000  # pixels to sample for KMeans
VAR_PCT = 35.0  # percentile of Sobel magnitude under which we consider "low detail"
DIST_PCT = 85.0  # percentile of LAB distance inside chosen cluster -> mask width
BG_CRUSH = 0.95  # how much luminance to remove in background mask
SKIP_LUMA = 0.08  # skip drawing if cell luma below this
HILITE_99 = 99.00  # re-normalize highlights to hit primary
PRIMARY_RGB = hex_rgb("#e91e63")
DIM_RGB = hex_rgb("#080610")


def srgb_to_luma(r, g, b):
    """Convert RGB to perceptual luminance (0..1)."""
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def percentile_stretch(luma_arr: np.ndarray, p_low=CONTRAST_PCT_LOW, p_high=CONTRAST_PCT_HIGH):
    """Per-image contrast stretch using percentiles."""
    lo = np.percentile(luma_arr, p_low)
    hi = np.percentile(luma_arr, p_high)
    if hi <= lo:
        hi = lo + 1e-6
    L = (luma_arr - lo) / (hi - lo)
    return np.clip(L, 0.0, 1.0)


def clahe_luma(luma_arr: np.ndarray):
    """Local contrast with CLAHE on 8-bit luma, return [0..1] float."""
    cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    # Ensure 2D array and convert to uint8
    if luma_arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {luma_arr.shape}")
    y8 = np.clip(luma_arr * 255.0, 0, 255).astype(np.uint8)
    # Ensure contiguous array for OpenCV
    y8 = np.ascontiguousarray(y8)
    y8 = cl.apply(y8)
    return y8.astype(np.float32) / 255.0


def unsharp_mask_rgb(arr: np.ndarray, radius_px=1.0, amount=0.6):
    """Mild unsharp on RGB array to rescue edges before ASCII mapping."""
    # OpenCV expects BGR
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    blur = cv2.GaussianBlur(bgr, (0, 0), radius_px)
    sharp = cv2.addWeighted(bgr, 1 + amount, blur, -amount, 0)
    return cv2.cvtColor(sharp, cv2.COLOR_BGR2RGB)


def tone_curve(L: np.ndarray, gamma_mid=GAMMA_MID, highlight_push=HIGHLIGHT_PUSH):
    """
    Piecewise curve:
      - crush shadows (<0.1)
      - keep mid bias via gamma
      - push highlights strongly
    Input/Output in [0,1]
    """
    Lc = L.copy()
    # crush tiny blacks
    shadow = 0.10
    Lc = np.maximum(0.0, (Lc - shadow)) / (1.0 - shadow)
    # mid gamma
    Lc = 1.0 - (1.0 - Lc) ** (1.0 / gamma_mid)
    # highlight push
    hi_mask = (Lc > 0.85).astype(np.float32)
    Lc = np.clip(Lc * (1.0 + hi_mask * (highlight_push - 1.0)), 0.0, 1.0)
    return Lc


def screen_blend(a: np.ndarray, b: np.ndarray, strength=1.0):
    """Screen blend two uint8 RGB images, with strength [0..1]."""
    a_f = a.astype(np.float32) / 255.0
    b_f = (b.astype(np.float32) / 255.0) * strength
    out = 1.0 - (1.0 - a_f) * (1.0 - b_f)
    return np.clip(out * 255.0, 0, 255).astype(np.uint8)


def estimate_background_mask_rgb(arr_rgb: np.ndarray, cell: int, gh: int, gw: int):
    """
    Returns (bg_mask_cells, sobel_cells) where:
      - bg_mask_cells in [0..1] is a soft mask of "likely background" per grid cell
      - sobel_cells is the mean Sobel magnitude per cell (for debugging/tuning)
    """
    # --- compute Sobel on a downscaled luminance for speed
    small = cv2.resize(arr_rgb, (gw, gh), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    sobel = np.hypot(sx, sy)
    sobel_norm = sobel / (sobel.max() + 1e-6)

    # "Low detail" threshold (percentile)
    sobel_thresh = np.percentile(sobel_norm, VAR_PCT)
    low_detail = (sobel_norm <= sobel_thresh).astype(np.float32)  # gh x gw

    # --- sample pixels and cluster in LAB
    h, w, _ = arr_rgb.shape
    lab = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)

    # random sample (cap at SAMPLE_PX)
    n = lab.shape[0]
    idx = np.random.choice(n, size=min(SAMPLE_PX, n), replace=False)
    sample = lab[idx]

    # KMeans
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0)
    _ret, labels, centers = cv2.kmeans(sample, K_BG, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    centers = centers.astype(np.float32)

    # Assign all pixels to nearest center to compute cluster sizes
    # (use the downscaled grid to stay fast and consistent with sobel)
    lab_small = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab_small[..., 0]  # (gh, gw) - no extra dimension
    A = lab_small[..., 1]  # (gh, gw)
    B = lab_small[..., 2]  # (gh, gw)
    # distance to each center
    dists = []
    for c in centers:
        d = np.sqrt((L - c[0]) ** 2 + (A - c[1]) ** 2 + (B - c[2]) ** 2)
        dists.append(d)
    dists = np.stack(dists, axis=-1)  # gh x gw x K
    lab_labels_small = np.argmin(dists, axis=-1)  # gh x gw

    # Choose the cluster that is both large and low-detail
    bg_score = []
    for k in range(centers.shape[0]):
        mask_k = (lab_labels_small == k).astype(np.float32)
        frac = mask_k.mean()
        lowd = (mask_k * low_detail).sum() / (mask_k.sum() + 1e-6)
        # weight size and low-detail; tweak weights as needed
        bg_score.append(0.6 * frac + 0.4 * lowd)
    bg_idx = int(np.argmax(bg_score))
    bg_center = centers[bg_idx]

    # LAB distance to bg center
    d_bg = np.sqrt((L - bg_center[0]) ** 2 + (A - bg_center[1]) ** 2 + (B - bg_center[2]) ** 2)
    # per-image distance width from in-cluster pixels
    in_bg = lab_labels_small == bg_idx
    if in_bg.any():
        dist_width = np.percentile(d_bg[in_bg], DIST_PCT)
    else:
        dist_width = np.percentile(d_bg, 50.0)

    # soft mask by distance AND low detail
    soft_color = smoothstep(1.0 - (d_bg / (dist_width + 1e-6)))
    soft_detail = smoothstep(1.0 - (sobel_norm / (sobel_thresh + 1e-6)))
    bg_mask = np.clip(soft_color * soft_detail, 0.0, 1.0)  # gh x gw (float32)

    return bg_mask.astype(np.float32), sobel_norm.astype(np.float32)


def lum_to_index(luma, n=None):
    """Map luma [0,1] to glyph index 0..N-1.

    Luma is already processed through percentile stretch, CLAHE, and tone curve,
    so we just map directly to glyph index.
    """
    if n is None:
        n = len(GLYPHS)
    return int(np.clip(luma * n, 0, n - 1))


# Flicker functions removed - no longer used


def transform_to_matrix(
    src_path: Path | str,
    cell: int = 16,
    font_name: str = "NotoSansJP-Regular.ttf",
    enable_flicker: bool = False,  # Kept for compatibility but unused
    color_bright: tuple = None,
    color_dim: tuple = None,
    color_bg: tuple = None,
) -> pygame.Surface | None:
    """Transform an image into a matrix-style ASCII mosaic using katakana glyphs.

    Args:
        src_path: Path to source image or URL
        cell: Size of each character cell in pixels (default: 16)
        font_name: Font file name for rendering characters
        enable_flicker: Kept for compatibility but unused (flicker disabled)
        color_bright: RGB tuple for bright glyphs
        color_dim: RGB tuple for dim glyphs
        color_bg: RGB tuple for background

    Returns:
        pygame.Surface with the matrix-transformed image, or None if transformation failed
    """
    try:
        # Use provided colors or defaults
        bright = color_bright if color_bright else DEFAULT_BRIGHT
        bg = color_bg if color_bg else DEFAULT_BG

        # Use global constants for tuning
        _bg_crush = BG_CRUSH
        _skip_luma = SKIP_LUMA
        _bloom_threshold = BLOOM_THRESHOLD
        _bloom_strength = BLOOM_STRENGTH
        _gamma_mid = GAMMA_MID
        _highlight_push = HIGHLIGHT_PUSH
        _mid_t = 0.33
        _high_t = 0.88
        _edge_gain = 0.45
        _bg_mode_pct = 62.0

        # Load image from URL or file path
        if isinstance(src_path, str) and (
            src_path.startswith("http://") or src_path.startswith("https://")
        ):
            # Download image from URL
            response = requests.get(src_path, timeout=10)
            response.raise_for_status()
            im = Image.open(BytesIO(response.content)).convert("RGB")
        else:
            # Load from file path
            im = Image.open(src_path).convert("RGB")
        w, h = im.size
        gw, gh = w // cell, h // cell

        # Mild edge sharpen BEFORE sampling to preserve structure
        arr = unsharp_mask_rgb(np.array(im), radius_px=0.8, amount=0.5)
        arr = arr[: gh * cell, : gw * cell]

        # Estimate background mask
        bg_mask_cells, sobel_cells = estimate_background_mask_rgb(arr, cell, gh, gw)

        # Dilate mask to clean up halos around silhouettes
        mask_u8 = (bg_mask_cells * 255).astype(np.uint8)
        mask_u8 = cv2.dilate(mask_u8, np.ones((3, 3), np.uint8), iterations=1)
        bg_mask_cells = mask_u8.astype(np.float32) / 255.0

        # Average RGB per cell
        blocks_rgb = arr.reshape(gh, cell, gw, cell, 3).mean(axis=(1, 3)).astype(np.float32)

        # Convert to luma [0..1]
        R = blocks_rgb[:, :, 0]
        G = blocks_rgb[:, :, 1]
        B = blocks_rgb[:, :, 2]
        blocks_luma = (0.299 * R + 0.587 * G + 0.114 * B) / 255.0

        # Global stretch
        L = percentile_stretch(blocks_luma)

        # Adaptive background crush
        L = L * (1.0 - _bg_crush * bg_mask_cells)

        # Local contrast + tone
        L = clahe_luma(L)
        L = tone_curve(L, gamma_mid=_gamma_mid, highlight_push=_highlight_push)

        # --- background mode subtraction (removes the dominant flat field)
        # Estimate mode-ish level by percentile (robust to outliers)
        bg_mode = np.percentile(L, _bg_mode_pct)

        # Soft-knee subtract so anything near bg_mode collapses toward 0
        eps = 1e-6
        L = np.clip((L - (bg_mode + 0.02)) / (1.0 - (bg_mode + 0.02) + eps), 0.0, 1.0)
        # Extra knee to kill lingering mids near the background level
        L = L * L

        # --- edge/silhouette boost (make edges darker -> more readable forms)
        # 'sobel_cells' is returned from estimate_background_mask_rgb; normalize it
        edge = sobel_cells / (sobel_cells.max() + 1e-6)
        edge *= 1.0 - bg_mask_cells  # don't darken the background field
        L = np.clip(L - _edge_gain * edge, 0.0, 1.0)

        # Normalize top end so we can hit primary
        top = np.percentile(L, HILITE_99)
        if top > 1e-6:
            L = np.clip(L / top, 0.0, 1.0)

        # Posterize to slam contrast and keep silhouettes crisp
        L = posterize01(L)

        # Global brightness lift for active areas (non-background)
        L = L + 0.12 * (1.0 - bg_mask_cells)
        L = np.clip(L, 0.0, 1.0)

        # Create output image with dark background
        out = Image.new("RGB", (gw * cell, gh * cell), bg)

        # Add desaturated, pink-tinted background layer
        # Resize original image to match output size
        bg_img = im.resize((gw * cell, gh * cell), Image.LANCZOS)
        bg_arr = np.array(bg_img).astype(np.float32)

        # Desaturate (convert to grayscale then back to RGB)
        gray = 0.299 * bg_arr[:, :, 0] + 0.587 * bg_arr[:, :, 1] + 0.114 * bg_arr[:, :, 2]
        bg_desat = np.stack([gray] * 3, axis=-1)

        # Tint with primary color (pink)
        primary_arr = np.array(bright, dtype=np.float32)
        bg_tinted = bg_desat * (primary_arr / 255.0)

        # Apply transparency (30% opacity) and blend with dark background
        out_arr = np.array(out).astype(np.float32)
        out_arr = out_arr * 0.7 + bg_tinted * 0.3
        out = Image.fromarray(out_arr.astype(np.uint8))

        # Add backlit glow layer for foreground areas (more diffuse)
        # Downsample luminance for smoother glow
        glow_layer = np.zeros((gh, gw), dtype=np.float32)
        for y in range(gh):
            for x in range(gw):
                if bg_mask_cells[y, x] < 0.5:  # foreground area
                    glow_layer[y, x] = L[y, x]

        # Resize to full resolution with interpolation for smooth gradients
        glow_full = cv2.resize(glow_layer, (gw * cell, gh * cell), interpolation=cv2.INTER_LINEAR)

        # Apply strong blur for soft backlit effect
        glow_full = cv2.GaussianBlur(glow_full, (0, 0), cell * 1.8)

        # Convert to RGB with bright white glow
        glow_rgb = np.stack([glow_full * 255] * 3, axis=-1).astype(np.uint8)

        # Blend glow with background (stronger for more punch)
        out_arr = np.array(out)
        out_arr = np.clip(
            out_arr.astype(np.float32) + glow_rgb.astype(np.float32) * 0.6, 0, 255
        ).astype(np.uint8)
        out = Image.fromarray(out_arr)

        draw = ImageDraw.Draw(out)

        # Load fonts (normal and larger sizes for margins)
        project_root = Path(__file__).parent.parent
        font_path = project_root / "assets" / "fonts" / font_name
        try:
            font = ImageFont.truetype(str(font_path), cell)
            font_large = ImageFont.truetype(str(font_path), int(cell * 1.5))
        except Exception:
            font = ImageFont.load_default()
            font_large = font

        # Random number generator for large glyph placement
        rng = random.Random(42)

        # Draw glyphs
        for y in range(gh):
            for x in range(gw):
                luma = float(L[y, x])

                # Skip drawing in dead background
                if luma < _skip_luma:
                    continue  # draw nothing (pure background)

                # Glyph selection with aggressive banding:
                # force darkest/lightest glyphs at thresholds for banding
                if luma < _mid_t:
                    # force darkest glyph/color for deep shadows
                    ch = GLYPHS[-2]  # "0" (darkest visible glyph)
                    fill = (int(DIM_RGB[0] * 0.22), int(DIM_RGB[1] * 0.22), int(DIM_RGB[2] * 0.22))
                elif luma > _high_t:
                    # bright hits primary and lightest visible glyph
                    ch = GLYPHS[0]  # lightest visible glyph (not space)
                    fill = PRIMARY_RGB
                else:
                    # mid band: normal mapping but steeper ramp
                    idx = lum_to_index(luma)
                    ch = GLYPHS[idx]
                    tcol = luma * luma * (3 - 2 * luma)  # smoothstep
                    # Brighten interpolation for backlit effect
                    tcol = min(1.0, tcol * 1.3)  # boost by 30%
                    r = int(DIM_RGB[0] + (PRIMARY_RGB[0] - DIM_RGB[0]) * tcol)
                    g = int(DIM_RGB[1] + (PRIMARY_RGB[1] - DIM_RGB[1]) * tcol)
                    b = int(DIM_RGB[2] + (PRIMARY_RGB[2] - DIM_RGB[2]) * tcol)
                    fill = (r, g, b)

                # Check if in dense area (high luminance + foreground)
                # Only place large kana where there are already lots of bright glyphs
                in_dense_area = (bg_mask_cells[y, x] < 0.3) and (
                    luma > 0.65
                )  # Bright foreground areas only

                # Randomly enlarge glyphs in dense bright areas with full primary color
                if in_dense_area and rng.random() < 0.12:  # 12% chance in dense areas
                    # Use larger font
                    draw.text((x * cell, y * cell), ch, fill=PRIMARY_RGB, font=font_large)
                else:
                    # Normal sized glyph
                    draw.text((x * cell, y * cell), ch, fill=fill, font=font)

        # Add highlight bloom for neon glow
        base = np.array(out)
        hot = ((L >= _bloom_threshold) & (bg_mask_cells < 0.5)).astype(np.float32)

        if hot.any():
            bloom = Image.new("RGB", (gw * cell, gh * cell), (0, 0, 0))
            bdraw = ImageDraw.Draw(bloom)
            for yy in range(gh):
                for xx in range(gw):
                    if hot[yy, xx] > 0:
                        # use lightest glyph for the bloom pass
                        bdraw.text(
                            (xx * cell, yy * cell), GLYPHS[0], fill=(255, 255, 255), font=font
                        )

            bloom_np = np.array(bloom)
            bloom_np = cv2.GaussianBlur(bloom_np, (0, 0), BLOOM_BLUR_PX)

            # tint bloom to bright color, then screen-blend
            tint = np.array(bright, dtype=np.float32)
            bloom_np = np.clip((bloom_np.astype(np.float32) / 255.0) * tint, 0, 255).astype(
                np.uint8
            )

            comp = screen_blend(base, bloom_np, strength=_bloom_strength)
        else:
            comp = base

        out = Image.fromarray(comp)

        # Add large glyph overlay for texture and boundary definition
        overlay = Image.new("RGBA", (gw * cell, gh * cell), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Use larger cell size for overlay glyphs (3x bigger)
        large_cell = cell * 3
        try:
            large_font = ImageFont.truetype(str(font_path), large_cell)
        except Exception:
            large_font = ImageFont.load_default()

        # Sample every 3rd cell for large glyph placement
        for y in range(0, gh, 3):
            for x in range(0, gw, 3):
                # Sample luminance from center of 3x3 block
                if y + 1 < gh and x + 1 < gw:
                    l_sample = float(L[y + 1, x + 1])
                else:
                    l_sample = float(L[y, x])

                # Only draw overlay glyphs in active areas
                if l_sample > _skip_luma:
                    # Pick glyph based on luminance
                    idx = lum_to_index(l_sample, len(GLYPHS))
                    ch = GLYPHS[idx]

                    # Bright color with transparency based on luminance
                    alpha = int(l_sample * 180)  # 0-180 alpha
                    # Use bright primary color
                    fill = (PRIMARY_RGB[0], PRIMARY_RGB[1], PRIMARY_RGB[2], alpha)

                    overlay_draw.text((x * cell, y * cell), ch, fill=fill, font=large_font)

        # Blend overlay onto base image
        out_rgba = out.convert("RGBA")
        out_rgba = Image.alpha_composite(out_rgba, overlay)
        out = out_rgba.convert("RGB")

        # Resize back to original dimensions using nearest neighbor
        out = out.resize((w, h), Image.NEAREST)

        # Convert PIL image to pygame surface
        mode = out.mode
        size = out.size
        data = out.tobytes()
        return pygame.image.fromstring(data, size, mode)

    except Exception as e:
        print(f"Error transforming image to matrix style: {e}")
        return None
