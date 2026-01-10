"""Tests for order manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.execution.manager import OrderManager
from polymind.core.execution.order import Order, OrderStatus


class TestOrderManager:
    """Tests for OrderManager."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def manager(self, mock_cache: MagicMock) -> OrderManager:
        """Create order manager with mocks."""
        return OrderManager(cache=mock_cache, retry_delay=0.01)

    @pytest.mark.asyncio
    async def test_create_order(self, manager: OrderManager) -> None:
        """Test creating a new order."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )
        assert order.status == OrderStatus.PENDING
        assert order.signal_id == "sig_123"
        assert order.id is not None

    @pytest.mark.asyncio
    async def test_save_and_load_order(self, manager: OrderManager, mock_cache: MagicMock) -> None:
        """Test saving and loading order from cache."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )

        await manager.save_order(order)
        mock_cache.set.assert_called()

        # Simulate cache returning the order
        mock_cache.get.return_value = order.to_dict()
        loaded = await manager.get_order(order.id)
        assert loaded is not None
        assert loaded.signal_id == "sig_123"

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, manager: OrderManager) -> None:
        """Test successful execution on first try."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )

        # Mock executor that succeeds
        executor = AsyncMock()
        executor.submit_order.return_value = {
            "order_id": "ext_456",
            "status": "filled",
            "filled_size": 100.0,
            "filled_price": 0.54,
        }

        result = await manager.execute_with_retry(order, executor)
        assert result.status == OrderStatus.FILLED
        assert executor.submit_order.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_retries_on_failure(self, manager: OrderManager) -> None:
        """Test retry on transient failure."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
            max_attempts=3,
        )

        # Mock executor that fails twice then succeeds
        executor = AsyncMock()
        executor.submit_order.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            {
                "order_id": "ext_456",
                "status": "filled",
                "filled_size": 100.0,
                "filled_price": 0.54,
            },
        ]

        result = await manager.execute_with_retry(order, executor)
        assert result.status == OrderStatus.FILLED
        assert executor.submit_order.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausts_retries(self, manager: OrderManager) -> None:
        """Test failure after exhausting retries."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
            max_attempts=2,
        )

        # Mock executor that always fails
        executor = AsyncMock()
        executor.submit_order.side_effect = Exception("Timeout")

        result = await manager.execute_with_retry(order, executor)
        assert result.status == OrderStatus.FAILED
        assert executor.submit_order.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_partial_fill(self, manager: OrderManager) -> None:
        """Test handling partial fill."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )

        # Mock executor returns partial fill
        executor = AsyncMock()
        executor.submit_order.return_value = {
            "order_id": "ext_456",
            "status": "partial",
            "filled_size": 60.0,
            "filled_price": 0.54,
        }

        result = await manager.execute_with_retry(order, executor)
        assert result.status == OrderStatus.PARTIAL
        assert result.filled_size == 60.0
