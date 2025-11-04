"""Theme loader - merges content, layout, and style configurations."""

import yaml
from pathlib import Path
from typing import Any, Dict


class ThemeLoader:
    """Loads and merges theme configuration from content/, layouts/, and styles/."""
    
    def __init__(self, root_dir: Path = None):
        """Initialize theme loader.
        
        Args:
            root_dir: Root directory of the project (defaults to current file's parent)
        """
        if root_dir is None:
            root_dir = Path(__file__).parent
        
        self.root_dir = Path(root_dir)
        self.content_dir = self.root_dir / "content"
        self.layouts_dir = self.root_dir / "layouts"
        self.styles_dir = self.root_dir / "styles"
        
        # Cache loaded files
        self._cache = {}
    
    def load_yaml(self, filepath: Path) -> Dict[str, Any]:
        """Load a YAML file with caching.
        
        Args:
            filepath: Path to YAML file
            
        Returns:
            Parsed YAML as dictionary
        """
        if filepath in self._cache:
            return self._cache[filepath]
        
        if not filepath.exists():
            return {}
        
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        self._cache[filepath] = data
        return data
    
    def load_style(self, theme_name: str = "pipboy") -> Dict[str, Any]:
        """Load style configuration.
        
        Args:
            theme_name: Name of the theme (e.g., 'pipboy', 'amber')
            
        Returns:
            Style configuration dictionary
        """
        # Load base styles first
        base = self.load_yaml(self.styles_dir / "_base.yaml")
        
        # Load theme-specific styles
        theme = self.load_yaml(self.styles_dir / f"{theme_name}.yaml")
        
        # Merge (theme overrides base)
        return self._deep_merge(base, theme)
    
    def load_layout(self, scene_name: str) -> Dict[str, Any]:
        """Load layout configuration for a scene.
        
        Args:
            scene_name: Name of the scene (e.g., 'splash', 'menu', 'intro')
            
        Returns:
            Layout configuration dictionary
        """
        return self.load_yaml(self.layouts_dir / f"{scene_name}.yaml")
    
    def load_content(self, content_name: str) -> Dict[str, Any]:
        """Load content configuration.
        
        Args:
            content_name: Name of the content file (e.g., 'menu', 'intro', 'splash')
            
        Returns:
            Content configuration dictionary
        """
        return self.load_yaml(self.content_dir / f"{content_name}.yaml")
    
    def load_theme(self, scene_name: str, theme_name: str = "pipboy") -> Dict[str, Any]:
        """Load complete theme for a scene (content + layout + style).
        
        Args:
            scene_name: Name of the scene
            theme_name: Name of the theme
            
        Returns:
            Merged theme configuration
        """
        content = self.load_content(scene_name)
        layout = self.load_layout(scene_name)
        style = self.load_style(theme_name)
        
        # Merge all three
        theme = {
            "content": content,
            "layout": layout,
            "style": style
        }
        
        return theme
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def resolve_position(self, position: Any, screen_size: tuple) -> tuple:
        """Resolve position expressions like 'center' or 'center - 60'.
        
        Args:
            position: Position value (can be int, str, or list)
            screen_size: (width, height) of screen
            
        Returns:
            (x, y) tuple of resolved positions
        """
        w, h = screen_size
        
        if isinstance(position, list):
            x = self._resolve_coord(position[0], w, "x")
            y = self._resolve_coord(position[1], h, "y")
            return (x, y)
        
        return (0, 0)
    
    def _resolve_coord(self, value: Any, dimension: int, axis: str) -> int:
        """Resolve a single coordinate value.
        
        Args:
            value: Coordinate value (int, 'center', 'center - 60', etc.)
            dimension: Screen dimension (width or height)
            axis: 'x' or 'y'
            
        Returns:
            Resolved coordinate as integer
        """
        if isinstance(value, int):
            return value
        
        if isinstance(value, str):
            value = value.strip()
            
            # Handle 'center'
            if value == "center":
                return dimension // 2
            
            # Handle 'bottom' or 'right'
            if value in ["bottom", "right"]:
                return dimension
            
            # Handle 'top' or 'left'
            if value in ["top", "left"]:
                return 0
            
            # Handle expressions like "center - 60" or "bottom - 40"
            if "center" in value:
                center = dimension // 2
                if "+" in value:
                    offset = int(value.split("+")[1].strip())
                    return center + offset
                elif "-" in value:
                    offset = int(value.split("-")[1].strip())
                    return center - offset
                return center
            
            if "bottom" in value or "right" in value:
                if "-" in value:
                    offset = int(value.split("-")[1].strip())
                    return dimension - offset
                return dimension
        
        return 0


# Global theme loader instance
_theme_loader = None

def get_theme_loader() -> ThemeLoader:
    """Get global theme loader instance."""
    global _theme_loader
    if _theme_loader is None:
        _theme_loader = ThemeLoader()
    return _theme_loader