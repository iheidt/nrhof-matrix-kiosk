# NRHOF Matrix Kiosk (Raspberry Pi 5)

A fullscreen 1280x1024 kiosk app that boots to a Matrix-style intro and then shows a 3-option touchscreen menu. Each option launches a command/app. Icons are SVG placeholders you can replace.

## Features
- Matrix intro
- Terminal-like UI, 3 large touch targets, keyboard 1/2/3 also work
- Loop back to intro when exiting menu
- Systemd unit for boot-to-app kiosk
- Voice command support
- Audio visualization
- Auto-update system

## Quick Start (Development Workflow)

### One-Time Setup
1. **On Mac**: Clone and set up the repo
2. **On Pi**: Run the bootstrap script (see [Pi Deployment Guide](docs/PI_DEPLOY.md))

### Daily Workflow

```bash
# See all available commands
make help

# Deploy changes to Pi (commit + push + update Pi)
make deploy

# Just push to GitHub
make push

# Pull latest code on Pi and restart
make pi-pull
make pi-restart

# View Pi logs
make pi-logs

# Test locally on Mac
make test
```

**Development Rule**: Edit on Mac → Push to GitHub → Pi pulls automatically (or use `make deploy`)

## Requirements
- Raspberry Pi OS (Wayland or X11)
- Python 3.11+
- Packages: `pygame`, `Pillow`, `cairosvg` (optional for SVG). Install:

```bash
sudo apt update
sudo apt install -y python3-pip python3-pygame python3-pil libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0
python3 -m pip install -r requirements.txt
```

> Tip: On Pi, you can often use the distro `python3-pygame` without pip; keep `requirements.txt` for dev machines.

## Run on your Mac for testing
```bash
python3 app.py
```
- Fullscreen toggle is in `config.json` if you prefer windowed while testing.
- Quit with Ctrl+Q.

## Configure menu actions
Edit `config.json`:
```json
{
  "menu": {
    "entries": [
      {"label": "Option 1", "icon": "assets/option1.svg", "command": "chromium-browser --kiosk https://example.com"},
      {"label": "Option 2", "icon": "assets/option2.svg", "command": "/usr/bin/python3 /home/pi/some_app/main.py"},
      {"label": "Option 3", "icon": "assets/option3.svg", "command": "lxterminal -e htop"}
    ]
  }
}
```
- If an icon is missing, a labeled placeholder is drawn.
- SVGs are rasterized at runtime if CairoSVG is available; PNGs/JPGs also work.

## Kiosk at boot with systemd
1. Copy the project to Pi (suggested path `/home/pi/nrhof-matrix-kiosk`).
2. Install deps (see above).
3. Install service:
```bash
sudo cp service/nrhof-matrix-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nrhof-matrix-kiosk.service
sudo systemctl start nrhof-matrix-kiosk.service
```

### Optional: disable screen blanking
```bash
sudo raspi-config  # Interface Options → Screen Blanking → Disable
```
Or add to `/etc/xdg/lxsession/LXDE-pi/autostart`:
```
@xset s off
@xset -dpms
@xset s noblank
```

## Touchscreen notes
- UI is sized for 1280×1024 5:4. It scales to current display but expects similar aspect.
- Press any option (touch/click) to launch; keyboard 1–3 also work.

## Add your SVGs
- Place your icons at `assets/option1.svg`, `assets/option2.svg`, `assets/option3.svg`.
- Any raster image path also works.

## Development
- Main loop: intro `typewriter_screen()` → `menu_screen()`.
- Hold Ctrl+Q to quit.
