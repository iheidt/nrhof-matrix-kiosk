#!/usr/bin/env python3
"""Thread pool management for background operations.

Provides a bounded thread pool for preload operations to prevent CPU spikes
that could impact real-time audio processing (ASR, VAD, etc.).
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from core.logger import get_logger

logger = get_logger("thread_pool")

# Global thread pool for preload operations
# Limited to 2 concurrent threads to avoid CPU spikes during voice processing
_preload_executor: ThreadPoolExecutor | None = None
_preload_lock = threading.Lock()

# Maximum concurrent preload threads
MAX_PRELOAD_THREADS = 2


def get_preload_executor() -> ThreadPoolExecutor:
    """Get or create the global preload thread pool.

    Returns:
        ThreadPoolExecutor with bounded concurrency
    """
    global _preload_executor

    with _preload_lock:
        if _preload_executor is None:
            _preload_executor = ThreadPoolExecutor(
                max_workers=MAX_PRELOAD_THREADS,
                thread_name_prefix="preload",
            )
            logger.info(f"Preload thread pool initialized (max_workers={MAX_PRELOAD_THREADS})")

    return _preload_executor


def submit_preload_task(func: Callable, name: str | None = None, *args, **kwargs):
    """Submit a preload task to the bounded thread pool.

    Args:
        func: Function to execute
        name: Optional task name for logging
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Future object
    """
    executor = get_preload_executor()
    task_name = name or func.__name__
    logger.debug(f"Submitting preload task: {task_name}")

    def _wrapped():
        try:
            logger.debug(f"Starting preload task: {task_name}")
            result = func(*args, **kwargs)
            logger.debug(f"Completed preload task: {task_name}")
            return result
        except Exception as e:
            logger.error(f"Preload task failed: {task_name}", error=str(e))
            raise

    return executor.submit(_wrapped)


def shutdown_preload_pool(wait: bool = True):
    """Shutdown the preload thread pool.

    Args:
        wait: Whether to wait for pending tasks to complete
    """
    global _preload_executor

    with _preload_lock:
        if _preload_executor is not None:
            logger.info("Shutting down preload thread pool...")
            _preload_executor.shutdown(wait=wait)
            _preload_executor = None


def create_named_thread(
    target: Callable,
    name: str,
    daemon: bool = True,
    args: tuple = (),
    kwargs: dict | None = None,
) -> threading.Thread:
    """Create a named thread with consistent conventions.

    Args:
        target: Function to run in thread
        name: Thread name (for debugging/profiling)
        daemon: Whether thread is daemon
        args: Positional arguments for target
        kwargs: Keyword arguments for target

    Returns:
        Created thread (not started)
    """
    if kwargs is None:
        kwargs = {}

    thread = threading.Thread(
        target=target,
        name=name,
        daemon=daemon,
        args=args,
        kwargs=kwargs,
    )

    logger.debug(f"Created thread: {name} (daemon={daemon})")
    return thread
