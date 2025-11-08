"""Test event bus dependency injection."""

from core.event_bus import EventBus, EventType


def test_event_bus_creation():
    """Test that we can create an event bus instance."""
    bus = EventBus()
    assert bus is not None


def test_event_bus_emit_and_subscribe():
    """Test event emission and subscription."""
    bus = EventBus()
    received_events = []

    def handler(event):
        received_events.append(event)

    bus.subscribe(EventType.LANGUAGE_CHANGED, handler)
    bus.emit(EventType.LANGUAGE_CHANGED, {"old": "en", "new": "jp"}, source="test")

    # Process events
    bus.process_events()

    assert len(received_events) == 1
    assert received_events[0].type == EventType.LANGUAGE_CHANGED
    assert received_events[0].payload["old"] == "en"


def test_event_bus_injection():
    """Test that event bus can be injected (not just global)."""
    bus1 = EventBus()
    bus2 = EventBus()

    # They should be different instances
    assert bus1 is not bus2

    # Each should work independently
    count1 = []
    count2 = []

    bus1.subscribe(EventType.SHUTDOWN, lambda e: count1.append(1))
    bus2.subscribe(EventType.SHUTDOWN, lambda e: count2.append(1))

    bus1.emit(EventType.SHUTDOWN, {}, source="test")
    bus1.process_events()

    assert len(count1) == 1
    assert len(count2) == 0
