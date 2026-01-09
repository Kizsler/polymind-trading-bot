"""Polymarket CLOB API client wrapper."""

from typing import Any

from py_clob_client.client import ClobClient

from polymind.config.settings import Settings


class PolymarketClient:
    """Wrapper around Polymarket CLOB client."""

    CLOB_HOST = "https://clob.polymarket.com"
    CHAIN_ID = 137  # Polygon mainnet

    def __init__(
        self,
        private_key: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize client."""
        self.settings = settings or Settings()
        self._private_key = private_key

        # Initialize read-only client
        self._client = ClobClient(
            host=self.CLOB_HOST,
            chain_id=self.CHAIN_ID,
        )

        if private_key:
            self._setup_auth(private_key)

    def _setup_auth(self, private_key: str) -> None:
        """Set up authenticated client."""
        self._client = ClobClient(
            host=self.CLOB_HOST,
            chain_id=self.CHAIN_ID,
            key=private_key,
        )
        creds = self._client.create_or_derive_api_creds()
        self._client.set_api_creds(creds)

    def get_markets(self) -> list[dict[str, Any]]:
        """Get all active markets."""
        return self._client.get_simplified_markets()

    def get_market(self, condition_id: str) -> dict[str, Any] | None:
        """Get a specific market by condition ID."""
        markets = self.get_markets()
        for market in markets:
            if market.get("condition_id") == condition_id:
                return market
        return None

    def get_orderbook(self, token_id: str) -> dict[str, Any]:
        """Get orderbook for a token."""
        return self._client.get_order_book(token_id)

    def get_price(self, token_id: str, side: str = "BUY") -> float:
        """Get current price for a token."""
        price = self._client.get_price(token_id, side)
        return float(price) if price else 0.0

    def get_midpoint(self, token_id: str) -> float:
        """Get midpoint price for a token."""
        mid = self._client.get_midpoint(token_id)
        return float(mid) if mid else 0.0

    def get_last_trade_price(self, token_id: str) -> float:
        """Get last trade price for a token."""
        price = self._client.get_last_trade_price(token_id)
        return float(price) if price else 0.0
