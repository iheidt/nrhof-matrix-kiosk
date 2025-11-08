"""Memory leak detection using tracemalloc."""

import tracemalloc


class MemoryProbe:
    """Track memory allocations using tracemalloc."""

    def __init__(self):
        """Initialize memory probe."""
        self.snapshots = {}
        self.tracing = False

    def start_trace(self):
        """Start tracing memory allocations."""
        if not self.tracing:
            tracemalloc.start()
            self.tracing = True
            print("🔬 Memory tracing started")

    def stop_trace(self):
        """Stop tracing memory allocations."""
        if self.tracing:
            tracemalloc.stop()
            self.tracing = False
            print("🔬 Memory tracing stopped")

    def snapshot(self, tag: str):
        """Take a memory snapshot with a tag.

        Args:
            tag: Tag to identify this snapshot (e.g., "enter:MenuScene")
        """
        if not self.tracing:
            return

        snapshot = tracemalloc.take_snapshot()
        self.snapshots[tag] = snapshot

    def compare(self, tag_a: str, tag_b: str, top_n: int = 15):
        """Compare two snapshots and log top differences.

        Args:
            tag_a: First snapshot tag
            tag_b: Second snapshot tag
            top_n: Number of top allocators to show (default: 15)
        """
        if tag_a not in self.snapshots or tag_b not in self.snapshots:
            print(f"⚠️  Cannot compare: missing snapshot(s) {tag_a} or {tag_b}")
            return

        snapshot_a = self.snapshots[tag_a]
        snapshot_b = self.snapshots[tag_b]

        # Compare snapshots
        top_stats = snapshot_b.compare_to(snapshot_a, "lineno")

        print(f"\n🔬 Memory diff: {tag_a} → {tag_b}")
        print("=" * 100)
        print(f"{'File:Line':<60} {'Size Diff':>15} {'Count Diff':>10}")
        print("-" * 100)

        total_size_diff = 0
        for stat in top_stats[:top_n]:
            total_size_diff += stat.size_diff

            # Format size diff
            size_diff_mb = stat.size_diff / 1024 / 1024
            size_sign = "+" if stat.size_diff > 0 else ""

            # Format count diff
            count_sign = "+" if stat.count_diff > 0 else ""

            # Truncate filename if too long
            location = f"{stat.traceback.format()[0]}"
            if len(location) > 60:
                location = "..." + location[-57:]

            print(
                f"{location:<60} {size_sign}{size_diff_mb:>13.2f} MB "
                f"{count_sign}{stat.count_diff:>9}"
            )

        # Print total
        total_mb = total_size_diff / 1024 / 1024
        total_sign = "+" if total_size_diff > 0 else ""
        print("-" * 100)
        print(f"{'TOTAL (top ' + str(top_n) + ')':<60} {total_sign}{total_mb:>13.2f} MB")
        print("=" * 100)

    def get_current_memory(self) -> float:
        """Get current memory usage in MB.

        Returns:
            Current memory usage in MB
        """
        if not self.tracing:
            return 0.0

        snapshot = tracemalloc.take_snapshot()
        total = sum(stat.size for stat in snapshot.statistics("lineno"))
        return total / 1024 / 1024

    def clear_snapshots(self):
        """Clear all stored snapshots."""
        self.snapshots.clear()


# Global instance
_memory_probe: MemoryProbe | None = None


def get_memory_probe() -> MemoryProbe:
    """Get global memory probe instance."""
    global _memory_probe
    if _memory_probe is None:
        _memory_probe = MemoryProbe()
    return _memory_probe


def start_trace():
    """Start memory tracing (convenience function)."""
    get_memory_probe().start_trace()


def snapshot(tag: str):
    """Take a memory snapshot (convenience function)."""
    get_memory_probe().snapshot(tag)


def compare(tag_a: str, tag_b: str, top_n: int = 15):
    """Compare two snapshots (convenience function)."""
    get_memory_probe().compare(tag_a, tag_b, top_n)
