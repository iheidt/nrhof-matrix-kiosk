#!/usr/bin/env bash
set -e

echo "=== NRHOF Matrix Kiosk - Pi Bootstrap ==="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project directory
echo "Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Detect virtual environment (.venv or .venv312)
if [ -d .venv ]; then
    VENV_DIR=".venv"
    echo "Using existing virtual environment: .venv"
elif [ -d .venv312 ]; then
    VENV_DIR=".venv312"
    echo "Using existing virtual environment: .venv312"
else
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    VENV_DIR=".venv"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip tools
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Generate systemd service files with current user and paths
echo "Generating systemd service files..."
CURRENT_USER="$USER"
HOME_DIR="$HOME"

# Detect venv path
if [ -d "$PROJECT_DIR/.venv" ]; then
    VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
elif [ -d "$PROJECT_DIR/.venv312" ]; then
    VENV_PYTHON="$PROJECT_DIR/.venv312/bin/python"
else
    echo "Error: No virtual environment found!"
    exit 1
fi

# Create kiosk service file
cat > /tmp/nrhof-matrix-kiosk.service <<EOF
[Unit]
Description=NRHOF Matrix Kiosk
After=network.target sound.target graphical.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="DISPLAY=:0"
Environment="XAUTHORITY=$HOME_DIR/.Xauthority"
ExecStart=$VENV_PYTHON $PROJECT_DIR/app.py --fullscreen
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOF

# Create update service file
cat > /tmp/nrhof-matrix-update.service <<EOF
[Unit]
Description=NRHOF Matrix Kiosk Update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/update.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Copy timer file (doesn't need customization)
cp service/nrhof-matrix-update.timer /tmp/

# Install service files
echo "Installing systemd service files..."
sudo mv /tmp/nrhof-matrix-kiosk.service /etc/systemd/system/
sudo mv /tmp/nrhof-matrix-update.service /etc/systemd/system/
sudo mv /tmp/nrhof-matrix-update.timer /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable services
echo "Enabling kiosk service..."
sudo systemctl enable nrhof-matrix-kiosk.service

echo "Enabling update timer..."
sudo systemctl enable nrhof-matrix-update.timer

echo ""
echo "=== Bootstrap Complete! ==="
echo ""
echo "Next steps:"
echo "1. Create .env file with your configuration:"
echo "   nano .env"
echo ""
echo "   Required:"
echo "   OPENAI_API_KEY=your_api_key_here"
echo ""
echo "   Optional:"
echo "   PIN_BRANCH=main    # or 'dev' (default: dev)"
echo ""
echo "2. Start the kiosk service:"
echo "   sudo systemctl start nrhof-matrix-kiosk.service"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status nrhof-matrix-kiosk.service"
echo ""
echo "4. View logs:"
echo "   journalctl -u nrhof-matrix-kiosk.service -f"
echo ""
