"""Tests for Data API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.data.polymarket.data_api import DataAPIClient


def test_data_api_client_has_base_url() -> None:
    """DataAPIClient should have correct base URL."""
    client = DataAPIClient()
    assert client.base_url == "https://data-api.polymarket.com"


@pytest.mark.asyncio
async def test_get_wallet_trades_returns_list() -> None:
    """get_wallet_trades should return a list of trades."""
    client = DataAPIClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "trade1",
            "market": "0x123",
            "asset_id": "token1",
            "side": "BUY",
            "size": "100",
            "price": "0.55",
            "timestamp": "1704067200",
            "transaction_hash": "0xabc",
            "maker": "0xwallet123",
        },
    ]

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        trades = await client.get_wallet_trades("0xwallet123")

    assert isinstance(trades, list)
    assert len(trades) == 1
    assert trades[0]["market"] == "0x123"


@pytest.mark.asyncio
async def test_get_wallet_positions_returns_list() -> None:
    """get_wallet_positions should return wallet positions."""
    client = DataAPIClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "asset_id": "token1",
            "market": "0x123",
            "size": "50",
            "average_price": "0.60",
        },
    ]

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        positions = await client.get_wallet_positions("0xwallet123")

    assert isinstance(positions, list)


@pytest.mark.asyncio
async def test_get_wallet_activity_returns_list() -> None:
    """get_wallet_activity should return recent activity."""
    client = DataAPIClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"type": "trade", "timestamp": "1704067200"},
    ]

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        activity = await client.get_wallet_activity("0xwallet123")

    assert isinstance(activity, list)


@pytest.mark.asyncio
async def test_get_wallet_trades_since_timestamp() -> None:
    """get_wallet_trades should support filtering by timestamp."""
    client = DataAPIClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await client.get_wallet_trades("0xwallet123", since_timestamp=1704067200)

        # Verify the timestamp param was passed
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs or len(call_args.args) > 1


@pytest.mark.asyncio
async def test_close_closes_http_client() -> None:
    """close should close the HTTP client."""
    client = DataAPIClient()

    with patch.object(client._http, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_get_market_holders_returns_list() -> None:
    """get_market_holders should return list of holders."""
    client = DataAPIClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"wallet": "0xwallet1", "size": "1000"},
        {"wallet": "0xwallet2", "size": "500"},
    ]

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        holders = await client.get_market_holders("0xmarket123")

    assert isinstance(holders, list)
    assert len(holders) == 2


@pytest.mark.asyncio
async def test_get_wallet_trades_raises_api_error_on_http_error() -> None:
    """get_wallet_trades should raise PolymarketAPIError on HTTP errors."""
    import httpx

    from polymind.data.polymarket.exceptions import PolymarketAPIError

    client = DataAPIClient()

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(PolymarketAPIError) as exc_info:
            await client.get_wallet_trades("0xwallet123")

        assert "Failed to fetch trades" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_wallet_positions_raises_api_error_on_http_error() -> None:
    """get_wallet_positions should raise PolymarketAPIError on HTTP errors."""
    import httpx

    from polymind.data.polymarket.exceptions import PolymarketAPIError

    client = DataAPIClient()

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(PolymarketAPIError) as exc_info:
            await client.get_wallet_positions("0xwallet123")

        assert "Failed to fetch positions" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_wallet_activity_raises_api_error_on_http_error() -> None:
    """get_wallet_activity should raise PolymarketAPIError on HTTP errors."""
    import httpx

    from polymind.data.polymarket.exceptions import PolymarketAPIError

    client = DataAPIClient()

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(PolymarketAPIError) as exc_info:
            await client.get_wallet_activity("0xwallet123")

        assert "Failed to fetch activity" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_market_holders_raises_api_error_on_http_error() -> None:
    """get_market_holders should raise PolymarketAPIError on HTTP errors."""
    import httpx

    from polymind.data.polymarket.exceptions import PolymarketAPIError

    client = DataAPIClient()

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(PolymarketAPIError) as exc_info:
            await client.get_market_holders("0xmarket123")

        assert "Failed to fetch holders" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_wallet_trades_with_limit() -> None:
    """get_wallet_trades should pass limit parameter."""
    client = DataAPIClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await client.get_wallet_trades("0xwallet123", limit=50)

        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 50


@pytest.mark.asyncio
async def test_wallet_address_is_lowercased() -> None:
    """Wallet address should be lowercased before sending to API."""
    client = DataAPIClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await client.get_wallet_trades("0xWALLET123")

        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["user"] == "0xwallet123"
