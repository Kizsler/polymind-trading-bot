"""Tests for Market Data Service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.data.polymarket.markets import MarketDataService


@pytest.fixture
def mock_client() -> MagicMock:
    """Create mock Polymarket client."""
    client = MagicMock()
    client.get_markets = MagicMock(
        return_value=[
            {"condition_id": "0x123", "question": "Will BTC hit 100k?"},
            {"condition_id": "0x456", "question": "Will ETH hit 10k?"},
        ]
    )
    client.get_market = MagicMock(
        return_value={"condition_id": "0x123", "question": "Will BTC hit 100k?"}
    )
    client.get_orderbook = MagicMock(
        return_value={
            "bids": [
                {"price": "0.60", "size": "100"},
                {"price": "0.58", "size": "200"},
            ],
            "asks": [
                {"price": "0.65", "size": "150"},
                {"price": "0.67", "size": "250"},
            ],
        }
    )
    client.get_midpoint = MagicMock(return_value=0.625)
    return client


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Create mock cache."""
    cache = AsyncMock()
    cache.get_market_price = AsyncMock(return_value=None)
    cache.set_market_price = AsyncMock(return_value=None)
    return cache


def test_service_can_be_created() -> None:
    """Service should initialize without arguments."""
    service = MarketDataService()
    assert service is not None


def test_service_get_markets(mock_client: MagicMock) -> None:
    """Service should return markets from client."""
    service = MarketDataService(client=mock_client)
    markets = service.get_markets()
    assert len(markets) == 2
    assert markets[0]["condition_id"] == "0x123"
    assert markets[1]["condition_id"] == "0x456"
    mock_client.get_markets.assert_called_once()


def test_service_get_market(mock_client: MagicMock) -> None:
    """Service should return specific market from client."""
    service = MarketDataService(client=mock_client)
    market = service.get_market("0x123")
    assert market is not None
    assert market["condition_id"] == "0x123"
    mock_client.get_market.assert_called_once_with("0x123")


def test_service_get_market_not_found(mock_client: MagicMock) -> None:
    """Service should return None when market not found."""
    mock_client.get_market = MagicMock(return_value=None)
    service = MarketDataService(client=mock_client)
    market = service.get_market("0xNONEXISTENT")
    assert market is None


@pytest.mark.asyncio
async def test_service_get_market_liquidity(mock_client: MagicMock) -> None:
    """Service should calculate liquidity from orderbook."""
    service = MarketDataService(client=mock_client)
    liquidity = await service.get_liquidity("0xtoken123")

    # Expected: sum of (price * size) for all bids and asks
    # Bids: 0.60 * 100 + 0.58 * 200 = 60 + 116 = 176
    # Asks: 0.65 * 150 + 0.67 * 250 = 97.5 + 167.5 = 265
    # Total: 176 + 265 = 441
    assert liquidity == 441.0
    mock_client.get_orderbook.assert_called_once_with("0xtoken123")


@pytest.mark.asyncio
async def test_service_get_spread(mock_client: MagicMock) -> None:
    """Service should calculate bid-ask spread (best_ask - best_bid)."""
    service = MarketDataService(client=mock_client)
    spread = await service.get_spread("0xtoken123")

    # Best bid: 0.60, Best ask: 0.65
    # Spread: 0.65 - 0.60 = 0.05
    assert spread == pytest.approx(0.05, rel=1e-9)
    mock_client.get_orderbook.assert_called_once_with("0xtoken123")


@pytest.mark.asyncio
async def test_service_get_spread_empty_orderbook(mock_client: MagicMock) -> None:
    """Service should return 0 spread for empty orderbook."""
    mock_client.get_orderbook = MagicMock(return_value={"bids": [], "asks": []})
    service = MarketDataService(client=mock_client)
    spread = await service.get_spread("0xtoken123")
    assert spread == 0.0


@pytest.mark.asyncio
async def test_service_caches_prices(
    mock_client: MagicMock, mock_cache: AsyncMock
) -> None:
    """Service should use cache for prices."""
    # First call - cache miss, should call API
    service = MarketDataService(client=mock_client, cache=mock_cache)
    price = await service.get_price_cached("0xtoken123")

    assert price == 0.625
    mock_cache.get_market_price.assert_called_once_with("0xtoken123")
    mock_client.get_midpoint.assert_called_once_with("0xtoken123")
    mock_cache.set_market_price.assert_called_once_with("0xtoken123", 0.625)


@pytest.mark.asyncio
async def test_service_returns_cached_price(
    mock_client: MagicMock, mock_cache: AsyncMock
) -> None:
    """Service should return cached price without calling API."""
    mock_cache.get_market_price = AsyncMock(return_value=0.55)
    service = MarketDataService(client=mock_client, cache=mock_cache)
    price = await service.get_price_cached("0xtoken123")

    assert price == 0.55
    mock_cache.get_market_price.assert_called_once_with("0xtoken123")
    mock_client.get_midpoint.assert_not_called()
    mock_cache.set_market_price.assert_not_called()


@pytest.mark.asyncio
async def test_service_get_market_snapshot(mock_client: MagicMock) -> None:
    """Service should return market snapshot with price, liquidity, spread."""
    service = MarketDataService(client=mock_client)
    snapshot = await service.get_market_snapshot("0xtoken123")

    assert "price" in snapshot
    assert "liquidity" in snapshot
    assert "spread" in snapshot
    assert snapshot["price"] == 0.625
    assert snapshot["liquidity"] == 441.0
    assert snapshot["spread"] == pytest.approx(0.05, rel=1e-9)


@pytest.mark.asyncio
async def test_service_get_liquidity_empty_orderbook(mock_client: MagicMock) -> None:
    """Service should return 0 liquidity for empty orderbook."""
    mock_client.get_orderbook = MagicMock(return_value={"bids": [], "asks": []})
    service = MarketDataService(client=mock_client)
    liquidity = await service.get_liquidity("0xtoken123")
    assert liquidity == 0.0
