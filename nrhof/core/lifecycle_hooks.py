"""Lifecycle hooks for NRHOF.

Provides hook registrations for application lifecycle events.
"""

from nrhof.core.lifecycle import LifecyclePhase, register_hook


def register_lifecycle_hooks():
    """Register all lifecycle hooks for the application."""
    # App lifecycle hooks
    register_hook(
        LifecyclePhase.APP_STARTUP,
        "log_startup",
        lambda ctx: print("[LIFECYCLE] App starting up..."),
        priority=100,
    )

    register_hook(
        LifecyclePhase.APP_READY,
        "log_ready",
        lambda ctx: print(f"[LIFECYCLE] App ready! Components: {list(ctx['components'].keys())}"),
        priority=100,
    )

    register_hook(
        LifecyclePhase.APP_PRE_FRAME,
        "log_first_frame",
        lambda ctx: print(f"[LIFECYCLE] First frame at {ctx.timestamp:.2f}"),
        priority=100,
        once=True,  # Only log first frame
    )

    register_hook(
        LifecyclePhase.APP_SHUTDOWN,
        "log_shutdown",
        lambda ctx: print(f"[LIFECYCLE] App shutting down. Workers: {list(ctx['workers'].keys())}"),
        priority=100,
    )

    # Worker lifecycle hooks
    register_hook(
        LifecyclePhase.WORKER_START,
        "log_worker_start",
        lambda ctx: print(f"[LIFECYCLE] Worker starting: {ctx['worker_name']}"),
        priority=50,
    )

    register_hook(
        LifecyclePhase.WORKER_STOP,
        "log_worker_stop",
        lambda ctx: print(f"[LIFECYCLE] Worker stopping: {ctx['worker_name']}"),
        priority=50,
    )
