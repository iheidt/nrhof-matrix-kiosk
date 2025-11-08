"""Test renderer interface."""
import pytest
from renderers.base import RendererBase
from renderers import FrameState


class MockRenderer(RendererBase):
    """Mock renderer for testing."""
    
    def __init__(self, config):
        super().__init__(config)
        self.initialized = False
        self.frames_rendered = []
        self.shutdown_called = False
    
    def initialize(self):
        self.initialized = True
    
    def get_surface(self):
        return "mock_surface"
    
    def shutdown(self):
        self.shutdown_called = True
    
    def render(self, frame_state):
        self.frames_rendered.append(frame_state)
    
    def present(self):
        pass


def test_renderer_interface():
    """Test that renderer interface works."""
    config = {"render": {"resolution": [1280, 1024]}}
    renderer = MockRenderer(config)
    
    assert not renderer.initialized
    
    renderer.initialize()
    assert renderer.initialized
    
    surface = renderer.get_surface()
    assert surface == "mock_surface"
    
    renderer.shutdown()
    assert renderer.shutdown_called


def test_renderer_optional_methods():
    """Test that render() and present() are optional."""
    config = {}
    renderer = MockRenderer(config)
    
    # These should work without error
    frame_state = FrameState()
    renderer.render(frame_state)
    renderer.present()
    
    assert len(renderer.frames_rendered) == 1
