"""
setup.py for creating macOS .app bundle of NRHOF app.

Usage:
    python setup.py py2app
"""
from setuptools import setup

APP = ["nrhof_launcher.py"]

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icons/icon.icns",
    "plist": {
        "CFBundleName": "NRHOF",
        "CFBundleDisplayName": "NRHOF",
        "CFBundleIdentifier": "com.nrhof.robot",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSUIElement": False,  # Show in Dock
    },
    "packages": ["xml"],  # Include stdlib xml package
    "includes": [
        "nrhof.integrations.upddapi",
        "xml.sax",
        "xml.sax.saxutils",
        "xml.etree.ElementTree",
    ],
    "excludes": [
        "matplotlib",
        "tkinter",
        "test",
        "unittest",
    ],
    "alias": True,  # Alias mode - symlinks to source for development
    "no_strip": True,  # Don't strip symbols
    "resources": [
        "assets",
        "config",
        "content",
        "layouts",
        "styles",
    ],
}

setup(
    name="NRHOF",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
