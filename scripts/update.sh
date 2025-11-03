#!/usr/bin/env bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project directory
cd "$PROJECT_DIR"

# Read PIN_BRANCH from .env if present, else default to dev
BRANCH="dev"
if [ -f .env ]; then
    # Source .env and check for PIN_BRANCH
    source .env
    if [ -n "$PIN_BRANCH" ]; then
        BRANCH="$PIN_BRANCH"
    fi
fi

echo "Updating branch: $BRANCH"

# Store current requirements.txt hash for comparison
REQ_HASH_BEFORE=""
if [ -f requirements.txt ]; then
    REQ_HASH_BEFORE=$(md5sum requirements.txt | cut -d' ' -f1)
fi

# Fetch all remote changes
git fetch --all --prune

# Checkout and reset to remote branch
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

# Check if requirements.txt changed
REQ_HASH_AFTER=""
if [ -f requirements.txt ]; then
    REQ_HASH_AFTER=$(md5sum requirements.txt | cut -d' ' -f1)
fi

if [ "$REQ_HASH_BEFORE" != "$REQ_HASH_AFTER" ]; then
    echo "requirements.txt changed, updating dependencies..."
    # Detect virtual environment
    if [ -d .venv ]; then
        source .venv/bin/activate
        pip install -r requirements.txt
        deactivate
    elif [ -d .venv312 ]; then
        source .venv312/bin/activate
        pip install -r requirements.txt
        deactivate
    else
        echo "Warning: No virtual environment found, skipping pip install"
    fi
else
    echo "requirements.txt unchanged, skipping pip install"
fi

# Create runtime directory if needed
mkdir -p runtime

# Write timestamp
date -u +"%Y-%m-%d %H:%M:%S UTC" > runtime/last_update.txt

echo "Update complete!"
exit 0
