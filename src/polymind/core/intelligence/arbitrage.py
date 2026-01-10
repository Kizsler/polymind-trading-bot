"""Arbitrage detection between prediction market platforms."""

from dataclasses import dataclass
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity.

    Attributes:
        polymarket_id: Polymarket market ID.
        kalshi_id: Kalshi ticker.
        description: Market description.
        poly_price: Polymarket probability.
        kalshi_price: Kalshi probability.
        spread: Price spread (absolute difference).
        direction: Trade direction (sell_poly_buy_kalshi or buy_poly_sell_kalshi).
        estimated_profit: Estimated profit per $1000 traded.
    """

    polymarket_id: str
    kalshi_id: str
    description: str
    poly_price: float
    kalshi_price: float
    spread: float
    direction: str
    estimated_profit: float


@dataclass
class ArbitrageDetector:
    """Detects arbitrage opportunities between Polymarket and Kalshi.

    Attributes:
        min_spread: Minimum spread to consider (e.g., 0.03 = 3%).
        min_volume: Minimum volume on both sides.
        normalizer: MarketNormalizer for cross-platform comparison.
        poly_fee: Polymarket fee rate.
        kalshi_fee: Kalshi fee rate.
    """

    min_spread: float = 0.03
    min_volume: float = 1000
    normalizer: Any = None
    poly_fee: float = 0.02
    kalshi_fee: float = 0.01

    def calculate_spread(
        self,
        poly_price: float,
        kalshi_price: float,
    ) -> float:
        """Calculate price spread between platforms.

        Args:
            poly_price: Polymarket probability.
            kalshi_price: Kalshi probability.

        Returns:
            Spread (poly - kalshi).
        """
        return poly_price - kalshi_price

    def estimate_profit(
        self,
        spread: float,
        size: float,
        poly_fee: float = 0.0,
        kalshi_fee: float = 0.0,
    ) -> float:
        """Estimate profit from arbitrage trade.

        Args:
            spread: Price spread (absolute).
            size: Trade size in USD.
            poly_fee: Polymarket fee rate.
            kalshi_fee: Kalshi fee rate.

        Returns:
            Estimated profit in USD.
        """
        gross_profit = abs(spread) * size
        total_fees = (poly_fee + kalshi_fee) * size
        return gross_profit - total_fees

    def is_opportunity_valid(
        self,
        spread: float,
        volume: float,
    ) -> bool:
        """Check if opportunity meets minimum requirements.

        Args:
            spread: Absolute spread value.
            volume: Minimum volume on either side.

        Returns:
            True if opportunity is valid.
        """
        return abs(spread) >= self.min_spread and volume >= self.min_volume

    async def detect_opportunities(
        self,
        polymarket_ids: list[str],
    ) -> list[ArbitrageOpportunity]:
        """Detect arbitrage opportunities for given markets.

        Args:
            polymarket_ids: List of Polymarket market IDs to check.

        Returns:
            List of valid ArbitrageOpportunity objects.
        """
        if self.normalizer is None:
            logger.warning("No normalizer configured, cannot detect opportunities")
            return []

        opportunities = []

        for poly_id in polymarket_ids:
            # Find equivalent Kalshi markets
            mappings = await self.normalizer.find_equivalent_markets(poly_id)

            for mapping in mappings:
                try:
                    # Get prices from both platforms
                    prices = await self.normalizer.get_cross_platform_prices(mapping)

                    if "polymarket" not in prices or "kalshi" not in prices:
                        continue

                    poly_market = prices["polymarket"]
                    kalshi_market = prices["kalshi"]

                    # Calculate spread
                    spread = self.normalizer.calculate_spread(
                        poly_market.probability,
                        kalshi_market.probability,
                    )

                    # Check minimum volume (use smaller of the two)
                    min_volume = min(poly_market.volume, kalshi_market.volume)

                    if not self.is_opportunity_valid(spread, min_volume):
                        continue

                    # Determine direction
                    if spread > 0:
                        direction = "sell_poly_buy_kalshi"
                    else:
                        direction = "buy_poly_sell_kalshi"

                    # Estimate profit for $1000 trade
                    estimated_profit = self.estimate_profit(
                        spread=spread,
                        size=1000,
                        poly_fee=self.poly_fee,
                        kalshi_fee=self.kalshi_fee,
                    )

                    opportunity = ArbitrageOpportunity(
                        polymarket_id=mapping.polymarket_id,
                        kalshi_id=mapping.kalshi_id,
                        description=mapping.description,
                        poly_price=poly_market.probability,
                        kalshi_price=kalshi_market.probability,
                        spread=spread,
                        direction=direction,
                        estimated_profit=estimated_profit,
                    )

                    opportunities.append(opportunity)

                    logger.info(
                        "Found arbitrage opportunity: {} ({:.1%} spread)",
                        mapping.description,
                        abs(spread),
                    )

                except Exception as e:
                    logger.error(
                        "Error checking arbitrage for {}: {}",
                        mapping.polymarket_id,
                        str(e),
                    )

        return opportunities

    async def create_arbitrage_signal(
        self,
        opportunity: ArbitrageOpportunity,
    ) -> dict[str, Any]:
        """Create a trade signal from an arbitrage opportunity.

        Args:
            opportunity: ArbitrageOpportunity to convert.

        Returns:
            Dict representing the trade signal.
        """
        return {
            "type": "ARBITRAGE",
            "source": "arbitrage_detector",
            "polymarket_id": opportunity.polymarket_id,
            "kalshi_id": opportunity.kalshi_id,
            "description": opportunity.description,
            "direction": opportunity.direction,
            "spread": opportunity.spread,
            "estimated_profit": opportunity.estimated_profit,
        }
