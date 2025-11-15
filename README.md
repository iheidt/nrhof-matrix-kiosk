# NRHOF Bot

A fullscreen 1280x1024 interactive bot with touchscreen menu, voice commands, and audio visualizations. Runs on Mac Mini.

## Quick Start

### Mac Mini Setup (Primary Platform)

```bash
# Clone and setup
git clone <repo-url>
cd nrhof-bot
python3 -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt

# Test locally
make test                    # Windowed mode
make test-full               # Fullscreen on secondary display

# Install for bot use (manual start/stop)
make mac-install

# Start/stop bot
make mac-start               # Start fullscreen on secondary display
make mac-stop                # Stop and return to normal use
make mac-logs                # View logs
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
      {"label": "Option 1", "icon": "assets/option1.svg", "command": "chromium-browser --fullscreen https://example.com"},
      {"label": "Option 2", "icon": "assets/option2.svg", "command": "/usr/bin/python3 /home/pi/some_app/main.py"},
      {"label": "Option 3", "icon": "assets/option3.svg", "command": "lxterminal -e htop"}
    ]
  }
}
```
- If an icon is missing, a labeled placeholder is drawn.
- SVGs are rasterized at runtime if CairoSVG is available; PNGs/JPGs also work.

## Bot at boot with systemd
1. Copy the project to Pi (suggested path `/home/pi/nrhof-bot`).
2. Install deps (see above).
3. Install service:
```bash
sudo cp service/nrhof-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nrhof-bot.service
sudo systemctl start nrhof-bot.service
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
