#!/usr/bin/env python3
"""Launcher script for NRHOF macOS app bundle."""

import os
import site
import sys

# Attempt to set app icon early
# NOTE: This doesn't fully work because the running process is python3.12,
# so macOS shows Python's icon while app runs. The bundle icon shows when closed.
# To fix this would require a native launcher binary instead of shell script.
if sys.platform == "darwin":
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSBundle

        app = NSApplication.sharedApplication()
        bundle = NSBundle.mainBundle()

        if bundle:
            icon_path = bundle.pathForResource_ofType_("icon", "icns")
            if icon_path:
                icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
                if icon:
                    app.setApplicationIconImage_(icon)
    except Exception:
        pass  # Icon setting is not critical

# Ensure we're in the correct directory (app bundle Resources)
if getattr(sys, "frozen", False):
    # Running as bundled app
    bundle_dir = os.path.dirname(sys.executable)
    resources_dir = os.path.join(bundle_dir, "..", "Resources")
    os.chdir(resources_dir)
else:
    # Running from source - activate venv if present
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Try to find and activate venv
    venv_path = os.path.join(script_dir, ".venv312")
    if os.path.exists(venv_path):
        site_packages = os.path.join(venv_path, "lib", "python3.12", "site-packages")
        if os.path.exists(site_packages):
            site.addsitedir(site_packages)

# Import and run main
from nrhof.__main__ import main

if __name__ == "__main__":
    main()
