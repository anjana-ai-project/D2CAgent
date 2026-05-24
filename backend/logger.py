"""Centralized logger factory for the D2CAgent backend."""
import logging
import sys

from backend.config import settings


def setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger with the project's standard format.

    Args:
        name: The logger name, typically the calling module's __name__.

    Returns:
        A configured logging.Logger instance that writes to stdout.
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level.upper())

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(settings.log_level.upper())
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger
