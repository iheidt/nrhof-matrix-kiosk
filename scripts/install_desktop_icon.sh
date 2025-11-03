#!/usr/bin/env bash
set -e

echo "=== Installing NRHOF Kiosk Desktop Icon ==="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

DESKTOP_FILE="$PROJECT_DIR/nrhof-kiosk.desktop"
DESKTOP_DIR="$HOME/Desktop"
APPLICATIONS_DIR="$HOME/.local/share/applications"

# Create directories if they don't exist
mkdir -p "$DESKTOP_DIR"
mkdir -p "$APPLICATIONS_DIR"

# Copy to applications directory (for app menu)
echo "Installing to applications menu..."
cp "$DESKTOP_FILE" "$APPLICATIONS_DIR/nrhof-kiosk.desktop"
chmod +x "$APPLICATIONS_DIR/nrhof-kiosk.desktop"

# Copy to desktop
echo "Installing to desktop..."
cp "$DESKTOP_FILE" "$DESKTOP_DIR/nrhof-kiosk.desktop"
chmod +x "$DESKTOP_DIR/nrhof-kiosk.desktop"

# Mark as trusted (required for Raspberry Pi OS)
if command -v gio &> /dev/null; then
    echo "Marking desktop icon as trusted..."
    gio set "$DESKTOP_DIR/nrhof-kiosk.desktop" metadata::trusted true 2>/dev/null || true
fi

echo ""
echo "✅ Desktop icon installed!"
echo ""
echo "You should now see:"
echo "  - 'NRHOF Matrix Kiosk' icon on your desktop"
echo "  - 'NRHOF Matrix Kiosk' in your applications menu"
echo ""
echo "Double-click the desktop icon to launch the kiosk."
echo ""
