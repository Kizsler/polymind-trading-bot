"""Tests for arbitrage detector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.intelligence.arbitrage import (
    ArbitrageDetector,
    ArbitrageOpportunity,
)
from polymind.core.intelligence.normalizer import (
    MarketMapping,
    NormalizedMarket,
)


class TestArbitrageDetector:
    """Tests for ArbitrageDetector."""

    @pytest.fixture
    def detector(self) -> ArbitrageDetector:
        """Create detector with default config."""
        return ArbitrageDetector(
            min_spread=0.03,  # 3% minimum spread
            min_volume=1000,  # $1000 minimum volume
        )

    def test_calculate_spread(self, detector: ArbitrageDetector) -> None:
        """Test spread calculation."""
        spread = detector.calculate_spread(
            poly_price=0.65,
            kalshi_price=0.60,
        )
        assert spread == pytest.approx(0.05, rel=0.01)

    def test_calculate_spread_negative(self, detector: ArbitrageDetector) -> None:
        """Test negative spread (Kalshi higher)."""
        spread = detector.calculate_spread(
            poly_price=0.55,
            kalshi_price=0.60,
        )
        assert spread == pytest.approx(-0.05, rel=0.01)

    def test_estimate_profit_basic(self, detector: ArbitrageDetector) -> None:
        """Test basic profit estimation."""
        # 5% spread, $1000 size, no fees
        profit = detector.estimate_profit(
            spread=0.05,
            size=1000,
            poly_fee=0.0,
            kalshi_fee=0.0,
        )
        assert profit == pytest.approx(50.0, rel=0.01)

    def test_estimate_profit_with_fees(self, detector: ArbitrageDetector) -> None:
        """Test profit estimation with fees."""
        # 5% spread, $1000 size, 2% fees each side
        profit = detector.estimate_profit(
            spread=0.05,
            size=1000,
            poly_fee=0.02,
            kalshi_fee=0.02,
        )
        # 5% of 1000 = 50, minus 4% fees (40) = 10
        assert profit == pytest.approx(10.0, rel=0.01)

    def test_estimate_profit_negative(self, detector: ArbitrageDetector) -> None:
        """Test profit estimation with fees exceeding spread."""
        profit = detector.estimate_profit(
            spread=0.03,
            size=1000,
            poly_fee=0.02,
            kalshi_fee=0.02,
        )
        # 3% of 1000 = 30, minus 4% fees (40) = -10
        assert profit == pytest.approx(-10.0, rel=0.01)

    def test_is_opportunity_valid(self, detector: ArbitrageDetector) -> None:
        """Test opportunity validation."""
        # Good opportunity: 5% spread, $5000 volume
        assert detector.is_opportunity_valid(spread=0.05, volume=5000) is True

        # Low spread
        assert detector.is_opportunity_valid(spread=0.02, volume=5000) is False

        # Low volume
        assert detector.is_opportunity_valid(spread=0.05, volume=500) is False

    @pytest.mark.asyncio
    async def test_detect_opportunities(self, detector: ArbitrageDetector) -> None:
        """Test detecting arbitrage opportunities."""
        mock_normalizer = MagicMock()
        mock_normalizer.find_equivalent_markets = AsyncMock(
            return_value=[
                MarketMapping(
                    polymarket_id="poly_btc",
                    kalshi_id="BTCUSD-100K",
                    description="BTC 100k",
                )
            ]
        )
        mock_normalizer.get_cross_platform_prices = AsyncMock(
            return_value={
                "polymarket": NormalizedMarket(
                    platform="polymarket",
                    market_id="poly_btc",
                    title="BTC 100k",
                    probability=0.65,
                    volume=10000,
                ),
                "kalshi": NormalizedMarket(
                    platform="kalshi",
                    market_id="BTCUSD-100K",
                    title="BTC 100k",
                    probability=0.60,
                    volume=5000,
                ),
            }
        )
        mock_normalizer.calculate_spread = MagicMock(return_value=0.05)

        detector.normalizer = mock_normalizer

        opportunities = await detector.detect_opportunities(["poly_btc"])

        assert len(opportunities) == 1
        assert opportunities[0].spread == pytest.approx(0.05, rel=0.01)
        assert opportunities[0].direction == "sell_poly_buy_kalshi"

    @pytest.mark.asyncio
    async def test_detect_opportunities_reverse_direction(
        self, detector: ArbitrageDetector
    ) -> None:
        """Test detecting reverse arbitrage (Kalshi higher)."""
        mock_normalizer = MagicMock()
        mock_normalizer.find_equivalent_markets = AsyncMock(
            return_value=[
                MarketMapping(
                    polymarket_id="poly_btc",
                    kalshi_id="BTCUSD-100K",
                    description="BTC 100k",
                )
            ]
        )
        mock_normalizer.get_cross_platform_prices = AsyncMock(
            return_value={
                "polymarket": NormalizedMarket(
                    platform="polymarket",
                    market_id="poly_btc",
                    title="BTC 100k",
                    probability=0.55,
                    volume=10000,
                ),
                "kalshi": NormalizedMarket(
                    platform="kalshi",
                    market_id="BTCUSD-100K",
                    title="BTC 100k",
                    probability=0.60,
                    volume=5000,
                ),
            }
        )
        mock_normalizer.calculate_spread = MagicMock(return_value=-0.05)

        detector.normalizer = mock_normalizer

        opportunities = await detector.detect_opportunities(["poly_btc"])

        assert len(opportunities) == 1
        assert opportunities[0].direction == "buy_poly_sell_kalshi"

    def test_arbitrage_opportunity_dataclass(self) -> None:
        """Test ArbitrageOpportunity dataclass."""
        opp = ArbitrageOpportunity(
            polymarket_id="poly_btc",
            kalshi_id="BTCUSD-100K",
            description="BTC 100k",
            poly_price=0.65,
            kalshi_price=0.60,
            spread=0.05,
            direction="sell_poly_buy_kalshi",
            estimated_profit=50.0,
        )

        assert opp.spread == 0.05
        assert opp.direction == "sell_poly_buy_kalshi"
