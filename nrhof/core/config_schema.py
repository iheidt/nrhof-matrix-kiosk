"""Configuration schema validation using Pydantic."""

from typing import Any, Literal

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator
except ImportError:
    # Fallback if pydantic not installed
    BaseModel = object  # type: ignore

    def Field(*args, **kwargs):  # noqa: N802
        """Fallback Field function."""
        return None

    def field_validator(*args, **kwargs):
        """Fallback field_validator decorator."""

        def decorator(f):
            return f

        return decorator


class RenderConfig(BaseModel):
    """Render configuration."""

    backend: Literal["pygame", "swift"] = "pygame"
    resolution: list[int] = Field(default=[1280, 1024], min_length=2, max_length=2)
    fullscreen: bool = False
    display: int = 0

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v):
        """Validate resolution is positive."""
        if len(v) != 2:
            raise ValueError("Resolution must be [width, height]")
        if v[0] <= 0 or v[1] <= 0:
            raise ValueError("Resolution dimensions must be positive")
        return v


class AudioConfig(BaseModel):
    """Audio configuration."""

    sample_rate: int = Field(default=16000, gt=0)
    channels: int = Field(default=1, ge=1, le=2)
    chunk_size: int = Field(default=512, gt=0)
    device_index: int | None = None
    muted: bool = False


class FeaturesConfig(BaseModel):
    """Features configuration."""

    wake_word: bool = True
    song_recognition: bool = False
    voice_recognition: bool = False
    webflow_integration: bool = True


class MenuConfig(BaseModel):
    """Menu configuration."""

    auto_cycle: bool = False
    cycle_interval: float = Field(default=5.0, gt=0)


class FontsConfig(BaseModel):
    """Fonts configuration."""

    directory: str = "assets/fonts"


class ColorsConfig(BaseModel):
    """Colors configuration."""

    primary: list[int] | str = [255, 20, 147]
    secondary: list[int] | str = [255, 255, 255]
    background: list[int] | str = [0, 0, 0]
    dim: list[int] | str = "#2C405B"


class AppConfig(BaseModel):
    """Top-level application configuration."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields for flexibility

    title: str = "NRHOF Matrix Kiosk"
    render: RenderConfig = Field(default_factory=RenderConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    menu: MenuConfig = Field(default_factory=MenuConfig)
    fonts: FontsConfig = Field(default_factory=FontsConfig)
    dev_overrides: dict[str, Any] | None = None


def validate_config(config_dict: dict[str, Any]) -> AppConfig:
    """Validate configuration dictionary.

    Args:
        config_dict: Raw configuration dictionary from YAML

    Returns:
        Validated AppConfig object

    Raises:
        ValidationError: If configuration is invalid
    """
    if BaseModel is object:
        # Pydantic not installed, return dict as-is
        print("Warning: pydantic not installed, skipping config validation")
        return config_dict  # type: ignore

    return AppConfig(**config_dict)


def config_to_dict(config: AppConfig) -> dict[str, Any]:
    """Convert AppConfig back to dictionary.

    Args:
        config: Validated AppConfig object

    Returns:
        Dictionary representation
    """
    if isinstance(config, dict):
        return config
    return config.model_dump()
