"""Market normalizer for cross-platform price comparison."""

from dataclasses import dataclass, field
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NormalizedMarket:
    """Normalized market data from any platform.

    Attributes:
        platform: Source platform (polymarket, kalshi).
        market_id: Platform-specific market ID.
        title: Market title/description.
        probability: Normalized probability (0-1).
        volume: Trading volume in USD.
    """

    platform: str
    market_id: str
    title: str
    probability: float
    volume: float


@dataclass
class MarketMapping:
    """Mapping between equivalent markets on different platforms.

    Attributes:
        polymarket_id: Polymarket market ID.
        kalshi_id: Kalshi ticker.
        description: Description of the mapped market.
    """

    polymarket_id: str
    kalshi_id: str
    description: str


@dataclass
class MarketNormalizer:
    """Normalizes market data from different platforms.

    Allows comparing prices between Polymarket, Kalshi, etc.

    Attributes:
        db: Database connection for market mappings.
        polymarket_api: Polymarket Data API client.
        kalshi_client: Kalshi API client.
    """

    db: Any = None
    polymarket_api: Any = None
    kalshi_client: Any = None

    def normalize_polymarket_odds(self, price: float) -> float:
        """Normalize Polymarket price to probability.

        Polymarket prices are already 0-1 probabilities.

        Args:
            price: Polymarket price (0-1).

        Returns:
            Probability (0-1).
        """
        return max(0.0, min(1.0, price))

    def normalize_kalshi_odds(
        self,
        yes_price: float,
        no_price: float,
    ) -> float:
        """Normalize Kalshi prices to probability.

        Kalshi prices can be in cents (0-100) or decimals (0-1).
        Prices may not sum to exactly 100 due to spread.

        Args:
            yes_price: YES contract price.
            no_price: NO contract price.

        Returns:
            YES probability (0-1).
        """
        # Normalize if prices are in cents
        if yes_price > 1 or no_price > 1:
            yes_price = yes_price / 100
            no_price = no_price / 100

        total = yes_price + no_price

        if total == 0:
            return 0.5  # Unknown

        # Normalize to account for spread
        return yes_price / total

    def calculate_spread(
        self,
        poly_prob: float,
        kalshi_prob: float,
    ) -> float:
        """Calculate price spread between platforms.

        Positive spread: Polymarket is higher.
        Negative spread: Kalshi is higher.

        Args:
            poly_prob: Polymarket probability.
            kalshi_prob: Kalshi probability.

        Returns:
            Spread as difference (poly - kalshi).
        """
        return poly_prob - kalshi_prob

    async def find_equivalent_markets(
        self,
        polymarket_id: str,
    ) -> list[MarketMapping]:
        """Find Kalshi markets equivalent to a Polymarket market.

        Args:
            polymarket_id: Polymarket market ID.

        Returns:
            List of MarketMapping objects.
        """
        if self.db is None:
            return []

        rows = await self.db.fetch_all(
            """
            SELECT polymarket_id, kalshi_id, description
            FROM market_mappings
            WHERE polymarket_id = ? AND active = TRUE
            """,
            polymarket_id,
        )

        return [
            MarketMapping(
                polymarket_id=row["polymarket_id"],
                kalshi_id=row["kalshi_id"],
                description=row["description"],
            )
            for row in rows
        ]

    async def get_cross_platform_prices(
        self,
        mapping: MarketMapping,
    ) -> dict[str, NormalizedMarket]:
        """Get normalized prices from both platforms.

        Args:
            mapping: Market mapping.

        Returns:
            Dict with 'polymarket' and 'kalshi' NormalizedMarket entries.
        """
        result = {}

        # Fetch Polymarket data
        if self.polymarket_api is not None:
            try:
                poly_data = await self.polymarket_api.get_market(mapping.polymarket_id)
                if poly_data:
                    result["polymarket"] = NormalizedMarket(
                        platform="polymarket",
                        market_id=mapping.polymarket_id,
                        title=mapping.description,
                        probability=self.normalize_polymarket_odds(
                            poly_data.get("price", 0.5)
                        ),
                        volume=poly_data.get("volume", 0),
                    )
            except Exception as e:
                logger.error("Failed to fetch Polymarket data: {}", str(e))

        # Fetch Kalshi data
        if self.kalshi_client is not None:
            try:
                kalshi_data = await self.kalshi_client.get_market(mapping.kalshi_id)
                if kalshi_data:
                    result["kalshi"] = NormalizedMarket(
                        platform="kalshi",
                        market_id=mapping.kalshi_id,
                        title=kalshi_data.title,
                        probability=self.normalize_kalshi_odds(
                            kalshi_data.yes_price,
                            kalshi_data.no_price,
                        ),
                        volume=kalshi_data.volume,
                    )
            except Exception as e:
                logger.error("Failed to fetch Kalshi data: {}", str(e))

        return result
