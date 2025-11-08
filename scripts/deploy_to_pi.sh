#!/usr/bin/env bash
set -e

# Deploy script: Update code on Pi and restart service
# Usage: ./deploy_to_pi.sh [user@host] [path]

PI_TARGET="${1:-iheidt@raspberrypi.local}"
PI_PATH="${2:-/home/iheidt/nrhof-matrix-kiosk}"

echo "🚀 Deploying to Pi..."
echo "   Target: $PI_TARGET"
echo "   Path: $PI_PATH"
echo ""

# Pull latest code
echo "📥 Pulling latest code..."
ssh "$PI_TARGET" "cd $PI_PATH && git pull"

# Check if requirements.txt changed
echo "🔍 Checking for dependency changes..."
REQ_CHANGED=$(ssh "$PI_TARGET" "cd $PI_PATH && git diff HEAD@{1} HEAD -- requirements.txt | wc -l" || echo "0")

if [ "$REQ_CHANGED" -gt 0 ]; then
    echo "📦 Requirements changed, updating dependencies..."
    ssh "$PI_TARGET" "cd $PI_PATH && source .venv/bin/activate && pip install -r requirements.txt"
else
    echo "✅ No dependency changes"
fi

# Check if service exists before restarting
echo "🔄 Checking for systemd service..."
SERVICE_EXISTS=$(ssh "$PI_TARGET" "systemctl list-unit-files | grep -c nrhof-matrix-kiosk.service" || echo "0")

if [ "$SERVICE_EXISTS" -gt 0 ]; then
    echo "🔄 Restarting kiosk service..."
    ssh "$PI_TARGET" "sudo systemctl restart nrhof-matrix-kiosk.service"
    echo "✅ Service restarted"

    # Show status
    echo ""
    echo "📊 Service status:"
    ssh "$PI_TARGET" "sudo systemctl status nrhof-matrix-kiosk.service --no-pager -l" || true
else
    echo "⚠️  Service not installed yet. Run bootstrap_pi.sh on the Pi first."
    echo "   Or manually run: python app.py"
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "  - View logs: make pi-logs"
echo "  - Check status: make pi-status"
echo "  - SSH to Pi: make pi-ssh"
