#!/usr/bin/env python3
"""UI layout constants and configuration.

This module provides centralized access to layout constants used throughout
the application, loaded from theme configuration files.
"""


def _load_margins_from_yaml():
    """Load margins from _base.yaml theme configuration.

    Returns:
        dict: Margin values loaded from theme or defaults
    """
    try:
        from nrhof.core.theme_loader import get_theme_loader

        theme_loader = get_theme_loader()
        base_layout = theme_loader.load_layout("_base")
        margins = base_layout.get("margins", {})
        footer = base_layout.get("footer", {})
        return {
            "top": margins.get("top", 50),
            "left": margins.get("left", 50),
            "right": margins.get("right", 50),
            "bottom": margins.get("bottom", 130),
            "footer_height": footer.get("height", 130),
        }
    except Exception:
        # Fallback to defaults if YAML can't be loaded
        return {"top": 50, "left": 50, "right": 50, "bottom": 130, "footer_height": 130}


# Load margins from theme configuration
_margins = _load_margins_from_yaml()

# Screen margin constants
MARGIN_TOP = _margins["top"]
MARGIN_LEFT = _margins["left"]
MARGIN_RIGHT = _margins["right"]
MARGIN_BOTTOM = _margins["bottom"]
FOOTER_HEIGHT = _margins["footer_height"]

__all__ = [
    "MARGIN_TOP",
    "MARGIN_LEFT",
    "MARGIN_RIGHT",
    "MARGIN_BOTTOM",
    "FOOTER_HEIGHT",
]
