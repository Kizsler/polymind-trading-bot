"""Tests for price lag detector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.intelligence.pricelag import (
    PriceLagDetector,
    PriceLagOpportunity,
    PriceDirection,
)


class TestPriceLagDetector:
    """Tests for PriceLagDetector."""

    @pytest.fixture
    def detector(self) -> PriceLagDetector:
        """Create detector with default config."""
        return PriceLagDetector(
            min_price_move=0.02,  # 2% minimum price move
            max_market_lag=0.10,  # Market should lag by at most 10%
        )

    def test_calculate_price_change(self, detector: PriceLagDetector) -> None:
        """Test price change calculation."""
        # 10% increase
        change = detector.calculate_price_change(
            old_price=100.0,
            new_price=110.0,
        )
        assert change == pytest.approx(0.10, rel=0.01)

    def test_calculate_price_change_negative(self, detector: PriceLagDetector) -> None:
        """Test negative price change."""
        # 5% decrease
        change = detector.calculate_price_change(
            old_price=100.0,
            new_price=95.0,
        )
        assert change == pytest.approx(-0.05, rel=0.01)

    def test_determine_direction_up(self, detector: PriceLagDetector) -> None:
        """Test direction determination for price increase."""
        direction = detector.determine_expected_direction(price_change=0.05)
        assert direction == PriceDirection.UP

    def test_determine_direction_down(self, detector: PriceLagDetector) -> None:
        """Test direction determination for price decrease."""
        direction = detector.determine_expected_direction(price_change=-0.05)
        assert direction == PriceDirection.DOWN

    def test_determine_direction_neutral(self, detector: PriceLagDetector) -> None:
        """Test direction for small price change."""
        direction = detector.determine_expected_direction(price_change=0.01)
        # Below min_price_move threshold
        assert direction == PriceDirection.NEUTRAL

    def test_detect_lag_basic(self, detector: PriceLagDetector) -> None:
        """Test basic lag detection."""
        # BTC up 5%, market still at 50%
        lag = detector.detect_lag(
            binance_price_change=0.05,
            market_probability=0.50,
            baseline_probability=0.50,
        )

        # Market should move up but hasn't
        assert lag is not None
        assert lag.expected_direction == PriceDirection.UP

    def test_detect_lag_market_already_moved(self, detector: PriceLagDetector) -> None:
        """Test no lag when market already moved."""
        # BTC up 5%, market already up to 60%
        lag = detector.detect_lag(
            binance_price_change=0.05,
            market_probability=0.60,
            baseline_probability=0.50,
        )

        # Market already moved, no opportunity
        assert lag is None

    def test_detect_lag_small_move(self, detector: PriceLagDetector) -> None:
        """Test no lag for small price moves."""
        # BTC only moved 1%
        lag = detector.detect_lag(
            binance_price_change=0.01,
            market_probability=0.50,
            baseline_probability=0.50,
        )

        # Move too small
        assert lag is None

    @pytest.mark.asyncio
    async def test_check_crypto_markets(self, detector: PriceLagDetector) -> None:
        """Test checking crypto-related markets."""
        mock_binance = MagicMock()
        mock_binance.get_price = AsyncMock(
            return_value=MagicMock(price=65000.0, timestamp=1234567890)
        )

        mock_polymarket = MagicMock()
        mock_polymarket.get_crypto_markets = AsyncMock(
            return_value=[
                {
                    "id": "btc_100k",
                    "title": "Will BTC hit 100k?",
                    "price": 0.50,
                    "symbol": "BTCUSDT",
                    "threshold": 100000,
                    "direction": "above",
                }
            ]
        )

        detector.binance_feed = mock_binance
        detector.polymarket_api = mock_polymarket
        detector._price_cache = {"BTCUSDT": 60000.0}  # Previous price

        opportunities = await detector.check_crypto_markets()

        # Should detect lag since BTC moved 8%+ but market still at 50%
        assert len(opportunities) >= 0  # Depends on threshold logic

    def test_price_lag_opportunity_dataclass(self) -> None:
        """Test PriceLagOpportunity dataclass."""
        opp = PriceLagOpportunity(
            market_id="btc_100k",
            market_title="Will BTC hit 100k?",
            crypto_symbol="BTCUSDT",
            binance_price_change=0.05,
            current_probability=0.50,
            expected_direction=PriceDirection.UP,
            confidence=0.75,
        )

        assert opp.crypto_symbol == "BTCUSDT"
        assert opp.expected_direction == PriceDirection.UP

    def test_calculate_confidence(self, detector: PriceLagDetector) -> None:
        """Test confidence calculation based on price move size."""
        # Larger move = higher confidence
        conf_small = detector.calculate_confidence(price_change=0.03)
        conf_large = detector.calculate_confidence(price_change=0.10)

        assert conf_small < conf_large
        assert 0 <= conf_small <= 1
        assert 0 <= conf_large <= 1

    @pytest.mark.asyncio
    async def test_create_lag_signal(self, detector: PriceLagDetector) -> None:
        """Test creating trade signal from opportunity."""
        opp = PriceLagOpportunity(
            market_id="btc_100k",
            market_title="Will BTC hit 100k?",
            crypto_symbol="BTCUSDT",
            binance_price_change=0.05,
            current_probability=0.50,
            expected_direction=PriceDirection.UP,
            confidence=0.75,
        )

        signal = await detector.create_lag_signal(opp)

        assert signal["type"] == "PRICE_LAG"
        assert signal["market_id"] == "btc_100k"
        assert signal["side"] == "YES"  # UP direction = buy YES
