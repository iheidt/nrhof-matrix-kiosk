"""Observability utilities for debugging and crash reporting."""

import sys
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any


class EventTap:
    """Tap into event bus for debugging."""

    def __init__(self, max_history: int = 50):
        """Initialize event tap.

        Args:
            max_history: Maximum number of events to keep in history
        """
        self.enabled = False
        self.event_history = deque(maxlen=max_history)
        self.last_event_time = None

    def enable(self):
        """Enable event tapping."""
        self.enabled = True
        print("🔍 Event debugging enabled")

    def tap(self, event_type: str, payload: dict[str, Any], source: str):
        """Tap an event.

        Args:
            event_type: Type of event
            payload: Event payload
            source: Event source
        """
        if not self.enabled:
            return

        current_time = datetime.now()
        ms_since_last = 0

        if self.last_event_time:
            delta = current_time - self.last_event_time
            ms_since_last = int(delta.total_seconds() * 1000)

        self.last_event_time = current_time

        # Calculate payload size
        payload_size = len(str(payload))

        # Log event
        print(
            f"📡 Event: {event_type} | "
            f"Source: {source} | "
            f"Payload: {payload_size}B | "
            f"Δt: {ms_since_last}ms"
        )

        # Store in history
        self.event_history.append(
            {
                "timestamp": current_time.isoformat(),
                "type": event_type,
                "source": source,
                "payload_size": payload_size,
                "ms_since_last": ms_since_last,
            }
        )

    def get_history(self) -> list[dict]:
        """Get event history.

        Returns:
            List of recent events
        """
        return list(self.event_history)


class CrashGuard:
    """Guard against crashes and write crash reports."""

    def __init__(self, event_tap: EventTap = None, runtime_dir: str = "runtime"):
        """Initialize crash guard.

        Args:
            event_tap: Optional EventTap for including event history
            runtime_dir: Directory to write crash logs
        """
        self.event_tap = event_tap
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(exist_ok=True)

    def write_crash_report(self, exc_type, exc_value, exc_traceback):
        """Write crash report to file.

        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = self.runtime_dir / f"crash_{timestamp}.log"

        with open(crash_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write(f"CRASH REPORT - {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

            # Write exception info
            f.write("EXCEPTION:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Type: {exc_type.__name__}\n")
            f.write(f"Message: {exc_value}\n\n")

            # Write traceback
            f.write("TRACEBACK:\n")
            f.write("-" * 80 + "\n")
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            f.writelines(tb_lines)
            f.write("\n")

            # Write event history if available
            if self.event_tap:
                f.write("RECENT EVENTS (last 50):\n")
                f.write("-" * 80 + "\n")
                history = self.event_tap.get_history()
                if history:
                    for event in history:
                        f.write(
                            f"[{event['timestamp']}] {event['type']} "
                            f"(source={event['source']}, "
                            f"size={event['payload_size']}B, "
                            f"Δt={event['ms_since_last']}ms)\n"
                        )
                else:
                    f.write("No events recorded\n")
                f.write("\n")

            # Write system info
            f.write("SYSTEM INFO:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Platform: {sys.platform}\n")

        print(f"\n💥 Crash report written to: {crash_file}")
        return crash_file


# Global instances
_event_tap = EventTap()
_crash_guard = CrashGuard(_event_tap)


def get_event_tap() -> EventTap:
    """Get global event tap instance."""
    return _event_tap


def get_crash_guard() -> CrashGuard:
    """Get global crash guard instance."""
    return _crash_guard
