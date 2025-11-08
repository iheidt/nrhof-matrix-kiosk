# Scene Cleanup Best Practices

## Overview

The base [Scene](cci:2://file:///Users/ianheidt/CascadeProjects/nrhof-matrix-kiosk/scenes/scene_manager.py:45:0-207:20) class now provides automatic cleanup on scene exit to prevent memory leaks.

## Automatic Cleanup

When a scene exits, the following cleanup happens automatically:

1. **Event Unsubscription**: All registered event handlers are unsubscribed
2. **Surface Deletion**: All registered pygame surfaces are deleted (frees VRAM)
3. **Cache Clearing**: All registered caches (dicts/lists) are cleared
4. **Event Queue**: Pygame event queue is cleared
5. **Garbage Collection**: Python GC is forced to run

## How to Use

### Register Event Subscriptions

```python
class MyScene(Scene):
    def on_enter(self):
        super().on_enter()

        # Subscribe to event
        def my_handler(event):
            print(f"Got event: {event}")

        self.ctx.event_bus.subscribe(EventType.LANGUAGE_CHANGED, my_handler)

        # Register for automatic cleanup
        self.register_event_subscription(EventType.LANGUAGE_CHANGED, my_handler)
