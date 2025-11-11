#!/usr/bin/env python3
"""
Event Bus - Lock-free event dispatcher for multi-threaded architecture.

Events flow from workers to the main render loop without blocking.
"""

import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.events import EventType

__all__ = ["EventBus", "EventType", "Event", "get_event_bus"]


@dataclass
class Event:
    """Event with type, payload, and metadata."""

    type: EventType
    payload: dict[str, Any]
    timestamp: float
    source: str = "unknown"

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class EventBus:
    """Lock-free event bus using queues for thread-safe communication."""

    def __init__(self, max_queue_size: int = 1000):
        """Initialize event bus.

        Args:
            max_queue_size: Maximum events in queue before blocking
        """
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._subscribers: dict[EventType, list[Callable]] = {}
        self._lock = threading.Lock()
        self._running = True

        # Metrics
        self._events_emitted = 0
        self._events_processed = 0
        self._events_dropped = 0

    def emit(
        self,
        event_type: EventType,
        payload: dict[str, Any] | None = None,
        source: str = "unknown",
    ):
        """Emit an event (non-blocking).

        Args:
            event_type: Type of event
            payload: Event data
            source: Source identifier (e.g., 'audio_worker', 'render_loop')
        """
        if not self._running:
            return

        event = Event(type=event_type, payload=payload or {}, timestamp=time.time(), source=source)

        try:
            # Non-blocking put with immediate timeout
            self._queue.put_nowait(event)
            self._events_emitted += 1
        except queue.Full:
            self._events_dropped += 1
            print(f"Warning: Event queue full, dropped {event_type}")

    def subscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> tuple[EventType, Callable]:
        """Subscribe to an event type.

        Args:
            event_type: Type of event to listen for
            handler: Callback function(event)

        Returns:
            Subscription token (event_type, handler) for unsubscription
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
        return (event_type, handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """Unsubscribe from an event type.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(handler)
                except ValueError:
                    pass

    def unsubscribe_token(self, token: tuple[EventType, Callable]):
        """Unsubscribe using a subscription token.

        Args:
            token: Subscription token returned from subscribe()
        """
        event_type, handler = token
        self.unsubscribe(event_type, handler)

    def process_events(self, max_events: int = 100) -> int:
        """Process pending events (call from main loop).

        Args:
            max_events: Maximum events to process per call

        Returns:
            Number of events processed
        """
        processed = 0

        while processed < max_events:
            try:
                # Non-blocking get
                event = self._queue.get_nowait()
                self._dispatch(event)
                processed += 1
                self._events_processed += 1
            except queue.Empty:
                break

        return processed

    def _dispatch(self, event: Event):
        """Dispatch event to subscribers.

        Args:
            event: Event to dispatch
        """
        with self._lock:
            handlers = self._subscribers.get(event.type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Error in event handler for {event.type}: {e}")

    def get_metrics(self) -> dict[str, int]:
        """Get event bus metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "events_emitted": self._events_emitted,
            "events_processed": self._events_processed,
            "events_dropped": self._events_dropped,
            "queue_size": self._queue.qsize(),
        }

    def shutdown(self):
        """Shutdown event bus."""
        self._running = False
        # Clear queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get global event bus instance.

    Returns:
        Global EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
