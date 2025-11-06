#!/usr/bin/env python3
"""Application path constants."""

from pathlib import Path

# Project root directory
ROOT = Path(__file__).resolve().parent.parent

__all__ = ['ROOT']