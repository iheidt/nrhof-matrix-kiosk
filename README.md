# NRHOF Matrix Kiosk

A fullscreen 1280x1024 kiosk app with Matrix-style intro, touchscreen menu, voice commands, and audio visualizations. Runs on Mac Mini (primary) or Raspberry Pi.

## Features
- **Matrix intro** - Typewriter effect with terminal aesthetic
- **Voice commands** - Natural language control via OpenAI
- **Audio visualizations** - Spectrum bars, waveform, Lissajous curves
- **Music videos** - Fullscreen video playback
- **Renderer abstraction** - Ready for Metal/Swift GPU acceleration
- **Dual deployment** - Mac Mini (primary) or Raspberry Pi
- **Touch & keyboard** - Large touch targets, keyboard shortcuts (1/2/3)

## Quick Start

### Mac Mini Setup (Primary Platform)

```bash
# Clone and setup
git clone <repo-url>
cd nrhof-matrix-kiosk
python3 -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt

# Test locally
make test                    # Windowed mode
make test-full               # Fullscreen on secondary display

# Install for kiosk use (manual start/stop)
make mac-install

# Start/stop kiosk
make mac-start               # Start fullscreen on secondary display
make mac-stop                # Stop and return to normal use
make mac-logs                # View logs
```

### Raspberry Pi Setup (Optional)

See [Pi Deployment Guide](docs/PI_DEPLOY.md) for Pi-specific setup.

```bash
# Deploy to Pi
make deploy                  # Push to GitHub + update Pi
make pi-restart              # Restart Pi service
make pi-logs                 # View Pi logs
```

## Requirements
- **macOS** (primary) or Raspberry Pi OS
- Python 3.12+
- Dependencies in `requirements.txt`:

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
