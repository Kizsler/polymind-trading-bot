"""Market Data Service for Polymarket."""

from typing import Any

from polymind.data.polymarket.client import PolymarketClient
from polymind.storage.cache import Cache


class MarketDataService:
    """Service for fetching and caching market data."""

    def __init__(
        self,
        client: PolymarketClient | None = None,
        cache: Cache | None = None,
    ) -> None:
        """Initialize market data service.

        Args:
            client: Optional Polymarket client instance
            cache: Optional cache instance for caching prices
        """
        self._client = client
        self._cache = cache

    def get_markets(self) -> list[dict[str, Any]]:
        """Get all markets from client.

        Returns:
            List of market dictionaries
        """
        if self._client is None:
            return []
        return self._client.get_markets()

    def get_market(self, condition_id: str) -> dict[str, Any] | None:
        """Get a specific market by condition ID.

        Args:
            condition_id: The market condition ID

        Returns:
            Market dictionary or None if not found
        """
        if self._client is None:
            return None
        return self._client.get_market(condition_id)

    async def get_price_cached(self, token_id: str) -> float:
        """Get price from cache first, then API.

        Args:
            token_id: The token ID to get price for

        Returns:
            Current price for the token
        """
        # Try cache first
        if self._cache is not None:
            cached_price = await self._cache.get_market_price(token_id)
            if cached_price is not None:
                return cached_price

        # Fall back to API
        price = 0.0
        if self._client is not None:
            price = self._client.get_midpoint(token_id)

        # Cache the result
        if self._cache is not None and price > 0:
            await self._cache.set_market_price(token_id, price)

        return price

    async def get_liquidity(self, token_id: str) -> float:
        """Calculate total liquidity from orderbook.

        Sums (price * size) for all bids and asks.

        Args:
            token_id: The token ID to get liquidity for

        Returns:
            Total liquidity value
        """
        if self._client is None:
            return 0.0

        orderbook = self._client.get_orderbook(token_id)
        total = 0.0

        for bid in orderbook.get("bids", []):
            price = float(bid.get("price", 0))
            size = float(bid.get("size", 0))
            total += price * size

        for ask in orderbook.get("asks", []):
            price = float(ask.get("price", 0))
            size = float(ask.get("size", 0))
            total += price * size

        return total

    async def get_spread(self, token_id: str) -> float:
        """Calculate bid-ask spread.

        Args:
            token_id: The token ID to get spread for

        Returns:
            Spread as best_ask - best_bid, or 0.0 if orderbook is empty
        """
        if self._client is None:
            return 0.0

        orderbook = self._client.get_orderbook(token_id)
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids or not asks:
            return 0.0

        # Best bid is highest price, best ask is lowest price
        best_bid = max(float(bid.get("price", 0)) for bid in bids)
        best_ask = min(float(ask.get("price", float("inf"))) for ask in asks)

        return best_ask - best_bid

    async def get_market_snapshot(self, token_id: str) -> dict[str, float]:
        """Get a snapshot of market data.

        Args:
            token_id: The token ID to get snapshot for

        Returns:
            Dictionary with price, liquidity, and spread
        """
        price = 0.0
        if self._client is not None:
            price = self._client.get_midpoint(token_id)

        liquidity = await self.get_liquidity(token_id)
        spread = await self.get_spread(token_id)

        return {
            "price": price,
            "liquidity": liquidity,
            "spread": spread,
        }
