"""Tests for error handling utilities."""

import pytest

from polymind.utils.errors import PolymindError, TradeError, RiskError, ConfigError


def test_polymind_error_is_exception() -> None:
    """PolymindError should be an Exception."""
    error = PolymindError("test error")
    assert isinstance(error, Exception)
    assert str(error) == "test error"


def test_trade_error_inherits_from_polymind_error() -> None:
    """TradeError should inherit from PolymindError."""
    error = TradeError("trade failed")
    assert isinstance(error, PolymindError)


def test_risk_error_inherits_from_polymind_error() -> None:
    """RiskError should inherit from PolymindError."""
    error = RiskError("risk limit exceeded")
    assert isinstance(error, PolymindError)


def test_config_error_inherits_from_polymind_error() -> None:
    """ConfigError should inherit from PolymindError."""
    error = ConfigError("invalid config")
    assert isinstance(error, PolymindError)
