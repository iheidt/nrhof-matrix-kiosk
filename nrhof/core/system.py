#!/usr/bin/env python3
"""System utilities for launching external commands."""

import subprocess


def launch_command(cmd: str):
    """Launch a system command in a subprocess.

    Args:
        cmd: Command string to execute

    Example:
        launch_command('open /Applications/Safari.app')
    """
    try:
        subprocess.Popen(cmd, shell=True)
    except Exception as e:
        print(f"Failed to launch '{cmd}': {e}")


__all__ = ["launch_command"]
