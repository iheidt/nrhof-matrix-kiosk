#!/usr/bin/env python3
"""Base worker class for background threads."""

import threading
from abc import ABC, abstractmethod

from core.event_bus import get_event_bus
from core.logger import get_logger


class BaseWorker(ABC):
    """Abstract base class for background workers.

    Provides common functionality:
    - Thread management (start/stop)
    - Lifecycle hooks integration
    - Event bus access
    - Logger setup
    - Consistent error handling
    """

    def __init__(self, config: dict, event_bus=None, logger_name: str | None = None):
        """Initialize base worker.

        Args:
            config: Configuration dictionary
            event_bus: Optional event bus instance (defaults to global)
            logger_name: Optional logger name (defaults to class name)
        """
        self.config = config
        self.event_bus = event_bus or get_event_bus()
        self.logger = get_logger(logger_name or self.__class__.__name__)

        # Thread management
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """Start the worker thread."""
        if self._running:
            self.logger.warning(f"{self.__class__.__name__} already running")
            return

        # Execute lifecycle hook
        self._execute_lifecycle_hook("WORKER_START")

        self._running = True
        self._thread = threading.Thread(
            target=self._safe_worker_loop, daemon=True, name=self.__class__.__name__
        )
        self._thread.start()
        self.logger.info(f"{self.__class__.__name__} started")

    def stop(self, timeout: float = 2.0):
        """Stop the worker thread.

        Args:
            timeout: Maximum time to wait for thread to stop (seconds)
        """
        if not self._running:
            return

        # Execute lifecycle hook
        self._execute_lifecycle_hook("WORKER_STOP")

        self.logger.info(f"Stopping {self.__class__.__name__}...")
        self._running = False

        if self._thread:
            self._thread.join(timeout=timeout)

        # Call cleanup hook
        self._cleanup()

        self.logger.info(f"{self.__class__.__name__} stopped")

    def is_running(self) -> bool:
        """Check if worker is currently running.

        Returns:
            True if worker thread is active
        """
        return self._running

    def _safe_worker_loop(self):
        """Wrapper around worker loop with error handling."""
        try:
            self._worker_loop()
        except Exception as e:
            self.logger.error(f"Fatal error in {self.__class__.__name__}", error=str(e))
        finally:
            self._running = False

    @abstractmethod
    def _worker_loop(self):
        """Main worker loop - runs in background thread.

        Subclasses must implement this method.
        Should check self._running and exit when False.
        """
        pass

    def _cleanup(self):
        """Optional cleanup hook called during stop().

        Subclasses can override to release resources.
        """
        pass

    def _execute_lifecycle_hook(self, phase: str):
        """Execute lifecycle hook if available.

        Args:
            phase: Lifecycle phase name (e.g., 'WORKER_START', 'WORKER_STOP')
        """
        try:
            from core.lifecycle import LifecyclePhase, execute_hooks

            phase_enum = getattr(LifecyclePhase, phase, None)
            if phase_enum:
                execute_hooks(phase_enum, worker_name=self.__class__.__name__, worker=self)
        except (ImportError, AttributeError):
            pass