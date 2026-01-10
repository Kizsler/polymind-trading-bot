"""Price lag detection for crypto prediction markets."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class PriceDirection(str, Enum):
    """Expected price direction."""

    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


@dataclass
class PriceLagOpportunity:
    """Detected price lag opportunity.

    When Binance prices move significantly but prediction markets
    haven't adjusted yet.

    Attributes:
        market_id: Polymarket market ID.
        market_title: Market title.
        crypto_symbol: Binance symbol (e.g., BTCUSDT).
        binance_price_change: Binance price change as decimal.
        current_probability: Current market probability.
        expected_direction: Expected market movement.
        confidence: Confidence in the opportunity.
    """

    market_id: str
    market_title: str
    crypto_symbol: str
    binance_price_change: float
    current_probability: float
    expected_direction: PriceDirection
    confidence: float


@dataclass
class PriceLagDetector:
    """Detects when prediction markets lag behind crypto prices.

    Monitors Binance prices and compares to crypto-related
    prediction markets on Polymarket.

    Attributes:
        min_price_move: Minimum Binance price move to consider.
        max_market_lag: Maximum allowed market lag.
        binance_feed: Binance WebSocket feed.
        polymarket_api: Polymarket Data API.
    """

    min_price_move: float = 0.02  # 2%
    max_market_lag: float = 0.10  # 10%
    binance_feed: Any = None
    polymarket_api: Any = None
    _price_cache: dict[str, float] = field(default_factory=dict, repr=False)

    def calculate_price_change(
        self,
        old_price: float,
        new_price: float,
    ) -> float:
        """Calculate percentage price change.

        Args:
            old_price: Previous price.
            new_price: Current price.

        Returns:
            Decimal change (e.g., 0.05 for 5%).
        """
        if old_price == 0:
            return 0.0
        return (new_price - old_price) / old_price

    def determine_expected_direction(
        self,
        price_change: float,
    ) -> PriceDirection:
        """Determine expected market direction from price change.

        Args:
            price_change: Binance price change.

        Returns:
            Expected PriceDirection.
        """
        if price_change >= self.min_price_move:
            return PriceDirection.UP
        elif price_change <= -self.min_price_move:
            return PriceDirection.DOWN
        return PriceDirection.NEUTRAL

    def detect_lag(
        self,
        binance_price_change: float,
        market_probability: float,
        baseline_probability: float,
    ) -> PriceLagOpportunity | None:
        """Detect if market is lagging behind Binance price.

        Args:
            binance_price_change: Recent Binance price change.
            market_probability: Current market probability.
            baseline_probability: Baseline probability before move.

        Returns:
            PriceLagOpportunity if lag detected, None otherwise.
        """
        direction = self.determine_expected_direction(binance_price_change)

        if direction == PriceDirection.NEUTRAL:
            return None

        # Calculate how much the market should have moved
        market_change = market_probability - baseline_probability

        # Check if market is lagging
        if direction == PriceDirection.UP:
            # Market should go up but hasn't significantly
            if market_change < abs(binance_price_change) * 0.5:
                return PriceLagOpportunity(
                    market_id="",  # To be filled by caller
                    market_title="",
                    crypto_symbol="",
                    binance_price_change=binance_price_change,
                    current_probability=market_probability,
                    expected_direction=direction,
                    confidence=self.calculate_confidence(binance_price_change),
                )
        else:
            # Market should go down but hasn't significantly
            if market_change > -abs(binance_price_change) * 0.5:
                return PriceLagOpportunity(
                    market_id="",
                    market_title="",
                    crypto_symbol="",
                    binance_price_change=binance_price_change,
                    current_probability=market_probability,
                    expected_direction=direction,
                    confidence=self.calculate_confidence(binance_price_change),
                )

        return None

    def calculate_confidence(self, price_change: float) -> float:
        """Calculate confidence based on price move magnitude.

        Args:
            price_change: Price change as decimal.

        Returns:
            Confidence score 0-1.
        """
        # Larger moves = higher confidence
        # 2% move = 0.5 confidence, 10% move = 1.0 confidence
        magnitude = abs(price_change)
        confidence = min(magnitude / 0.10, 1.0)  # Cap at 1.0
        return max(confidence, 0.3)  # Floor at 0.3

    async def check_crypto_markets(self) -> list[PriceLagOpportunity]:
        """Check all crypto-related markets for lag.

        Returns:
            List of PriceLagOpportunity objects.
        """
        if self.binance_feed is None or self.polymarket_api is None:
            logger.warning("Binance feed or Polymarket API not configured")
            return []

        opportunities = []

        try:
            # Get crypto-related markets from Polymarket
            markets = await self.polymarket_api.get_crypto_markets()

            for market in markets:
                symbol = market.get("symbol")
                if not symbol:
                    continue

                # Get current and cached Binance price
                price_data = await self.binance_feed.get_price(symbol)
                if not price_data:
                    continue

                current_price = price_data.price
                cached_price = self._price_cache.get(symbol, current_price)

                # Calculate price change
                price_change = self.calculate_price_change(cached_price, current_price)

                # Update cache
                self._price_cache[symbol] = current_price

                # Check for lag
                # Use 0.5 as baseline (neutral) for simplicity
                lag = self.detect_lag(
                    binance_price_change=price_change,
                    market_probability=market.get("price", 0.5),
                    baseline_probability=0.5,
                )

                if lag:
                    lag.market_id = market.get("id", "")
                    lag.market_title = market.get("title", "")
                    lag.crypto_symbol = symbol
                    opportunities.append(lag)

                    logger.info(
                        "Detected price lag: {} ({} moved {:.1%})",
                        lag.market_title,
                        symbol,
                        price_change,
                    )

        except Exception as e:
            logger.error("Error checking crypto markets: {}", str(e))

        return opportunities

    async def create_lag_signal(
        self,
        opportunity: PriceLagOpportunity,
    ) -> dict[str, Any]:
        """Create a trade signal from a lag opportunity.

        Args:
            opportunity: PriceLagOpportunity to convert.

        Returns:
            Dict representing the trade signal.
        """
        # Determine side based on expected direction
        if opportunity.expected_direction == PriceDirection.UP:
            side = "YES"  # Buy YES contracts
        else:
            side = "NO"  # Buy NO contracts (or sell YES)

        return {
            "type": "PRICE_LAG",
            "source": "price_lag_detector",
            "market_id": opportunity.market_id,
            "market_title": opportunity.market_title,
            "crypto_symbol": opportunity.crypto_symbol,
            "side": side,
            "binance_change": opportunity.binance_price_change,
            "current_probability": opportunity.current_probability,
            "confidence": opportunity.confidence,
        }
