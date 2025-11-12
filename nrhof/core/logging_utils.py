#!/usr/bin/env python3
"""Centralized logging utilities with consistent formatting and metrics support."""

import logging
import sys
from pathlib import Path
from typing import Any

# Global configuration
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_DEFAULT_LEVEL = logging.INFO
_CONFIGURED_LOGGERS: set[str] = set()


def setup_logger(
    name: str,
    level: int | None = None,
    format_string: str | None = None,
    stream: Any = None,
) -> logging.Logger:
    """Set up a logger with consistent formatting.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
        stream: Output stream (default: sys.stdout)

    Returns:
        Configured logger instance

    Example:
        >>> from nrhof.core.logging_utils import setup_logger
        >>> logger = setup_logger(__name__)
        >>> logger.info("Application started")
    """
    logger = logging.getLogger(name)

    # Only configure once per logger name
    if name in _CONFIGURED_LOGGERS:
        return logger

    # Set level
    if level is None:
        level = _DEFAULT_LEVEL
    logger.setLevel(level)

    # Create handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler(stream or sys.stdout)
        formatter = logging.Formatter(
            format_string or _LOG_FORMAT,
            datefmt=_LOG_DATE_FORMAT,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Prevent propagation to root logger (avoid duplicate logs)
    logger.propagate = False

    # Mark as configured
    _CONFIGURED_LOGGERS.add(name)

    return logger


def set_global_log_level(level: int):
    """Set log level for all configured loggers.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)

    Example:
        >>> set_global_log_level(logging.DEBUG)
    """
    global _DEFAULT_LEVEL
    _DEFAULT_LEVEL = level

    # Update all existing loggers
    for logger_name in _CONFIGURED_LOGGERS:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


def configure_file_logging(
    log_dir: str | Path = "runtime",
    log_file: str = "app.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 3,
):
    """Configure file-based logging with rotation.

    Args:
        log_dir: Directory for log files
        log_file: Log file name
        max_bytes: Maximum file size before rotation
        backup_count: Number of backup files to keep

    Example:
        >>> configure_file_logging("logs", "nrhof.log")
    """
    from logging.handlers import RotatingFileHandler

    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_path / log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT))

    # Add to all configured loggers
    for logger_name in _CONFIGURED_LOGGERS:
        logger = logging.getLogger(logger_name)
        # Check if file handler already exists
        has_file_handler = any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
        if not has_file_handler:
            logger.addHandler(file_handler)


def get_logger_stats() -> dict[str, Any]:
    """Get statistics about configured loggers.

    Returns:
        Dictionary with logger statistics

    Example:
        >>> stats = get_logger_stats()
        >>> print(f"Configured loggers: {stats['count']}")
    """
    return {
        "count": len(_CONFIGURED_LOGGERS),
        "loggers": sorted(_CONFIGURED_LOGGERS),
        "default_level": logging.getLevelName(_DEFAULT_LEVEL),
    }


# Convenience functions for structured logging (future: metrics export)


def log_metric(
    logger: logging.Logger,
    metric_name: str,
    value: float | int,
    tags: dict[str, str] | None = None,
):
    """Log a metric value (future: export to Prometheus/JSONL).

    Args:
        logger: Logger instance
        metric_name: Metric name (e.g., 'fps', 'latency_ms')
        value: Metric value
        tags: Optional tags/labels for the metric

    Example:
        >>> log_metric(logger, "fps", 60.0, {"scene": "menu"})
    """
    tags_str = ""
    if tags:
        tags_str = " " + " ".join(f"{k}={v}" for k, v in tags.items())
    logger.debug(f"[METRIC] {metric_name}={value}{tags_str}")


def log_event(
    logger: logging.Logger,
    event_name: str,
    data: dict[str, Any] | None = None,
):
    """Log a structured event (future: export to JSONL).

    Args:
        logger: Logger instance
        event_name: Event name (e.g., 'scene_transition', 'wake_word_detected')
        data: Optional event data

    Example:
        >>> log_event(logger, "scene_transition", {"from": "menu", "to": "settings"})
    """
    data_str = ""
    if data:
        data_str = " " + " ".join(f"{k}={v}" for k, v in data.items())
    logger.info(f"[EVENT] {event_name}{data_str}")
