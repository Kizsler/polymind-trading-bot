"""Tests for Binance WebSocket feed."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from polymind.data.binance.feed import BinanceFeed, PriceUpdate


class TestBinanceFeed:
    """Tests for BinanceFeed."""

    @pytest.fixture
    def feed(self) -> BinanceFeed:
        """Create feed instance."""
        return BinanceFeed()

    def test_feed_creates_with_defaults(self, feed: BinanceFeed) -> None:
        """Test feed creates with default configuration."""
        assert feed.base_url == "wss://stream.binance.com:9443"
        assert len(feed._prices) == 0

    def test_feed_initial_state(self, feed: BinanceFeed) -> None:
        """Test feed initial state."""
        assert not feed.is_connected
        assert len(feed._subscriptions) == 0

    @pytest.mark.asyncio
    async def test_get_price_no_data(self, feed: BinanceFeed) -> None:
        """Test getting price when no data available."""
        price = await feed.get_price("BTCUSDT")
        assert price is None

    @pytest.mark.asyncio
    async def test_get_price_with_cached_data(self, feed: BinanceFeed) -> None:
        """Test getting price with cached data."""
        feed._prices["BTCUSDT"] = PriceUpdate(
            symbol="BTCUSDT",
            price=65000.0,
            timestamp=1234567890,
        )

        price = await feed.get_price("BTCUSDT")

        assert price is not None
        assert price.symbol == "BTCUSDT"
        assert price.price == 65000.0

    @pytest.mark.asyncio
    async def test_subscribe_adds_callback(self, feed: BinanceFeed) -> None:
        """Test subscribing adds callback."""
        callback = AsyncMock()

        await feed.subscribe("BTCUSDT", callback)

        assert "BTCUSDT" in feed._subscriptions
        assert callback in feed._subscriptions["BTCUSDT"]

    @pytest.mark.asyncio
    async def test_subscribe_multiple_callbacks(self, feed: BinanceFeed) -> None:
        """Test multiple callbacks for same symbol."""
        callback1 = AsyncMock()
        callback2 = AsyncMock()

        await feed.subscribe("BTCUSDT", callback1)
        await feed.subscribe("BTCUSDT", callback2)

        assert len(feed._subscriptions["BTCUSDT"]) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_callback(self, feed: BinanceFeed) -> None:
        """Test unsubscribing removes callback."""
        callback = AsyncMock()
        await feed.subscribe("BTCUSDT", callback)

        await feed.unsubscribe("BTCUSDT", callback)

        assert callback not in feed._subscriptions.get("BTCUSDT", [])

    @pytest.mark.asyncio
    async def test_process_message_updates_price(self, feed: BinanceFeed) -> None:
        """Test processing message updates price cache."""
        message = {
            "e": "trade",
            "s": "BTCUSDT",
            "p": "65000.00",
            "T": 1234567890000,
        }

        await feed._process_message(message)

        assert "BTCUSDT" in feed._prices
        assert feed._prices["BTCUSDT"].price == 65000.0

    @pytest.mark.asyncio
    async def test_process_message_triggers_callbacks(self, feed: BinanceFeed) -> None:
        """Test processing message triggers subscribed callbacks."""
        callback = AsyncMock()
        await feed.subscribe("BTCUSDT", callback)

        message = {
            "e": "trade",
            "s": "BTCUSDT",
            "p": "65000.00",
            "T": 1234567890000,
        }

        await feed._process_message(message)

        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args.symbol == "BTCUSDT"
        assert call_args.price == 65000.0

    def test_price_update_dataclass(self) -> None:
        """Test PriceUpdate dataclass."""
        update = PriceUpdate(
            symbol="ETHUSDT",
            price=3500.0,
            timestamp=1234567890,
        )

        assert update.symbol == "ETHUSDT"
        assert update.price == 3500.0
        assert update.timestamp == 1234567890

    @pytest.mark.asyncio
    async def test_get_all_prices(self, feed: BinanceFeed) -> None:
        """Test getting all cached prices."""
        feed._prices["BTCUSDT"] = PriceUpdate("BTCUSDT", 65000.0, 1234567890)
        feed._prices["ETHUSDT"] = PriceUpdate("ETHUSDT", 3500.0, 1234567890)

        prices = await feed.get_all_prices()

        assert len(prices) == 2
        assert "BTCUSDT" in prices
        assert "ETHUSDT" in prices
