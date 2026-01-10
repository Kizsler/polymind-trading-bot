"""Tests for order state management."""

import pytest
from polymind.core.execution.order import Order, OrderStatus


class TestOrder:
    """Tests for Order model."""

    def test_create_pending_order(self) -> None:
        """Test creating a new pending order."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        assert order.status == OrderStatus.PENDING
        assert order.filled_size == 0.0
        assert order.filled_price is None
        assert order.attempts == 0

    def test_order_mark_submitted(self) -> None:
        """Test marking order as submitted."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_submitted(external_id="ext_456")
        assert order.status == OrderStatus.SUBMITTED
        assert order.external_id == "ext_456"
        assert order.attempts == 1

    def test_order_mark_filled(self) -> None:
        """Test marking order as filled."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_submitted(external_id="ext_456")
        order.mark_filled(filled_size=100.0, filled_price=0.54)
        assert order.status == OrderStatus.FILLED
        assert order.filled_size == 100.0
        assert order.filled_price == 0.54

    def test_order_mark_partial(self) -> None:
        """Test marking order as partially filled."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_submitted(external_id="ext_456")
        order.mark_partial(filled_size=60.0, filled_price=0.54)
        assert order.status == OrderStatus.PARTIAL
        assert order.filled_size == 60.0
        assert order.remaining_size == 40.0

    def test_order_mark_failed(self) -> None:
        """Test marking order as failed."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_failed(reason="Insufficient funds")
        assert order.status == OrderStatus.FAILED
        assert order.failure_reason == "Insufficient funds"

    def test_order_can_retry(self) -> None:
        """Test retry eligibility."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
            max_attempts=3,
        )
        order.mark_submitted(external_id="ext_1")
        order.mark_failed(reason="Timeout")
        assert order.can_retry is True

        order.mark_submitted(external_id="ext_2")
        order.mark_failed(reason="Timeout")
        assert order.can_retry is True

        order.mark_submitted(external_id="ext_3")
        order.mark_failed(reason="Timeout")
        assert order.can_retry is False

    def test_order_to_dict(self) -> None:
        """Test serialization to dict."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        data = order.to_dict()
        assert data["signal_id"] == "sig_123"
        assert data["status"] == "pending"
        assert "created_at" in data

    def test_order_mark_cancelled(self) -> None:
        """Test marking order as cancelled."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_cancelled()
        assert order.status == OrderStatus.CANCELLED
