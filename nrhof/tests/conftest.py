"""Pytest configuration."""

import sys
from pathlib import Path

# Add project root to path (now we're one level deeper)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
