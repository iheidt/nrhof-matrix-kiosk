# Scene Cleanup Best Practices

## Overview

The base [Scene](cci:2://file:///Users/ianheidt/CascadeProjects/nrhof-matrix-kiosk/scenes/scene_manager.py:45:0-219:20) class provides automatic cleanup on scene exit to prevent memory leaks.

## Automatic Cleanup

When a scene exits, the following cleanup happens automatically:

1. **Event Unsubscription**: All registered event handlers are unsubscribed using tokens
2. **Surface Deletion**: All registered pygame surfaces are deleted (frees VRAM)
3. **Cache Clearing**: All registered caches (dicts/lists) are cleared
4. **Event Queue**: Pygame event queue is cleared
5. **Garbage Collection**: Python GC is forced to run

## Best Practices

1. **Always call `super().on_enter()` and `super().on_exit()`** in scene subclasses
2. **Use `subscribe_event()` for event subscriptions** - tokens are tracked automatically
3. **Register large surfaces** with `register_surface()` for automatic cleanup
4. **Register scene-specific caches** with `register_cache()` for automatic clearing
5. **Avoid storing references** to heavy objects in scene instance variables without cleanup
6. **Test scene transitions** to ensure memory is released properly

## Memory Profiling

By default, memory profiling is **disabled** to prevent performance degradation. The profiling operations (garbage collection + memory snapshots) can take 200-800ms and block the main thread during scene transitions.

### Enable Memory Profiling

To debug memory leaks, enable profiling:

```bash
ENABLE_MEMORY_PROFILING=1 python app.py
```

This will:
- Take memory snapshots on scene enter/exit
- Run full garbage collection on scene exit
- Print detailed memory diff reports

**Warning:** This will cause noticeable frame drops (FPS drops, P99 latency spikes up to 500ms) during scene transitions.

### Production Mode

In production, the app uses:
- **Periodic lightweight GC** - Runs `gc.collect(generation=0)` every 5 seconds (fast, non-blocking)
- **Cache eviction** - Clears font and widget caches on scene exit
- **No memory snapshots** - Avoids expensive tracemalloc operations

This provides good memory management without impacting performance.

## How to Use

### Subscribe to Events

```python
class MyScene(Scene):
    def on_enter(self):
        super().on_enter()

        # Subscribe to event (automatically tracked for cleanup)
        def my_handler(event):
            print(f"Got event: {event}")

        self.subscribe_event(EventType.LANGUAGE_CHANGED, my_handler)
        # Token is automatically stored and unsubscribed on exit
