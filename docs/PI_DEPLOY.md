# Raspberry Pi Deployment Guide

Complete guide for deploying the NRHOF Matrix Kiosk to your Raspberry Pi 5.

## Prerequisites

### Hardware
- Raspberry Pi 5 (or Pi 4 with 4GB+ RAM)
- MicroSD card (32GB+ recommended)
- Display (1280x1024 recommended, but any resolution works)
- Audio interface (USB or built-in)
- Optional: Touchscreen for interactive features

### Software
- Raspberry Pi OS (64-bit, Bookworm or later)
- Python 3.12+ (comes with Pi OS Bookworm)
- Git installed

## Quick Start

### 1. Prepare Your Raspberry Pi

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
  python3.12 \
  python3.12-venv \
  python3-pip \
  git \
  libcairo2 \
  libpango-1.0-0 \
  libgdk-pixbuf2.0-0 \
  portaudio19-dev \
  python3-dev \
  libasound2-dev
```

### 2. Clone the Repository

```bash
# Clone to home directory
cd ~
git clone <your-repo-url> nrhof-matrix-kiosk
cd nrhof-matrix-kiosk
```

### 3. Configure Environment

Create a `.env` file with your settings:

```bash
cp .env.example .env
nano .env
```

Add your configuration:

```bash
# Required: OpenAI API key for voice recognition
OPENAI_API_KEY=your_api_key_here

# Optional: Git branch to track (default: dev)
PIN_BRANCH=main

# Optional: Override config settings
# FULLSCREEN=true
# RESOLUTION=1280x1024
```

### 4. Run Bootstrap Script

The bootstrap script will:
- Create a Python virtual environment
- Install all dependencies
- Install systemd services
- Enable auto-start on boot

```bash
chmod +x scripts/bootstrap_pi.sh
./scripts/bootstrap_pi.sh
```

### 5. Start the Kiosk

```bash
# Start immediately
sudo systemctl start nrhof-matrix-kiosk.service

# Check status
sudo systemctl status nrhof-matrix-kiosk.service

# View live logs
journalctl -u nrhof-matrix-kiosk.service -f
```

## Manual Installation (Alternative)

If you prefer to set up manually:

```bash
# 1. Create virtual environment
python3.12 -m venv .venv312
source .venv312/bin/activate

# 2. Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 3. Test run
python app.py

# 4. Install services (optional)
sudo cp service/*.service /etc/systemd/system/
sudo cp service/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nrhof-matrix-kiosk.service
sudo systemctl enable nrhof-matrix-update.timer
```

## Configuration

### Display Settings

Edit `config.yaml` to adjust display settings:

```yaml
render:
  resolution: [1280, 1024]  # Your display resolution
  fullscreen: true           # Set to true for kiosk mode
  fps_target: 60
```

### Audio Settings

```yaml
audio:
  sample_rate: 44100
  frame_size: 2048
  music_threshold: 0.01
```

### Voice Recognition

Voice commands are enabled by default. To disable:

```yaml
flags:
  enable_voice: false
```

## Auto-Update System

The kiosk includes an auto-update system that:
- Checks for updates hourly
- Pulls latest code from your configured branch
- Automatically installs new dependencies
- Restarts the service if needed

### Control Auto-Updates

```bash
# Check update timer status
sudo systemctl status nrhof-matrix-update.timer

# Disable auto-updates
sudo systemctl stop nrhof-matrix-update.timer
sudo systemctl disable nrhof-matrix-update.timer

# Manually trigger update
sudo systemctl start nrhof-matrix-update.service
```

### Pin to Specific Branch

Set `PIN_BRANCH` in your `.env` file:

```bash
PIN_BRANCH=main    # Use stable main branch
# or
PIN_BRANCH=dev     # Use development branch (default)
```

## Kiosk Mode Setup

### Disable Screen Blanking

```bash
# Method 1: Using raspi-config
sudo raspi-config
# Navigate to: Display Options → Screen Blanking → No

# Method 2: Manual configuration
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```

Add these lines:

```
@xset s off
@xset -dpms
@xset s noblank
```

### Hide Mouse Cursor

Install unclutter:

```bash
sudo apt install -y unclutter
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```

Add:

```
@unclutter -idle 0.1 -root
```

### Auto-Login (Optional)

```bash
sudo raspi-config
# Navigate to: System Options → Boot / Auto Login → Desktop Autologin
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status nrhof-matrix-kiosk.service

# View detailed logs
journalctl -u nrhof-matrix-kiosk.service -n 100 --no-pager

# Check if virtual environment exists
ls -la /home/pi/nrhof-matrix-kiosk/.venv312

# Verify Python version
python3.12 --version
```

### Audio Issues

```bash
# List audio devices
aplay -l

# Test audio output
speaker-test -t wav -c 2

# Check ALSA configuration
alsamixer
```

### Display Issues

```bash
# Check display environment
echo $DISPLAY

# Verify X authority
ls -la ~/.Xauthority

# Test pygame display
source .venv312/bin/activate
python -c "import pygame; pygame.init(); print('Pygame OK')"
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R pi:pi /home/pi/nrhof-matrix-kiosk

# Make scripts executable
chmod +x scripts/*.sh
```

### Voice Recognition Not Working

```bash
# Check microphone
arecord -l

# Test recording
arecord -d 5 test.wav
aplay test.wav

# Verify OpenAI API key
cat .env | grep OPENAI_API_KEY
```

## Service Management

### Common Commands

```bash
# Start kiosk
sudo systemctl start nrhof-matrix-kiosk.service

# Stop kiosk
sudo systemctl stop nrhof-matrix-kiosk.service

# Restart kiosk
sudo systemctl restart nrhof-matrix-kiosk.service

# Enable auto-start on boot
sudo systemctl enable nrhof-matrix-kiosk.service

# Disable auto-start
sudo systemctl disable nrhof-matrix-kiosk.service

# View logs (live)
journalctl -u nrhof-matrix-kiosk.service -f

# View logs (last 100 lines)
journalctl -u nrhof-matrix-kiosk.service -n 100
```

### Manual Testing

Run the app directly (without systemd):

```bash
cd /home/pi/nrhof-matrix-kiosk
source .venv312/bin/activate
python app.py

# Or with fullscreen
python app.py --fullscreen
```

## Performance Optimization

### GPU Memory

Increase GPU memory for better graphics performance:

```bash
sudo raspi-config
# Navigate to: Performance Options → GPU Memory → 256
```

### Overclock (Pi 5)

**Warning:** Only if you have adequate cooling.

```bash
sudo nano /boot/firmware/config.txt
```

Add:

```
over_voltage=6
arm_freq=2800
```

### Reduce Background Services

```bash
# Disable unnecessary services
sudo systemctl disable bluetooth.service
sudo systemctl disable cups.service
```

## Network Configuration

### WiFi Setup

```bash
sudo raspi-config
# Navigate to: System Options → Wireless LAN
```

### Static IP (Optional)

```bash
sudo nano /etc/dhcpcd.conf
```

Add:

```
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

### SSH Access

Enable SSH for remote management:

```bash
sudo raspi-config
# Navigate to: Interface Options → SSH → Yes
```

## Backup and Recovery

### Backup Configuration

```bash
# Backup your .env and config files
cd /home/pi/nrhof-matrix-kiosk
tar -czf ~/kiosk-backup-$(date +%Y%m%d).tar.gz .env config.yaml runtime/
```

### Restore from Backup

```bash
cd /home/pi/nrhof-matrix-kiosk
tar -xzf ~/kiosk-backup-YYYYMMDD.tar.gz
```

### Full SD Card Image

Create a full system backup:

```bash
# On your Mac/PC with SD card reader
sudo dd if=/dev/diskX of=~/pi-kiosk-backup.img bs=4M status=progress
```

## Development Workflow

### Remote Development

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Stop service for testing
sudo systemctl stop nrhof-matrix-kiosk.service

# Make changes
cd /home/pi/nrhof-matrix-kiosk
nano app.py

# Test manually
source .venv312/bin/activate
python app.py

# Restart service when done
sudo systemctl start nrhof-matrix-kiosk.service
```

### Sync from Development Machine

```bash
# On your Mac
rsync -avz --exclude '.venv*' --exclude '__pycache__' \
  /Users/ianheidt/CascadeProjects/nrhof-matrix-kiosk/ \
  pi@raspberrypi.local:/home/pi/nrhof-matrix-kiosk/

# Then restart on Pi
ssh pi@raspberrypi.local "sudo systemctl restart nrhof-matrix-kiosk.service"
```

## Monitoring

### System Resources

```bash
# CPU and memory usage
htop

# Temperature
vcgencmd measure_temp

# Disk usage
df -h
```

### Application Logs

```bash
# View application log file
tail -f runtime/kiosk.log

# View systemd journal
journalctl -u nrhof-matrix-kiosk.service -f

# Check for errors
journalctl -u nrhof-matrix-kiosk.service -p err
```

## Security Considerations

### API Key Protection

- Never commit `.env` to git
- Use restrictive file permissions:

```bash
chmod 600 .env
```

### Firewall (Optional)

```bash
sudo apt install -y ufw
sudo ufw allow ssh
sudo ufw enable
```

### Regular Updates

```bash
# Update system packages monthly
sudo apt update && sudo apt upgrade -y

# Update Python dependencies
cd /home/pi/nrhof-matrix-kiosk
source .venv312/bin/activate
pip install --upgrade -r requirements.txt
```

## Additional Resources

- **Bootstrap Script**: `scripts/bootstrap_pi.sh`
- **Update Script**: `scripts/update.sh`
- **Service File**: `service/nrhof-matrix-kiosk.service`
- **Main Config**: `config.yaml`
- **README**: `README.md`

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs: `journalctl -u nrhof-matrix-kiosk.service -n 100`
3. Test manually: `python app.py`
4. Verify dependencies: `pip list`
5. Check system resources: `htop`, `vcgencmd measure_temp`
