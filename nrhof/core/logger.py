#!/usr/bin/env python3
"""
Structured logging with JSON lines format and rotation.
"""

import json
import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON string
        """
        log_data = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger with JSON output and rotation."""

    def __init__(self, name: str, config: dict[str, Any]):
        """Initialize structured logger.

        Args:
            name: Logger name
            config: Logging configuration
        """
        self.logger = logging.getLogger(name)
        self.config = config
        self._setup_logger()

    def _setup_logger(self):
        """Set up logger with handlers."""
        # Get config
        log_config = self.config.get("logging", {})
        level_str = log_config.get("level", "INFO")
        log_file = log_config.get("file", "runtime/kiosk.log")
        max_bytes = log_config.get("max_size_mb", 10) * 1024 * 1024
        backup_count = log_config.get("backup_count", 3)
        structured = log_config.get("structured", True)

        # Set level
        level = getattr(logging, level_str.upper(), logging.INFO)
        self.logger.setLevel(level)

        # Remove existing handlers
        self.logger.handlers.clear()

        # Console handler (always human-readable)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler (JSON if structured)
        if log_file:
            # Create directory if needed
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
            file_handler.setLevel(level)

            if structured:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(console_formatter)

            self.logger.addHandler(file_handler)

    def debug(self, message: str, **extra):
        """Log debug message.

        Args:
            message: Log message
            **extra: Extra fields to include
        """
        self._log(logging.DEBUG, message, extra)

    def info(self, message: str, **extra):
        """Log info message.

        Args:
            message: Log message
            **extra: Extra fields to include
        """
        self._log(logging.INFO, message, extra)

    def warning(self, message: str, **extra):
        """Log warning message.

        Args:
            message: Log message
            **extra: Extra fields to include
        """
        self._log(logging.WARNING, message, extra)

    def error(self, message: str, **extra):
        """Log error message.

        Args:
            message: Log message
            **extra: Extra fields to include
        """
        self._log(logging.ERROR, message, extra)

    def exception(self, message: str, **extra):
        """Log exception with traceback.

        Args:
            message: Log message
            **extra: Extra fields to include
        """
        self._log(logging.ERROR, message, extra, exc_info=True)

    def _log(self, level: int, message: str, extra: dict[str, Any], exc_info: bool = False):
        """Internal log method.

        Args:
            level: Log level
            message: Log message
            extra: Extra fields
            exc_info: Include exception info
        """
        if extra:
            # Create log record with extra fields
            record = self.logger.makeRecord(
                self.logger.name,
                level,
                "(unknown file)",
                0,
                message,
                (),
                None if not exc_info else sys.exc_info(),
            )
            record.extra_fields = extra
            self.logger.handle(record)
        else:
            self.logger.log(level, message, exc_info=exc_info)


# Global logger instance
_logger: StructuredLogger | None = None


def get_logger(name: str = "kiosk", config: dict[str, Any] | None = None) -> StructuredLogger:
    """Get global logger instance.

    Args:
        name: Logger name
        config: Configuration (only used on first call)

    Returns:
        StructuredLogger instance
    """
    global _logger
    if _logger is None:
        if config is None:
            config = {}
        _logger = StructuredLogger(name, config)
    return _logger
