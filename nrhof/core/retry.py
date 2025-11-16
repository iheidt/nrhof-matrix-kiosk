#!/usr/bin/env python3
"""Retry utilities for handling transient failures."""

import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from nrhof.core.logging_utils import setup_logger

logger = setup_logger(__name__)

T = TypeVar("T")


def retry(
    tries: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator with exponential backoff.

    Args:
        tries: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function that retries on failure

    Example:
        @retry(tries=3, delay=0.5, exceptions=(ConnectionError,))
        def connect_to_api():
            # May fail transiently
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            _tries, _delay = tries, delay

            for attempt in range(_tries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == _tries - 1:
                        # Last attempt - re-raise
                        raise

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{_tries}): {e}. "
                        f"Retrying in {_delay:.1f}s..."
                    )
                    time.sleep(_delay)
                    _delay *= backoff

            # Should never reach here, but satisfy type checker
            raise RuntimeError(f"{func.__name__} failed after {tries} attempts")

        return wrapper

    return decorator
