#!/usr/bin/env python3
"""Lifecycle hook system for managing application, scene, and component lifecycles."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from core.logger import get_logger


class LifecyclePhase(Enum):
    """Lifecycle phases for hooks."""

    # Application lifecycle
    APP_STARTUP = auto()  # Before any initialization
    APP_READY = auto()  # After all components initialized
    APP_PRE_FRAME = auto()  # Before each frame
    APP_POST_FRAME = auto()  # After each frame
    APP_SHUTDOWN = auto()  # Before shutdown
    APP_CLEANUP = auto()  # Final cleanup

    # Scene lifecycle
    SCENE_BEFORE_ENTER = auto()  # Before scene.on_enter()
    SCENE_AFTER_ENTER = auto()  # After scene.on_enter()
    SCENE_BEFORE_EXIT = auto()  # Before scene.on_exit()
    SCENE_AFTER_EXIT = auto()  # After scene.on_exit()
    SCENE_PAUSE = auto()  # Scene paused (backgrounded)
    SCENE_RESUME = auto()  # Scene resumed (foregrounded)
    SCENE_DESTROY = auto()  # Scene being destroyed

    # Worker lifecycle
    WORKER_START = auto()  # Worker starting
    WORKER_STOP = auto()  # Worker stopping
    WORKER_ERROR = auto()  # Worker error occurred

    # Resource lifecycle
    RESOURCE_LOAD = auto()  # Resource loading
    RESOURCE_UNLOAD = auto()  # Resource unloading


@dataclass
class HookContext:
    """Context passed to lifecycle hooks."""

    phase: LifecyclePhase
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access to data."""
        return self.data.get(key)

    def __setitem__(self, key: str, value: Any):
        """Allow dict-like setting of data."""
        self.data[key] = value


@dataclass
class Hook:
    """Represents a single lifecycle hook."""

    name: str
    callback: Callable[[HookContext], None]
    priority: int = 0  # Higher priority runs first
    once: bool = False  # Run only once then auto-unregister
    enabled: bool = True

    def execute(self, context: HookContext) -> bool:
        """Execute the hook callback.

        Returns:
            bool: True if hook should be kept, False if it should be removed
        """
        if not self.enabled:
            return True

        try:
            self.callback(context)
            return not self.once  # Remove if once=True
        except Exception as e:
            logger = get_logger("lifecycle")
            logger.error(f"Hook '{self.name}' failed", error=str(e), phase=context.phase.name)
            return True  # Keep hook even on error


class LifecycleManager:
    """Manages lifecycle hooks across the application."""

    def __init__(self):
        self._hooks: dict[LifecyclePhase, list[Hook]] = {phase: [] for phase in LifecyclePhase}
        self._logger = get_logger("lifecycle")
        self._metrics: dict[str, Any] = {
            "hooks_executed": 0,
            "hooks_failed": 0,
            "phase_counts": {phase: 0 for phase in LifecyclePhase},
        }

    def register(
        self,
        phase: LifecyclePhase,
        name: str,
        callback: Callable[[HookContext], None],
        priority: int = 0,
        once: bool = False,
    ) -> Hook:
        """Register a lifecycle hook.

        Args:
            phase: Lifecycle phase to hook into
            name: Unique name for the hook
            callback: Function to call (receives HookContext)
            priority: Execution priority (higher runs first)
            once: If True, hook runs once then auto-unregisters

        Returns:
            Hook: The registered hook object
        """
        hook = Hook(name=name, callback=callback, priority=priority, once=once)
        self._hooks[phase].append(hook)
        # Sort by priority (descending)
        self._hooks[phase].sort(key=lambda h: h.priority, reverse=True)
        self._logger.debug(
            f"Registered hook '{name}' for {phase.name}",
            priority=priority,
            once=once,
        )
        return hook

    def unregister(self, phase: LifecyclePhase, name: str) -> bool:
        """Unregister a hook by name.

        Args:
            phase: Lifecycle phase
            name: Hook name

        Returns:
            bool: True if hook was found and removed
        """
        hooks = self._hooks[phase]
        for i, hook in enumerate(hooks):
            if hook.name == name:
                hooks.pop(i)
                self._logger.debug(f"Unregistered hook '{name}' from {phase.name}")
                return True
        return False

    def execute(self, phase: LifecyclePhase, **context_data) -> HookContext:
        """Execute all hooks for a given phase.

        Args:
            phase: Lifecycle phase to execute
            **context_data: Additional data to pass to hooks

        Returns:
            HookContext: The context used for execution
        """
        context = HookContext(phase=phase, data=context_data)
        hooks = self._hooks[phase]

        # Track which hooks to remove (once=True hooks)
        to_remove = []

        for hook in hooks:
            should_keep = hook.execute(context)
            if not should_keep:
                to_remove.append(hook.name)
            self._metrics["hooks_executed"] += 1

        # Remove once-only hooks
        for name in to_remove:
            self.unregister(phase, name)

        self._metrics["phase_counts"][phase] += 1
        return context

    def clear(self, phase: LifecyclePhase | None = None):
        """Clear hooks for a phase or all phases.

        Args:
            phase: Specific phase to clear, or None for all
        """
        if phase:
            self._hooks[phase].clear()
            self._logger.debug(f"Cleared all hooks for {phase.name}")
        else:
            for p in LifecyclePhase:
                self._hooks[p].clear()
            self._logger.debug("Cleared all lifecycle hooks")

    def get_hooks(self, phase: LifecyclePhase) -> list[Hook]:
        """Get all hooks for a phase.

        Args:
            phase: Lifecycle phase

        Returns:
            List[Hook]: List of hooks (copy)
        """
        return self._hooks[phase].copy()

    def get_metrics(self) -> dict[str, Any]:
        """Get lifecycle metrics.

        Returns:
            Dict: Metrics data
        """
        return self._metrics.copy()


# Global lifecycle manager instance
_lifecycle_manager: LifecycleManager | None = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get the global lifecycle manager instance.

    Returns:
        LifecycleManager: Global instance
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


def register_hook(
    phase: LifecyclePhase,
    name: str,
    callback: Callable[[HookContext], None],
    priority: int = 0,
    once: bool = False,
) -> Hook:
    """Convenience function to register a hook.

    Args:
        phase: Lifecycle phase
        name: Hook name
        callback: Callback function
        priority: Execution priority
        once: Run once flag

    Returns:
        Hook: Registered hook
    """
    return get_lifecycle_manager().register(phase, name, callback, priority, once)


def execute_hooks(phase: LifecyclePhase, **context_data) -> HookContext:
    """Convenience function to execute hooks.

    Args:
        phase: Lifecycle phase
        **context_data: Context data

    Returns:
        HookContext: Execution context
    """
    return get_lifecycle_manager().execute(phase, **context_data)


__all__ = [
    "LifecyclePhase",
    "HookContext",
    "Hook",
    "LifecycleManager",
    "get_lifecycle_manager",
    "register_hook",
    "execute_hooks",
]
