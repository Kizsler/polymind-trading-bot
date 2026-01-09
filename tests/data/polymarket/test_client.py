"""Tests for Polymarket client wrapper."""

import pytest
from unittest.mock import MagicMock, patch

from polymind.data.polymarket.client import PolymarketClient


@pytest.fixture
def mock_clob_client() -> MagicMock:
    """Create mock CLOB client."""
    client = MagicMock()
    client.get_simplified_markets = MagicMock(return_value=[
        {"condition_id": "0x123", "question": "Will BTC hit 100k?"}
    ])
    client.get_order_book = MagicMock(return_value={
        "bids": [{"price": "0.65", "size": "100"}],
        "asks": [{"price": "0.67", "size": "150"}]
    })
    return client


def test_client_can_be_created() -> None:
    """Client should initialize without API key for read-only."""
    client = PolymarketClient()
    assert client is not None


def test_client_get_markets(mock_clob_client: MagicMock) -> None:
    """Client should fetch markets."""
    with patch(
        "polymind.data.polymarket.client.ClobClient",
        return_value=mock_clob_client
    ):
        client = PolymarketClient()
        markets = client.get_markets()
        assert len(markets) > 0
        assert "condition_id" in markets[0]


def test_client_get_orderbook(mock_clob_client: MagicMock) -> None:
    """Client should fetch orderbook for a market."""
    with patch(
        "polymind.data.polymarket.client.ClobClient",
        return_value=mock_clob_client
    ):
        client = PolymarketClient()
        book = client.get_orderbook("0x123")
        assert "bids" in book
        assert "asks" in book
