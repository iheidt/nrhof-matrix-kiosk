#!/usr/bin/env python3
"""Configuration loader with environment-based config support."""

import os
import re
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str = "config/base.yaml") -> dict[str, Any]:
    """Load configuration from YAML files with environment-based overrides.

    Loads base config from config/base.yaml and merges with environment-specific
    config from config/envs/{NRHOF_ENV}.yaml (default: dev).

    Args:
        config_path: Path to base config file (default: config/base.yaml)

    Returns:
        Configuration dictionary with environment overrides applied

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML

    Environment Variables:
        NRHOF_ENV: Environment name (dev|prod, default: dev)
    """
    # Determine environment
    env = os.getenv("NRHOF_ENV", "dev")

    # Load base config
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file) as f:
        config = yaml.safe_load(f)

    if config is None:
        config = {}

    # Load environment-specific config
    env_config_path = Path(f"config/envs/{env}.yaml")
    if env_config_path.exists():
        print(f"⚙️  Loading {env} environment config")
        with open(env_config_path) as f:
            env_config = yaml.safe_load(f)
        if env_config:
            # Merge environment config into base config
            _deep_merge(config, env_config)
    else:
        print(f"⚠️  No environment config found for '{env}' (expected: {env_config_path})")

    # Expand environment variables in config
    config = _expand_env_vars(config)

    # Validate config if STRICT_CONFIG is set
    if os.getenv("STRICT_CONFIG", "1") != "0":
        try:
            from nrhof.core.config_schema import config_to_dict, validate_config

            validated = validate_config(config)
            config = config_to_dict(validated)
            print("✓ Config validation passed")
        except ImportError:
            print("Warning: pydantic not installed, skipping validation")
        except Exception as e:
            print(f"✗ Config validation failed: {e}")
            raise

    return config


def _expand_env_vars(obj: Any) -> Any:
    """Recursively expand ${VAR} environment variables in config.

    Args:
        obj: Config object (dict, list, str, or other)

    Returns:
        Object with environment variables expanded
    """
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Match ${VAR} or $VAR patterns
        def replace_env(match):
            var_name = match.group(1) or match.group(2)
            return os.getenv(var_name, match.group(0))  # Keep original if not found

        # Replace ${VAR} and $VAR patterns
        result = re.sub(r"\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)", replace_env, obj)
        return result
    else:
        return obj


def _deep_merge(base: dict, override: dict):
    """Deep merge override dict into base dict in-place.

    Args:
        base: Base configuration dictionary (modified in-place)
        override: Override configuration dictionary
    """
    for key, value in override.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            # Recursively merge nested dicts
            _deep_merge(base[key], value)
        else:
            # Override value
            base[key] = value


def get_nested(config: dict, path: str, default: Any = None) -> Any:
    """Get nested config value using dot notation.

    Args:
        config: Configuration dictionary
        path: Dot-separated path (e.g., 'render.resolution')
        default: Default value if path not found

    Returns:
        Config value or default

    Examples:
        >>> config = {'render': {'resolution': [1280, 1024]}}
        >>> get_nested(config, 'render.resolution')
        [1280, 1024]
        >>> get_nested(config, 'render.missing', default=[800, 600])
        [800, 600]
    """
    keys = path.split(".")
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def set_nested(config: dict, path: str, value: Any):
    """Set nested config value using dot notation.

    Args:
        config: Configuration dictionary
        path: Dot-separated path (e.g., 'render.resolution')
        value: Value to set

    Examples:
        >>> config = {}
        >>> set_nested(config, 'render.resolution', [1920, 1080])
        >>> config
        {'render': {'resolution': [1920, 1080]}}
    """
    keys = path.split(".")
    current = config

    # Navigate to parent of target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the value
    current[keys[-1]] = value


# CLI argument override helpers
def override_from_args(config: dict, args):
    """Apply CLI argument overrides to config.

    Args:
        config: Configuration dictionary
        args: Parsed argparse arguments

    Common overrides:
        --fullscreen -> render.fullscreen
        --windowed -> render.fullscreen (False)
        --resolution WxH -> render.resolution
        --display N -> render.display
    """
    if hasattr(args, "fullscreen") and args.fullscreen:
        set_nested(config, "render.fullscreen", True)

    if hasattr(args, "windowed") and args.windowed:
        set_nested(config, "render.fullscreen", False)

    if hasattr(args, "resolution") and args.resolution:
        # Parse "1920x1080" format
        try:
            w, h = map(int, args.resolution.lower().split("x"))
            set_nested(config, "render.resolution", [w, h])
        except (ValueError, AttributeError):
            print(f"Warning: Invalid resolution format: {args.resolution}")

    if hasattr(args, "display") and args.display is not None:
        set_nested(config, "render.display", int(args.display))
