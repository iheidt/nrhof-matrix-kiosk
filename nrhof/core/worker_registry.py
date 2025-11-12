"""Worker registry for managing worker lifecycle."""

from typing import Any

from nrhof.core.logging_utils import setup_logger

logger = setup_logger(__name__)


class WorkerRegistry:
    """Registry for managing worker lifecycle with consistent hooks.

    Provides centralized worker management with:
    - Registration and discovery
    - Coordinated startup/shutdown
    - Graceful error handling
    - Hot-reload support (future)
    """

    def __init__(self):
        """Initialize empty worker registry."""
        self._workers: dict[str, Any] = {}
        self._started = False

    def register(self, name: str, worker: Any) -> None:
        """Register a worker.

        Args:
            name: Unique worker name (e.g., 'audio', 'vad', 'wake_word')
            worker: Worker instance with start() and stop() methods

        Raises:
            ValueError: If worker name already registered
        """
        if name in self._workers:
            raise ValueError(f"Worker '{name}' already registered")

        self._workers[name] = worker
        logger.debug(f"Registered worker: {name}")

    def get(self, name: str) -> Any | None:
        """Get a worker by name.

        Args:
            name: Worker name

        Returns:
            Worker instance or None if not found
        """
        return self._workers.get(name)

    def start_all(self) -> dict[str, Any]:
        """Start all registered workers.

        Returns:
            Dictionary of started workers {name: worker}

        Raises:
            RuntimeError: If workers already started
        """
        if self._started:
            raise RuntimeError("Workers already started")

        logger.info(f"Starting {len(self._workers)} workers...")
        started = {}

        for name, worker in self._workers.items():
            try:
                logger.debug(f"Starting worker: {name}")
                worker.start()
                started[name] = worker
            except Exception as e:
                logger.error(f"Failed to start worker '{name}': {e}")
                # Continue starting other workers
                continue

        self._started = True
        logger.info(f"Started {len(started)}/{len(self._workers)} workers")
        return started

    def stop_all(self) -> None:
        """Stop all registered workers gracefully."""
        if not self._started:
            logger.warning("Workers not started, nothing to stop")
            return

        logger.info(f"Stopping {len(self._workers)} workers...")

        for name, worker in reversed(list(self._workers.items())):
            try:
                logger.debug(f"Stopping worker: {name}")
                if hasattr(worker, "stop"):
                    worker.stop()
                elif hasattr(worker, "shutdown"):
                    worker.shutdown()
            except Exception as e:
                logger.error(f"Error stopping worker '{name}': {e}")
                # Continue stopping other workers
                continue

        self._started = False
        logger.info("All workers stopped")

    def list_workers(self) -> list[str]:
        """Get list of registered worker names.

        Returns:
            List of worker names
        """
        return list(self._workers.keys())

    def is_started(self) -> bool:
        """Check if workers are started.

        Returns:
            True if workers have been started
        """
        return self._started

    def __len__(self) -> int:
        """Get number of registered workers."""
        return len(self._workers)

    def __contains__(self, name: str) -> bool:
        """Check if worker is registered."""
        return name in self._workers
