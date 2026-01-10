"""Tests for slippage protection."""

import pytest
from polymind.core.execution.slippage import SlippageGuard, SlippageExceededError


class TestSlippageGuard:
    """Tests for SlippageGuard."""

    def test_calculate_slippage_no_slippage(self) -> None:
        """Test slippage calculation when prices match."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        slippage = guard.calculate_slippage(
            expected_price=0.50,
            actual_price=0.50,
        )
        assert slippage == 0.0

    def test_calculate_slippage_within_threshold(self) -> None:
        """Test slippage within acceptable range."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        slippage = guard.calculate_slippage(
            expected_price=0.50,
            actual_price=0.51,
        )
        assert slippage == pytest.approx(2.0, rel=0.01)

    def test_calculate_slippage_exceeds_threshold(self) -> None:
        """Test slippage exceeding threshold."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        slippage = guard.calculate_slippage(
            expected_price=0.50,
            actual_price=0.55,
        )
        assert slippage == pytest.approx(10.0, rel=0.01)

    def test_check_slippage_passes(self) -> None:
        """Test check passes when within threshold."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        # Should not raise - 1% slippage is within 2% threshold
        guard.check_slippage(expected_price=0.50, actual_price=0.505)

    def test_check_slippage_raises(self) -> None:
        """Test check raises when exceeding threshold."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        with pytest.raises(SlippageExceededError) as exc_info:
            guard.check_slippage(expected_price=0.50, actual_price=0.55)
        assert "10.0%" in str(exc_info.value)
        assert "2.0%" in str(exc_info.value)

    def test_estimate_fill_price_buy(self) -> None:
        """Test estimating fill price from orderbook for buy."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        orderbook = {
            "asks": [
                {"price": 0.50, "size": 100},
                {"price": 0.51, "size": 100},
                {"price": 0.52, "size": 100},
            ],
            "bids": [],
        }
        fill_price = guard.estimate_fill_price(
            orderbook=orderbook,
            side="BUY",
            size=150,
        )
        # 100 @ 0.50 + 50 @ 0.51 = 75.50 / 150 = 0.5033
        assert fill_price == pytest.approx(0.5033, rel=0.01)

    def test_estimate_fill_price_sell(self) -> None:
        """Test estimating fill price from orderbook for sell."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        orderbook = {
            "asks": [],
            "bids": [
                {"price": 0.50, "size": 100},
                {"price": 0.49, "size": 100},
                {"price": 0.48, "size": 100},
            ],
        }
        fill_price = guard.estimate_fill_price(
            orderbook=orderbook,
            side="SELL",
            size=150,
        )
        # 100 @ 0.50 + 50 @ 0.49 = 74.50 / 150 = 0.4967
        assert fill_price == pytest.approx(0.4967, rel=0.01)

    def test_estimate_fill_price_insufficient_liquidity(self) -> None:
        """Test when orderbook has insufficient liquidity."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        orderbook = {
            "asks": [{"price": 0.50, "size": 50}],
            "bids": [],
        }
        with pytest.raises(ValueError, match="Insufficient liquidity"):
            guard.estimate_fill_price(
                orderbook=orderbook,
                side="BUY",
                size=100,
            )
