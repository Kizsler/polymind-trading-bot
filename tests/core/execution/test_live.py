"""Tests for live executor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from polymind.core.execution.live import LiveExecutor, LiveExecutorError


class TestLiveExecutor:
    """Tests for LiveExecutor."""

    def test_init_without_credentials_raises(self) -> None:
        """Test that init without credentials raises error."""
        with pytest.raises(LiveExecutorError, match="credentials"):
            LiveExecutor(api_key=None, api_secret=None)

    def test_init_with_credentials(self) -> None:
        """Test successful init with credentials."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )
        assert executor.is_configured

    @pytest.mark.asyncio
    async def test_submit_order_success(self) -> None:
        """Test successful order submission."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )

        # Mock the CLOB client
        mock_response = {
            "orderID": "order_123",
            "status": "MATCHED",
            "matchedAmount": "100",
            "averagePrice": "0.55",
        }

        executor._clob_client = AsyncMock()
        executor._clob_client.create_order = AsyncMock(return_value=mock_response)

        result = await executor.submit_order(
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )

        assert result["order_id"] == "order_123"
        assert result["status"] == "filled"
        assert result["filled_size"] == 100.0

    @pytest.mark.asyncio
    async def test_submit_order_partial_fill(self) -> None:
        """Test partial fill handling."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )

        mock_response = {
            "orderID": "order_123",
            "status": "OPEN",
            "matchedAmount": "60",
            "averagePrice": "0.54",
        }

        executor._clob_client = AsyncMock()
        executor._clob_client.create_order = AsyncMock(return_value=mock_response)

        result = await executor.submit_order(
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )

        assert result["status"] == "partial"
        assert result["filled_size"] == 60.0

    @pytest.mark.asyncio
    async def test_cancel_order(self) -> None:
        """Test order cancellation."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )

        executor._clob_client = AsyncMock()
        executor._clob_client.cancel_order = AsyncMock(return_value={"success": True})

        result = await executor.cancel_order("order_123")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_order_status(self) -> None:
        """Test getting order status."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )

        mock_response = {
            "orderID": "order_123",
            "status": "MATCHED",
            "matchedAmount": "100",
            "averagePrice": "0.55",
        }

        executor._clob_client = AsyncMock()
        executor._clob_client.get_order = AsyncMock(return_value=mock_response)

        result = await executor.get_order_status("order_123")
        assert result["status"] == "filled"
        assert result["filled_size"] == 100.0
