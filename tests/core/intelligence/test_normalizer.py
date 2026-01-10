"""Tests for market normalizer."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.intelligence.normalizer import (
    MarketNormalizer,
    NormalizedMarket,
    MarketMapping,
)


class TestMarketNormalizer:
    """Tests for MarketNormalizer."""

    @pytest.fixture
    def normalizer(self) -> MarketNormalizer:
        """Create normalizer instance."""
        return MarketNormalizer()

    def test_normalize_polymarket_odds(self, normalizer: MarketNormalizer) -> None:
        """Test normalizing Polymarket odds."""
        # Polymarket prices are already 0-1 probability
        result = normalizer.normalize_polymarket_odds(0.65)
        assert result == pytest.approx(0.65, rel=0.01)

    def test_normalize_polymarket_odds_boundary(self, normalizer: MarketNormalizer) -> None:
        """Test boundary values."""
        assert normalizer.normalize_polymarket_odds(0.0) == 0.0
        assert normalizer.normalize_polymarket_odds(1.0) == 1.0

    def test_normalize_kalshi_odds(self, normalizer: MarketNormalizer) -> None:
        """Test normalizing Kalshi odds."""
        # Kalshi prices are in cents (0-100)
        # yes=45 means 45 cents = 0.45 probability
        result = normalizer.normalize_kalshi_odds(yes_price=45, no_price=55)
        assert result == pytest.approx(0.45, rel=0.01)

    def test_normalize_kalshi_odds_with_spread(self, normalizer: MarketNormalizer) -> None:
        """Test Kalshi odds when prices don't sum to 100."""
        # yes=45, no=52 means there's a spread
        # Midpoint: yes probability
        result = normalizer.normalize_kalshi_odds(yes_price=45, no_price=52)
        # Should be 45/97 ≈ 0.464 or similar normalization
        assert 0.4 < result < 0.5

    def test_normalized_market_dataclass(self) -> None:
        """Test NormalizedMarket dataclass."""
        market = NormalizedMarket(
            platform="polymarket",
            market_id="market_123",
            title="Will X happen?",
            probability=0.65,
            volume=50000,
        )

        assert market.platform == "polymarket"
        assert market.probability == 0.65

    def test_market_mapping_dataclass(self) -> None:
        """Test MarketMapping dataclass."""
        mapping = MarketMapping(
            polymarket_id="poly_123",
            kalshi_id="KALSHI-123",
            description="BTC 100k by Jan",
        )

        assert mapping.polymarket_id == "poly_123"
        assert mapping.kalshi_id == "KALSHI-123"

    @pytest.mark.asyncio
    async def test_find_equivalent_markets(self, normalizer: MarketNormalizer) -> None:
        """Test finding equivalent markets across platforms."""
        # Mock the database lookup
        mock_db = MagicMock()
        mock_db.fetch_all = AsyncMock(
            return_value=[
                {
                    "polymarket_id": "poly_btc",
                    "kalshi_id": "BTCUSD-25JAN-100000",
                    "description": "BTC 100k",
                }
            ]
        )
        normalizer.db = mock_db

        mappings = await normalizer.find_equivalent_markets("poly_btc")

        assert len(mappings) == 1
        assert mappings[0].kalshi_id == "BTCUSD-25JAN-100000"

    @pytest.mark.asyncio
    async def test_get_cross_platform_prices(self, normalizer: MarketNormalizer) -> None:
        """Test getting prices from multiple platforms."""
        mock_polymarket = MagicMock()
        mock_polymarket.get_market = AsyncMock(
            return_value={"token_id": "poly_btc", "price": 0.65, "volume": 50000}
        )

        mock_kalshi = MagicMock()
        mock_kalshi.get_market = AsyncMock(
            return_value=MagicMock(
                ticker="BTCUSD-100K",
                title="BTC 100k",
                yes_price=0.60,
                no_price=0.40,
                volume=30000,
            )
        )

        normalizer.polymarket_api = mock_polymarket
        normalizer.kalshi_client = mock_kalshi

        mapping = MarketMapping(
            polymarket_id="poly_btc",
            kalshi_id="BTCUSD-100K",
            description="BTC 100k",
        )

        prices = await normalizer.get_cross_platform_prices(mapping)

        assert "polymarket" in prices
        assert "kalshi" in prices
        assert prices["polymarket"].probability == pytest.approx(0.65, rel=0.01)
        assert prices["kalshi"].probability == pytest.approx(0.60, rel=0.01)

    def test_calculate_spread(self, normalizer: MarketNormalizer) -> None:
        """Test calculating spread between platforms."""
        # Polymarket at 65%, Kalshi at 60%
        spread = normalizer.calculate_spread(poly_prob=0.65, kalshi_prob=0.60)

        assert spread == pytest.approx(0.05, rel=0.01)

    def test_calculate_spread_negative(self, normalizer: MarketNormalizer) -> None:
        """Test negative spread (Kalshi higher)."""
        spread = normalizer.calculate_spread(poly_prob=0.55, kalshi_prob=0.60)

        assert spread == pytest.approx(-0.05, rel=0.01)
