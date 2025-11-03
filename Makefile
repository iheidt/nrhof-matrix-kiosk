# NRHOF Matrix Kiosk - Makefile
# Convenient commands for Mac → GitHub → Pi workflow

# Configuration
PI_HOST ?= raspberrypi.local
PI_USER ?= iheidt
PI_PATH ?= /home/$(PI_USER)/nrhof-matrix-kiosk
BRANCH ?= main

.PHONY: help push deploy pi-pull pi-restart pi-logs pi-status pi-ssh test

# Default target
help:
	@echo "NRHOF Matrix Kiosk - Deployment Commands"
	@echo ""
	@echo "Development Workflow:"
	@echo "  make push          - Commit and push to GitHub"
	@echo "  make deploy        - Push to GitHub + update Pi"
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
