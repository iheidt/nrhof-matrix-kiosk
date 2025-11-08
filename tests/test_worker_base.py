"""Test worker base class."""
import time
import pytest
from workers.base import BaseWorker


class DummyWorker(BaseWorker):
    """Dummy worker implementation for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tick_count = 0
    
    def _worker_loop(self):
        """Simple worker that counts ticks."""
        while self._running:
            self.tick_count += 1
            time.sleep(0.01)


def test_worker_start_stop():
    """Test worker can start and stop."""
    worker = DummyWorker(config={})
    
    assert not worker.is_running()
    
    worker.start()
    assert worker.is_running()
    
    time.sleep(0.05)  # Let it tick a few times
    
    worker.stop()
    assert not worker.is_running()
    assert worker.tick_count > 0


def test_worker_event_bus_injection():
    """Test that workers can accept injected event bus."""
    from core.event_bus import EventBus
    
    custom_bus = EventBus()
    worker = DummyWorker(config={}, event_bus=custom_bus)
    
    assert worker.event_bus is custom_bus
