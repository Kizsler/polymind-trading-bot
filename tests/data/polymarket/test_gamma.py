"""Tests for Gamma API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.data.polymarket.gamma import GammaClient


def test_gamma_client_has_base_url() -> None:
    """GammaClient should have correct base URL."""
    client = GammaClient()
    assert client.base_url == "https://gamma-api.polymarket.com"


@pytest.mark.asyncio
async def test_get_markets_returns_list() -> None:
    """get_markets should return a list of markets."""
    client = GammaClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"condition_id": "0x123", "question": "Test?", "tokens": []},
    ]

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        markets = await client.get_markets()

    assert isinstance(markets, list)
    assert len(markets) == 1


@pytest.mark.asyncio
async def test_get_market_by_id() -> None:
    """get_market should fetch a specific market."""
    client = GammaClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "condition_id": "0x123",
        "question": "Will X happen?",
        "tokens": [{"token_id": "abc", "outcome": "Yes"}],
    }

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        market = await client.get_market("0x123")

    assert market is not None
    assert market["condition_id"] == "0x123"


@pytest.mark.asyncio
async def test_get_market_returns_none_for_404() -> None:
    """get_market should return None for 404 response."""
    client = GammaClient()

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        market = await client.get_market("0xNONEXISTENT")

    assert market is None


@pytest.mark.asyncio
async def test_get_events_returns_active_events() -> None:
    """get_events should return active events/markets."""
    client = GammaClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": "event1", "title": "Election", "markets": []},
    ]

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        events = await client.get_events()

    assert isinstance(events, list)


@pytest.mark.asyncio
async def test_get_market_by_slug() -> None:
    """get_market_by_slug should fetch a market by its slug."""
    client = GammaClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "condition_id": "0x456",
        "question": "Will Y happen?",
        "slug": "will-y-happen",
    }

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        market = await client.get_market_by_slug("will-y-happen")

    assert market is not None
    assert market["slug"] == "will-y-happen"


@pytest.mark.asyncio
async def test_get_market_by_slug_returns_none_for_404() -> None:
    """get_market_by_slug should return None for 404 response."""
    client = GammaClient()

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        market = await client.get_market_by_slug("nonexistent-slug")

    assert market is None


@pytest.mark.asyncio
async def test_search_markets() -> None:
    """search_markets should search for markets by query."""
    client = GammaClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"condition_id": "0x789", "question": "Bitcoin price?"},
    ]

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        markets = await client.search_markets("bitcoin")

    assert isinstance(markets, list)
    assert len(markets) == 1


@pytest.mark.asyncio
async def test_close_closes_http_client() -> None:
    """close should close the HTTP client."""
    client = GammaClient()

    with patch.object(client._http, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_get_markets_with_custom_params() -> None:
    """get_markets should pass pagination and filter params."""
    client = GammaClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await client.get_markets(limit=50, offset=10, active=False)

    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert call_args[0][0] == "/markets"
    params = call_args[1]["params"]
    assert params["limit"] == 50
    assert params["offset"] == 10
    assert "active" not in params  # active=False means don't filter


@pytest.mark.asyncio
async def test_get_markets_raises_api_error_on_http_error() -> None:
    """get_markets should raise PolymarketAPIError on HTTP errors."""
    import httpx

    from polymind.data.polymarket.exceptions import PolymarketAPIError

    client = GammaClient()

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(PolymarketAPIError) as exc_info:
            await client.get_markets()

        assert "Failed to fetch markets" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_market_raises_api_error_on_http_error() -> None:
    """get_market should raise PolymarketAPIError on HTTP errors."""
    import httpx

    from polymind.data.polymarket.exceptions import PolymarketAPIError

    client = GammaClient()

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(PolymarketAPIError) as exc_info:
            await client.get_market("0x123")

        assert "Failed to fetch market" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_events_raises_api_error_on_http_error() -> None:
    """get_events should raise PolymarketAPIError on HTTP errors."""
    import httpx

    from polymind.data.polymarket.exceptions import PolymarketAPIError

    client = GammaClient()

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(PolymarketAPIError) as exc_info:
            await client.get_events()

        assert "Failed to fetch events" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_markets_raises_api_error_on_http_error() -> None:
    """search_markets should raise PolymarketAPIError on HTTP errors."""
    import httpx

    from polymind.data.polymarket.exceptions import PolymarketAPIError

    client = GammaClient()

    with patch.object(client._http, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(PolymarketAPIError) as exc_info:
            await client.search_markets("bitcoin")

        assert "Failed to search markets" in str(exc_info.value)
