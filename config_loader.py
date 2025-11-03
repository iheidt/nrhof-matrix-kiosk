#!/usr/bin/env python3
"""
Configuration loader with YAML support and environment variable overrides.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Configuration with dot notation access and env overrides."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize config from dictionary.
        
        Args:
            config_dict: Configuration dictionary
        """
        self._config = config_dict
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value with dot notation.
        
        Args:
            key: Dot-separated key (e.g., 'audio.sample_rate')
            default: Default value if key not found
            
        Returns:
            Config value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set config value with dot notation.
        
        Args:
            key: Dot-separated key
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self._config.copy()
    
    def __getitem__(self, key: str) -> Any:
        """Get config value using bracket notation.
        
        Args:
            key: Config key
            
        Returns:
            Config value
        """
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """Set config value using bracket notation.
        
        Args:
            key: Config key
            value: Value to set
        """
        self.set(key, value)


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file with env overrides.
    
    Args:
        config_path: Path to config file (default: config.yaml)
        
    Returns:
        Config object
    """
    if config_path is None:
        config_path = Path(__file__).parent / 'config.yaml'
    
    # Load YAML
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    # Apply environment variable overrides
    # Format: KIOSK_SECTION_KEY=value
    # Example: KIOSK_AUDIO_SAMPLE_RATE=48000
    for key, value in os.environ.items():
        if key.startswith('KIOSK_'):
            # Remove prefix and convert to lowercase dot notation
            config_key = key[6:].lower().replace('_', '.')
            
            # Try to parse as int, float, bool, or keep as string
            try:
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                pass  # Keep as string
            
            config_dict = _set_nested(config_dict, config_key, value)
    
    return Config(config_dict)


def _set_nested(d: Dict, key: str, value: Any) -> Dict:
    """Set nested dictionary value using dot notation.
    
    Args:
        d: Dictionary
        key: Dot-separated key
        value: Value to set
        
    Returns:
        Modified dictionary
    """
    keys = key.split('.')
    current = d
    
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    current[keys[-1]] = value
    return d