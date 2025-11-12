"""Test configuration loading."""

from nrhof.core.config_loader import load_config


def test_config_parses():
    """Test that config.yaml parses correctly."""
    cfg = load_config()
    assert isinstance(cfg, dict)
    assert "render" in cfg
    assert "audio" in cfg


def test_config_has_required_keys():
    """Test that config has all required top-level keys."""
    cfg = load_config()
    required_keys = ["render", "audio", "features", "menu", "fonts"]
    for key in required_keys:
        assert key in cfg, f"Missing required config key: {key}"


def test_render_config_structure():
    """Test render config has expected structure."""
    cfg = load_config()
    render = cfg["render"]
    assert "resolution" in render
    assert isinstance(render["resolution"], list)
    assert len(render["resolution"]) == 2
    assert "backend" in render
