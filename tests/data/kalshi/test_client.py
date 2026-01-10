"""Tests for Kalshi API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from polymind.data.kalshi.client import KalshiClient, KalshiMarket


class TestKalshiClient:
    """Tests for KalshiClient."""

    @pytest.fixture
    def client(self) -> KalshiClient:
        """Create client without credentials (read-only mode)."""
        return KalshiClient()

    @pytest.fixture
    def authenticated_client(self) -> KalshiClient:
        """Create client with credentials."""
        return KalshiClient(
            api_key="test_key",
            api_secret="test_secret",
        )

    def test_client_creates_without_credentials(self, client: KalshiClient) -> None:
        """Test client can be created without credentials for read-only access."""
        assert client.api_key is None
        assert client.api_secret is None

    def test_client_creates_with_credentials(self, authenticated_client: KalshiClient) -> None:
        """Test client can be created with credentials."""
        assert authenticated_client.api_key == "test_key"
        assert authenticated_client.api_secret == "test_secret"

    @pytest.mark.asyncio
    async def test_get_markets(self, client: KalshiClient) -> None:
        """Test fetching markets."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "markets": [
                    {
                        "ticker": "BTCUSD-25JAN-100000",
                        "title": "Will BTC reach $100k by Jan 2025?",
                        "yes_price": 0.45,
                        "no_price": 0.55,
                        "volume": 50000,
                        "category": "crypto",
                    }
                ]
            }

            markets = await client.get_markets()

            assert len(markets) == 1
            assert markets[0].ticker == "BTCUSD-25JAN-100000"
            assert markets[0].yes_price == 0.45
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_market(self, client: KalshiClient) -> None:
        """Test fetching a single market."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "market": {
                    "ticker": "BTCUSD-25JAN-100000",
                    "title": "Will BTC reach $100k by Jan 2025?",
                    "yes_price": 0.45,
                    "no_price": 0.55,
                    "volume": 50000,
                    "category": "crypto",
                }
            }

            market = await client.get_market("BTCUSD-25JAN-100000")

            assert market is not None
            assert market.ticker == "BTCUSD-25JAN-100000"
            assert market.title == "Will BTC reach $100k by Jan 2025?"

    @pytest.mark.asyncio
    async def test_get_orderbook(self, client: KalshiClient) -> None:
        """Test fetching orderbook."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "orderbook": {
                    "yes": [
                        {"price": 45, "quantity": 1000},
                        {"price": 44, "quantity": 2000},
                    ],
                    "no": [
                        {"price": 55, "quantity": 1000},
                        {"price": 56, "quantity": 1500},
                    ],
                }
            }

            orderbook = await client.get_orderbook("BTCUSD-25JAN-100000")

            assert "yes" in orderbook
            assert "no" in orderbook
            assert len(orderbook["yes"]) == 2
            assert orderbook["yes"][0]["price"] == 45

    @pytest.mark.asyncio
    async def test_search_markets(self, client: KalshiClient) -> None:
        """Test searching markets by query."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "markets": [
                    {
                        "ticker": "BTCUSD-25JAN-100000",
                        "title": "Will BTC reach $100k?",
                        "yes_price": 0.45,
                        "no_price": 0.55,
                        "volume": 50000,
                        "category": "crypto",
                    },
                    {
                        "ticker": "BTCUSD-25JAN-150000",
                        "title": "Will BTC reach $150k?",
                        "yes_price": 0.15,
                        "no_price": 0.85,
                        "volume": 20000,
                        "category": "crypto",
                    },
                ]
            }

            markets = await client.search_markets("BTC")

            assert len(markets) == 2
            assert all("BTC" in m.ticker for m in markets)

    def test_kalshi_market_dataclass(self) -> None:
        """Test KalshiMarket dataclass."""
        market = KalshiMarket(
            ticker="TEST-MARKET",
            title="Test Market",
            yes_price=0.60,
            no_price=0.40,
            volume=1000,
            category="test",
        )

        assert market.ticker == "TEST-MARKET"
        assert market.yes_price == 0.60
        assert market.spread == pytest.approx(0.0)  # 0.60 + 0.40 = 1.0, no spread

    def test_kalshi_market_spread_calculation(self) -> None:
        """Test spread calculation when prices don't sum to 1."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test",
            yes_price=0.45,
            no_price=0.52,
            volume=1000,
            category="test",
        )
        # Spread is how much over 1.0 the combined price is
        # This represents the market maker's edge
        assert market.spread == pytest.approx(-0.03)  # 0.45 + 0.52 = 0.97, -3% under
