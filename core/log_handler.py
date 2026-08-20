"""Contains the core logic of logging."""

from __future__ import annotations

__all__ = ["setup_logger"]

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"


def setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger with separate file and console handlers.

    Args:
        name (str): Name of logger, typically __name__ from the caller.

    Returns:
        Logger: Configured logger instance.

    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers.
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure console handler.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Configure file handler.
    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        mode="w",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger.
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Return the logger.
    return logger
