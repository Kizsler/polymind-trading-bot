"""Structured logging configuration."""

import sys
from typing import Any

from loguru import logger


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
) -> Any:
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        json_format: Use JSON format for structured logging.

    Returns:
        Configured logger instance.
    """
    # Remove default handler
    logger.remove()

    # Define format
    if json_format:
        log_format = "{message}"
        logger.add(
            sys.stderr,
            format=log_format,
            level=level,
            serialize=True,
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stderr,
            format=log_format,
            level=level,
            colorize=True,
        )

    return logger


def get_logger(name: str) -> Any:
    """Get a named logger.

    Args:
        name: Logger name (usually module name).

    Returns:
        Logger instance bound to the name.
    """
    return logger.bind(name=name)
