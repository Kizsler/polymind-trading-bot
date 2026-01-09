"""Tests for logging utilities."""

import pytest

from polymind.utils.logging import configure_logging, get_logger


def test_configure_logging_returns_logger() -> None:
    """configure_logging should return a configured logger."""
    logger = configure_logging(level="DEBUG")
    assert logger is not None


def test_get_logger_returns_child_logger() -> None:
    """get_logger should return a named logger."""
    logger = get_logger("test.module")
    assert logger is not None


def test_logger_has_expected_methods() -> None:
    """Logger should have standard logging methods."""
    logger = get_logger("test")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
