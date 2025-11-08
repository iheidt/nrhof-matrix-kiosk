"""Test renderer interface contract."""

from renderers import create_renderer


def test_renderer_init_shutdown():
    """Test renderer can initialize and shutdown."""
    cfg = {"render": {"resolution": [800, 600], "backend": "pygame"}}
    renderer = create_renderer(cfg)
    renderer.initialize()

    # Should have a surface
    surface = renderer.get_surface()
    assert surface is not None

    # Cleanup
    renderer.shutdown()


def test_renderer_has_required_methods():
    """Test renderer implements required interface."""
    cfg = {"render": {"resolution": [800, 600], "backend": "pygame"}}
    renderer = create_renderer(cfg)

    # Check required methods exist
    assert hasattr(renderer, "initialize")
    assert hasattr(renderer, "get_surface")
    assert hasattr(renderer, "shutdown")
    assert callable(renderer.initialize)
    assert callable(renderer.get_surface)
    assert callable(renderer.shutdown)


def test_renderer_optional_methods():
    """Test renderer has optional methods."""
    cfg = {"render": {"resolution": [800, 600], "backend": "pygame"}}
    renderer = create_renderer(cfg)

    # Check optional methods exist (may be no-op)
    assert hasattr(renderer, "render")
    assert hasattr(renderer, "present")
    assert callable(renderer.render)
    assert callable(renderer.present)
