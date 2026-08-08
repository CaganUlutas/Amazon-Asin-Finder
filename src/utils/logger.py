"""
Logging configuration for the Amazon ASIN Finder application.

Provides a dual-output logger that writes to:
1. Rotating log files on disk
2. A Qt signal-based handler for real-time UI log display

Usage:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Task started")
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Callable

from src.utils.constants import (
    LOG_DIR,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
)


class UILogHandler(logging.Handler):
    """
    Custom logging handler that forwards log records to the UI.

    Instead of writing to a stream, this handler calls a registered
    callback function with formatted log messages. This allows the
    log panel in the UI to display real-time log entries.
    """

    _callback: Optional[Callable[[str, str, str], None]] = None

    def __init__(self, level=logging.DEBUG):
        super().__init__(level)

    @classmethod
    def set_callback(cls, callback: Callable[[str, str, str], None]) -> None:
        """
        Register a callback to receive log messages.

        Args:
            callback: A function accepting (timestamp, level, message).
        """
        cls._callback = callback

    @classmethod
    def clear_callback(cls) -> None:
        """Remove the registered callback."""
        cls._callback = None

    def emit(self, record: logging.LogRecord) -> None:
        """Forward the log record to the registered UI callback."""
        if self._callback is None:
            return
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            level = record.levelname
            message = self.format(record)
            self._callback(timestamp, level, message)
        except Exception:
            # Silently ignore errors in the UI handler to prevent
            # recursive logging failures
            pass


def setup_logging(level: int = logging.DEBUG) -> None:
    """
    Configure the application-wide logging system.

    Sets up:
    - Root logger with the specified level
    - Rotating file handler (writes to logs/asin_finder.log)
    - Console handler (stderr)
    - UI handler (for real-time log panel updates)
    """
    root_logger = logging.getLogger("asin_finder")

    # Prevent duplicate handlers on repeated calls
    if root_logger.handlers:
        return

    root_logger.setLevel(level)

    # Formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # File handler with rotation
    log_file = LOG_DIR / "asin_finder.log"
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # UI handler
    ui_handler = UILogHandler(level=logging.DEBUG)
    ui_formatter = logging.Formatter("%(name)s | %(message)s")
    ui_handler.setFormatter(ui_formatter)
    root_logger.addHandler(ui_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger under the application's logger hierarchy.

    Args:
        name: The logger name (typically __name__).

    Returns:
        A configured Logger instance.

    Example:
        logger = get_logger(__name__)
        logger.info("Crawling started for URL: %s", url)
    """
    # Ensure logging is set up
    setup_logging()

    # Create child logger under the root
    if name.startswith("src."):
        # Strip the 'src.' prefix for cleaner log output
        short_name = name.replace("src.", "", 1)
    else:
        short_name = name

    return logging.getLogger(f"asin_finder.{short_name}")
