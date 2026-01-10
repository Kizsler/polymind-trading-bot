"""Tests for market analyzer."""

import pytest
from datetime import datetime, timezone, timedelta

from polymind.core.intelligence.market import MarketAnalyzer, MarketQuality


class TestMarketAnalyzer:
    """Tests for MarketAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> MarketAnalyzer:
        """Create analyzer with default config."""
        return MarketAnalyzer()

    def test_calculate_liquidity_score_high(self, analyzer: MarketAnalyzer) -> None:
        """Test liquidity score for deep orderbook."""
        orderbook = {
            "bids": [
                {"price": 0.55, "size": 5000},
                {"price": 0.54, "size": 3000},
                {"price": 0.53, "size": 2000},
            ],
            "asks": [
                {"price": 0.56, "size": 5000},
                {"price": 0.57, "size": 3000},
                {"price": 0.58, "size": 2000},
            ],
        }
        score = analyzer.calculate_liquidity_score(orderbook)
        assert score >= 0.8  # High liquidity

    def test_calculate_liquidity_score_low(self, analyzer: MarketAnalyzer) -> None:
        """Test liquidity score for thin orderbook."""
        orderbook = {
            "bids": [{"price": 0.55, "size": 100}],
            "asks": [{"price": 0.56, "size": 100}],
        }
        score = analyzer.calculate_liquidity_score(orderbook)
        assert score <= 0.3  # Low liquidity

    def test_calculate_liquidity_score_empty(self, analyzer: MarketAnalyzer) -> None:
        """Test liquidity score for empty orderbook."""
        orderbook = {"bids": [], "asks": []}
        score = analyzer.calculate_liquidity_score(orderbook)
        assert score == 0.0

    def test_calculate_spread_score_tight(self, analyzer: MarketAnalyzer) -> None:
        """Test spread score for tight spread."""
        orderbook = {
            "bids": [{"price": 0.55, "size": 1000}],
            "asks": [{"price": 0.56, "size": 1000}],
        }
        score = analyzer.calculate_spread_score(orderbook)
        # 1 cent spread on ~55.5 cent mid = ~1.8% spread
        # With max_spread_percent=5%, score = 1 - (0.018/0.05) ≈ 0.64
        assert score >= 0.6

    def test_calculate_spread_score_wide(self, analyzer: MarketAnalyzer) -> None:
        """Test spread score for wide spread."""
        orderbook = {
            "bids": [{"price": 0.40, "size": 1000}],
            "asks": [{"price": 0.60, "size": 1000}],
        }
        score = analyzer.calculate_spread_score(orderbook)
        # 20 cent spread = 40% = very bad
        assert score <= 0.3

    def test_calculate_spread_score_empty(self, analyzer: MarketAnalyzer) -> None:
        """Test spread score for empty orderbook."""
        orderbook = {"bids": [], "asks": []}
        score = analyzer.calculate_spread_score(orderbook)
        assert score == 0.0

    def test_calculate_volatility_score_stable(self, analyzer: MarketAnalyzer) -> None:
        """Test volatility score for stable prices."""
        prices = [0.50, 0.51, 0.50, 0.49, 0.50]
        score = analyzer.calculate_volatility_score(prices)
        # Low variance = high score
        assert score >= 0.8

    def test_calculate_volatility_score_volatile(self, analyzer: MarketAnalyzer) -> None:
        """Test volatility score for volatile prices."""
        prices = [0.30, 0.70, 0.40, 0.80, 0.20]
        score = analyzer.calculate_volatility_score(prices)
        # High variance = low score
        assert score <= 0.3

    def test_calculate_volatility_score_empty(self, analyzer: MarketAnalyzer) -> None:
        """Test volatility score for empty prices."""
        score = analyzer.calculate_volatility_score([])
        assert score == 0.5  # Neutral default

    def test_calculate_time_decay_score_far(self, analyzer: MarketAnalyzer) -> None:
        """Test time decay for distant resolution."""
        resolution = datetime.now(timezone.utc) + timedelta(days=30)
        score = analyzer.calculate_time_decay_score(resolution)
        # Far resolution = high score
        assert score >= 0.9

    def test_calculate_time_decay_score_near(self, analyzer: MarketAnalyzer) -> None:
        """Test time decay for imminent resolution."""
        resolution = datetime.now(timezone.utc) + timedelta(hours=1)
        score = analyzer.calculate_time_decay_score(resolution)
        # Close resolution = lower score (more risky)
        assert score <= 0.5

    def test_calculate_time_decay_score_past(self, analyzer: MarketAnalyzer) -> None:
        """Test time decay for past resolution."""
        resolution = datetime.now(timezone.utc) - timedelta(hours=1)
        score = analyzer.calculate_time_decay_score(resolution)
        # Past = 0 score
        assert score == 0.0

    def test_get_quality_score(self, analyzer: MarketAnalyzer) -> None:
        """Test combined quality score calculation."""
        orderbook = {
            "bids": [
                {"price": 0.55, "size": 5000},
                {"price": 0.54, "size": 3000},
            ],
            "asks": [
                {"price": 0.56, "size": 5000},
                {"price": 0.57, "size": 3000},
            ],
        }
        prices = [0.55, 0.54, 0.55, 0.56, 0.55]
        resolution = datetime.now(timezone.utc) + timedelta(days=7)

        quality = analyzer.get_quality_score(
            orderbook=orderbook,
            price_history=prices,
            resolution_time=resolution,
        )

        assert isinstance(quality, MarketQuality)
        assert 0.0 <= quality.liquidity_score <= 1.0
        assert 0.0 <= quality.spread_score <= 1.0
        assert 0.0 <= quality.volatility_score <= 1.0
        assert 0.0 <= quality.time_decay_score <= 1.0
        assert 0.0 <= quality.overall_score <= 1.0

    def test_market_quality_overall_weighted(self, analyzer: MarketAnalyzer) -> None:
        """Test that overall score is weighted average."""
        quality = MarketQuality(
            liquidity_score=1.0,
            spread_score=1.0,
            volatility_score=1.0,
            time_decay_score=1.0,
        )
        assert quality.overall_score == 1.0

        quality = MarketQuality(
            liquidity_score=0.0,
            spread_score=0.0,
            volatility_score=0.0,
            time_decay_score=0.0,
        )
        assert quality.overall_score == 0.0
