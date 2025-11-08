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


class PerformanceMonitor:
    """Monitor performance metrics like FPS and memory."""

    def __init__(self):
        """Initialize performance monitor."""
        self.frame_times = []
        self.max_samples = 300  # Keep last 5 seconds at 60 FPS
        self.scene_transitions = []
        self.initial_memory = None

    def record_frame_time(self, dt: float):
        """Record frame time.

        Args:
            dt: Delta time in seconds
        """
        self.frame_times.append(dt)
        if len(self.frame_times) > self.max_samples:
            self.frame_times.pop(0)

    def get_fps_stats(self) -> dict:
        """Get FPS statistics.

        Returns:
            Dict with avg_fps, p99_frame_time_ms
        """
        if not self.frame_times:
            return {"avg_fps": 0, "p99_frame_time_ms": 0}

        avg_dt = sum(self.frame_times) / len(self.frame_times)
        avg_fps = 1.0 / avg_dt if avg_dt > 0 else 0

        # Calculate 99th percentile frame time
        sorted_times = sorted(self.frame_times)
        p99_idx = int(len(sorted_times) * 0.99)
        p99_frame_time = sorted_times[p99_idx] if sorted_times else 0

        return {
            "avg_fps": round(avg_fps, 1),
            "p99_frame_time_ms": round(p99_frame_time * 1000, 1),
        }

    def record_scene_transition(self, from_scene: str, to_scene: str):
        """Record scene transition with memory snapshot.

        Args:
            from_scene: Scene transitioning from
            to_scene: Scene transitioning to
        """
        import psutil

        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if self.initial_memory is None:
            self.initial_memory = memory_mb

        memory_delta = memory_mb - self.initial_memory
        fps_stats = self.get_fps_stats()

        transition = {
            "from": from_scene,
            "to": to_scene,
            "avg_fps": fps_stats["avg_fps"],
            "p99_frame_time_ms": fps_stats["p99_frame_time_ms"],
            "memory_mb": round(memory_mb, 1),
            "memory_delta_mb": round(memory_delta, 1),
        }

        self.scene_transitions.append(transition)

        # Log transition
        print(
            f"📊 Scene: {from_scene} → {to_scene} | "
            f"FPS: {fps_stats['avg_fps']} | "
            f"P99: {fps_stats['p99_frame_time_ms']}ms | "
            f"Mem: {memory_delta:+.1f}MB"
        )

    def get_report(self) -> str:
        """Get performance report.

        Returns:
            Formatted performance report
        """
        if not self.scene_transitions:
            return "No scene transitions recorded"

        report = ["Performance Report:", "=" * 80]

        for t in self.scene_transitions:
            report.append(
                f"{t['from']:20} → {t['to']:20} | "
                f"FPS: {t['avg_fps']:5.1f} | "
                f"P99: {t['p99_frame_time_ms']:5.1f}ms | "
                f"Mem: {t['memory_delta_mb']:+6.1f}MB"
            )

        return "\n".join(report)


# Global instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    return _performance_monitor
