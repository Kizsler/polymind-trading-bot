"""Market analysis and quality scoring."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MarketQuality:
    """Quality scores for a market.

    Attributes:
        liquidity_score: How deep the orderbook is (0-1).
        spread_score: How tight the spread is (0-1).
        volatility_score: How stable prices are (0-1).
        time_decay_score: Time until resolution factor (0-1).
    """

    liquidity_score: float = 0.0
    spread_score: float = 0.0
    volatility_score: float = 0.5
    time_decay_score: float = 0.0

    @property
    def overall_score(self) -> float:
        """Calculate weighted average quality score."""
        return (
            self.liquidity_score * 0.3
            + self.spread_score * 0.3
            + self.volatility_score * 0.2
            + self.time_decay_score * 0.2
        )


@dataclass
class MarketAnalyzer:
    """Analyzes market quality for trading decisions.

    Attributes:
        min_liquidity: Minimum total liquidity for max score.
        max_spread_percent: Maximum spread for good score.
        max_volatility: Maximum price variance for good score.
        min_hours_to_resolution: Minimum hours for highest decay score.
    """

    min_liquidity: float = 10000.0
    max_spread_percent: float = 0.05
    max_volatility: float = 0.3
    min_hours_to_resolution: float = 24.0

    def calculate_liquidity_score(self, orderbook: dict[str, Any]) -> float:
        """Calculate liquidity score from orderbook depth.

        Args:
            orderbook: Dict with 'bids' and 'asks' lists.

        Returns:
            Score between 0 and 1.
        """
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids or not asks:
            return 0.0

        total_bid_size = sum(level.get("size", 0) for level in bids)
        total_ask_size = sum(level.get("size", 0) for level in asks)
        total_liquidity = total_bid_size + total_ask_size

        # Normalize: min_liquidity = 1.0 score
        score = min(total_liquidity / self.min_liquidity, 1.0)
        return score

    def calculate_spread_score(self, orderbook: dict[str, Any]) -> float:
        """Calculate spread score from best bid/ask.

        Args:
            orderbook: Dict with 'bids' and 'asks' lists.

        Returns:
            Score between 0 and 1.
        """
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids or not asks:
            return 0.0

        best_bid = max(level.get("price", 0) for level in bids)
        best_ask = min(level.get("price", float("inf")) for level in asks)

        if best_bid <= 0 or best_ask <= best_bid:
            return 0.0

        mid_price = (best_bid + best_ask) / 2
        spread_percent = (best_ask - best_bid) / mid_price

        # Lower spread = higher score
        # 0% spread = 1.0, max_spread_percent = 0.0
        score = max(0, 1 - (spread_percent / self.max_spread_percent))
        return min(score, 1.0)

    def calculate_volatility_score(self, prices: list[float]) -> float:
        """Calculate volatility score from price history.

        Args:
            prices: List of historical prices.

        Returns:
            Score between 0 and 1 (higher = more stable).
        """
        if not prices or len(prices) < 2:
            return 0.5  # Neutral default

        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5

        # Normalize: std_dev of 0 = 1.0, std_dev >= max_volatility = 0.0
        score = max(0, 1 - (std_dev / self.max_volatility))
        return min(score, 1.0)

    def calculate_time_decay_score(self, resolution_time: datetime) -> float:
        """Calculate time decay score based on resolution time.

        Args:
            resolution_time: When the market resolves.

        Returns:
            Score between 0 and 1.
        """
        now = datetime.now(timezone.utc)
        time_remaining = resolution_time - now

        if time_remaining.total_seconds() <= 0:
            return 0.0  # Already resolved or past

        hours_remaining = time_remaining.total_seconds() / 3600

        # More time = higher score
        # >= min_hours_to_resolution = 1.0
        score = min(hours_remaining / self.min_hours_to_resolution, 1.0)
        return score

    def get_quality_score(
        self,
        orderbook: dict[str, Any],
        price_history: list[float],
        resolution_time: datetime,
    ) -> MarketQuality:
        """Calculate overall market quality.

        Args:
            orderbook: Dict with 'bids' and 'asks'.
            price_history: List of historical prices.
            resolution_time: When market resolves.

        Returns:
            MarketQuality with all component scores.
        """
        return MarketQuality(
            liquidity_score=self.calculate_liquidity_score(orderbook),
            spread_score=self.calculate_spread_score(orderbook),
            volatility_score=self.calculate_volatility_score(price_history),
            time_decay_score=self.calculate_time_decay_score(resolution_time),
        )
