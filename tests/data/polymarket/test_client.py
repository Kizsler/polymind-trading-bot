"""Tests for Polymarket client wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from polymind.data.polymarket.client import PolymarketClient
from polymind.data.polymarket.exceptions import (
    PolymarketAPIError,
    PolymarketAuthError,
)


@pytest.fixture
def mock_clob_client() -> MagicMock:
    """Create mock CLOB client."""
    client = MagicMock()
    client.get_simplified_markets = MagicMock(
        return_value=[{"condition_id": "0x123", "question": "Will BTC hit 100k?"}]
    )
    client.get_order_book = MagicMock(
        return_value={
            "bids": [{"price": "0.65", "size": "100"}],
            "asks": [{"price": "0.67", "size": "150"}],
        }
    )
    client.get_price = MagicMock(return_value="0.65")
    client.get_midpoint = MagicMock(return_value="0.66")
    client.get_last_trade_price = MagicMock(return_value="0.64")
    return client


def test_client_can_be_created() -> None:
    """Client should initialize without API key for read-only."""
    client = PolymarketClient()
    assert client is not None


def test_client_get_markets(mock_clob_client: MagicMock) -> None:
    """Client should fetch markets."""
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        markets = client.get_markets()
        assert len(markets) > 0
        assert "condition_id" in markets[0]


def test_client_get_orderbook(mock_clob_client: MagicMock) -> None:
    """Client should fetch orderbook for a market."""
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        book = client.get_orderbook("0x123")
        assert "bids" in book
        assert "asks" in book


def test_client_get_market_found(mock_clob_client: MagicMock) -> None:
    """Client should find a market by condition ID."""
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        market = client.get_market("0x123")
        assert market is not None
        assert market["condition_id"] == "0x123"
        assert market["question"] == "Will BTC hit 100k?"


def test_client_get_market_not_found(mock_clob_client: MagicMock) -> None:
    """Client should return None when market not found."""
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        market = client.get_market("0xNONEXISTENT")
        assert market is None


def test_client_get_price(mock_clob_client: MagicMock) -> None:
    """Client should fetch price for a token."""
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        price = client.get_price("0x123", "BUY")
        assert price == 0.65
        mock_clob_client.get_price.assert_called_once_with("0x123", "BUY")


def test_client_get_price_returns_zero_when_none(mock_clob_client: MagicMock) -> None:
    """Client should return 0.0 when price is None."""
    mock_clob_client.get_price = MagicMock(return_value=None)
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        price = client.get_price("0x123")
        assert price == 0.0


def test_client_get_midpoint(mock_clob_client: MagicMock) -> None:
    """Client should fetch midpoint for a token."""
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        midpoint = client.get_midpoint("0x123")
        assert midpoint == 0.66
        mock_clob_client.get_midpoint.assert_called_once_with("0x123")


def test_client_get_midpoint_returns_zero_when_none(
    mock_clob_client: MagicMock,
) -> None:
    """Client should return 0.0 when midpoint is None."""
    mock_clob_client.get_midpoint = MagicMock(return_value=None)
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        midpoint = client.get_midpoint("0x123")
        assert midpoint == 0.0


def test_client_get_last_trade_price(mock_clob_client: MagicMock) -> None:
    """Client should fetch last trade price for a token."""
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        price = client.get_last_trade_price("0x123")
        assert price == 0.64
        mock_clob_client.get_last_trade_price.assert_called_once_with("0x123")


def test_client_get_last_trade_price_returns_zero_when_none(
    mock_clob_client: MagicMock,
) -> None:
    """Client should return 0.0 when last trade price is None."""
    mock_clob_client.get_last_trade_price = MagicMock(return_value=None)
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        price = client.get_last_trade_price("0x123")
        assert price == 0.0


def test_client_get_markets_api_error(mock_clob_client: MagicMock) -> None:
    """Client should raise PolymarketAPIError when API call fails."""
    mock_clob_client.get_simplified_markets = MagicMock(
        side_effect=Exception("API connection failed")
    )
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        with pytest.raises(PolymarketAPIError) as exc_info:
            client.get_markets()
        assert "Failed to fetch markets" in str(exc_info.value)


def test_client_get_orderbook_api_error(mock_clob_client: MagicMock) -> None:
    """Client should raise PolymarketAPIError when orderbook fetch fails."""
    mock_clob_client.get_order_book = MagicMock(
        side_effect=Exception("Network timeout")
    )
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        with pytest.raises(PolymarketAPIError) as exc_info:
            client.get_orderbook("0x123")
        assert "Failed to fetch orderbook" in str(exc_info.value)


def test_client_get_price_api_error(mock_clob_client: MagicMock) -> None:
    """Client should raise PolymarketAPIError when price fetch fails."""
    mock_clob_client.get_price = MagicMock(side_effect=Exception("Server error"))
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        with pytest.raises(PolymarketAPIError) as exc_info:
            client.get_price("0x123")
        assert "Failed to fetch price" in str(exc_info.value)


def test_client_get_midpoint_api_error(mock_clob_client: MagicMock) -> None:
    """Client should raise PolymarketAPIError when midpoint fetch fails."""
    mock_clob_client.get_midpoint = MagicMock(side_effect=Exception("Rate limited"))
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        with pytest.raises(PolymarketAPIError) as exc_info:
            client.get_midpoint("0x123")
        assert "Failed to fetch midpoint" in str(exc_info.value)


def test_client_get_last_trade_price_api_error(mock_clob_client: MagicMock) -> None:
    """Client should raise PolymarketAPIError when last trade price fetch fails."""
    mock_clob_client.get_last_trade_price = MagicMock(
        side_effect=Exception("Connection refused")
    )
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        client = PolymarketClient()
        with pytest.raises(PolymarketAPIError) as exc_info:
            client.get_last_trade_price("0x123")
        assert "Failed to fetch last trade price" in str(exc_info.value)


def test_client_auth_error() -> None:
    """Client should raise PolymarketAuthError when authentication fails."""
    mock_clob_client = MagicMock()
    mock_clob_client.create_or_derive_api_creds = MagicMock(
        side_effect=Exception("Invalid private key")
    )
    with patch(
        "polymind.data.polymarket.client.ClobClient", return_value=mock_clob_client
    ):
        with pytest.raises(PolymarketAuthError) as exc_info:
            PolymarketClient(private_key="invalid_key")
        assert "Failed to authenticate" in str(exc_info.value)
