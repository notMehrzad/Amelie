"""Contains the core logic of logging."""

from __future__ import annotations

__all__ = ["setup_logger"]

import logging
from typing import final, override

from colorama import Fore, Style, init

init(autoreset=True)  # ensures colors reset automatically


@final
class _ColorFormatter(logging.Formatter):
    COLORS = {  # noqa: RUF012
        logging.INFO: Fore.BLUE,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.LIGHTRED_EX,
        logging.CRITICAL: Fore.RED,
    }

    @override
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return color + message + Style.RESET_ALL


def setup_logger(logger_name: str) -> logging.Logger:
    """Create and configure a logger with separate file and console handlers.

    Args:
        logger_name (str): Name of logger, typically __name__ from the caller.

    Returns:
        Logger: Configured logger instance.

    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers.
    if logger.handlers:
        return logger

    # Configure file handler.
    file_handler = logging.FileHandler(filename="log.log", mode="w", encoding="utf-8")
    # Store only warning, error and critical logging in file
    file_handler.setLevel(logging.WARNING)
    file_handler_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%I:%M:%S %p",
    )
    file_handler.setFormatter(file_handler_format)

    # console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # everything will be logged on the console
    console_handler_format = _ColorFormatter("%(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_handler_format)

    logger.addHandler(file_handler)  # adds file handler
    logger.addHandler(console_handler)  # adds console handler

    return logger
