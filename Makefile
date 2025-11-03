# NRHOF Matrix Kiosk - Makefile
# Convenient commands for development and deployment

# Configuration
PI_HOST ?= raspberrypi.local
PI_USER ?= iheidt
PI_PATH ?= /home/$(PI_USER)/nrhof-matrix-kiosk
BRANCH ?= main
MAC_LAUNCHAGENT := ~/Library/LaunchAgents/com.nrhof.matrix-kiosk.plist

.PHONY: help push deploy pi-pull pi-restart pi-logs pi-status pi-ssh test mac-install mac-start mac-stop mac-restart mac-logs mac-status mac-uninstall

# Default target
help:
	@echo "NRHOF Matrix Kiosk - Deployment Commands"
	@echo ""
	@echo "Development Workflow:"
	@echo "  make push          - Commit and push to GitHub"
	@echo "  make deploy        - Push to GitHub + update Pi"
	@echo ""
	@echo "Mac Mini Management:"
	@echo "  make mac-install   - Install LaunchAgent (manual start)"
	@echo "  make mac-start     - Start kiosk service"
	@echo "  make mac-stop      - Stop kiosk service"
	@echo "  make mac-restart   - Restart kiosk service"
	@echo "  make mac-logs      - View kiosk logs"
	@echo "  make mac-status    - Check service status"
	@echo "  make mac-uninstall - Remove LaunchAgent"
	@echo ""
	@echo "Pi Management:"
	@echo "  make pi-pull       - Pull latest code on Pi"
	@echo "  make pi-restart    - Restart kiosk service on Pi"
	@echo "  make pi-logs       - View live logs from Pi"
	@echo "  make pi-status     - Check service status on Pi"
	@echo "  make pi-ssh        - SSH into Pi"
	@echo ""
	@echo "Local Testing:"
	@echo "  make test          - Run app locally"
	@echo "  make test-full     - Run app in fullscreen"
	@echo ""
	@echo "Configuration:"
	@echo "  PI_HOST=$(PI_HOST)"
	@echo "  PI_USER=$(PI_USER)"
	@echo "  PI_PATH=$(PI_PATH)"

# Push to GitHub
push:
	@echo "📦 Committing and pushing to GitHub..."
	@git add .
	@git status --short
	@read -p "Commit message: " msg; \
	git commit -m "$$msg" || true
	@git push origin $(BRANCH)
	@echo "✅ Pushed to GitHub"

# Full deployment: push to GitHub + update Pi
deploy: push
	@echo "🚀 Deploying to Pi..."
	@./scripts/deploy_to_pi.sh $(PI_USER)@$(PI_HOST) $(PI_PATH)
	@echo "✅ Deployment complete!"

# Pull latest code on Pi
pi-pull:
	@echo "📥 Pulling latest code on Pi..."
	@ssh $(PI_USER)@$(PI_HOST) "cd $(PI_PATH) && git pull"
	@echo "✅ Code updated on Pi"

# Restart kiosk service on Pi
pi-restart:
	@echo "🔄 Restarting kiosk service on Pi..."
	@ssh $(PI_USER)@$(PI_HOST) "sudo systemctl restart nrhof-matrix-kiosk.service"
	@echo "✅ Service restarted"

# View live logs from Pi
pi-logs:
	@echo "📋 Viewing Pi logs (Ctrl+C to exit)..."
	@ssh $(PI_USER)@$(PI_HOST) "journalctl -u nrhof-matrix-kiosk.service -f"

# Check service status on Pi
pi-status:
	@echo "📊 Checking Pi service status..."
	@ssh $(PI_USER)@$(PI_HOST) "sudo systemctl status nrhof-matrix-kiosk.service"

# SSH into Pi
pi-ssh:
	@ssh $(PI_USER)@$(PI_HOST)

# Run locally for testing
test:
	@echo "🧪 Running app locally..."
	python app.py

# Run locally in fullscreen
test-full:
	@echo "🧪 Running app in fullscreen..."
	python app.py --fullscreen

# Quick update (no commit, just pull on Pi)
quick-update:
	@$(MAKE) pi-pull
	@$(MAKE) pi-restart

# ============================================
# Mac Mini Deployment Commands
# ============================================

# Install LaunchAgent (manual start)
mac-install:
	@echo "🍎 Installing Mac Mini LaunchAgent..."
	@mkdir -p logs
	@mkdir -p ~/Library/LaunchAgents
	@cp service/com.nrhof.matrix-kiosk.plist $(MAC_LAUNCHAGENT)
	@launchctl load $(MAC_LAUNCHAGENT)
	@echo "✅ LaunchAgent installed"
	@echo "   Use 'make mac-start' to run kiosk"
	@echo "   Use 'make mac-stop' to stop kiosk"

# Start kiosk service
mac-start:
	@echo "▶️  Starting kiosk..."
	@launchctl start com.nrhof.matrix-kiosk
	@echo "✅ Kiosk started"

# Stop kiosk service
mac-stop:
	@echo "⏹️  Stopping kiosk..."
	@launchctl stop com.nrhof.matrix-kiosk
	@echo "✅ Kiosk stopped"

# Restart kiosk service
mac-restart: mac-stop
	@sleep 2
	@$(MAKE) mac-start

# View kiosk logs
mac-logs:
	@echo "📋 Viewing kiosk logs (Ctrl+C to exit)..."
	@tail -f logs/kiosk.log

# View error logs
mac-errors:
	@echo "📋 Viewing error logs..."
	@tail -f logs/kiosk.error.log

# Check service status
mac-status:
	@echo "📊 Checking kiosk status..."
	@launchctl list | grep com.nrhof.matrix-kiosk || echo "Service not running"

# Uninstall LaunchAgent
mac-uninstall:
	@echo "🗑️  Uninstalling LaunchAgent..."
	@launchctl unload $(MAC_LAUNCHAGENT) 2>/dev/null || true
	@rm -f $(MAC_LAUNCHAGENT)
	@echo "✅ LaunchAgent uninstalled"

# Reinstall (useful after config changes)
mac-reinstall: mac-uninstall mac-install
