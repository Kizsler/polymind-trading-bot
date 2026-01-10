"""Kalshi API client for prediction market data."""

import base64
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from polymind.utils.logging import get_logger

logger = get_logger(__name__)

KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"


@dataclass
class KalshiMarket:
    """Kalshi market data.

    Attributes:
        ticker: Market ticker (e.g., "BTCUSD-25JAN-100000").
        title: Human-readable title.
        yes_price: Current YES contract price (0-1).
        no_price: Current NO contract price (0-1).
        volume: Trading volume.
        category: Market category.
    """

    ticker: str
    title: str
    yes_price: float
    no_price: float
    volume: int
    category: str

    @property
    def spread(self) -> float:
        """Calculate the bid-ask spread.

        Returns:
            Spread as deviation from 1.0.
            Positive = prices sum to more than 1 (market maker edge).
            Negative = prices sum to less than 1 (arbitrage opportunity).
        """
        return (self.yes_price + self.no_price) - 1.0


@dataclass
class KalshiClient:
    """Client for Kalshi prediction market API.

    Requires RSA signature authentication using API key and private key.

    Attributes:
        api_key: API key ID for authenticated requests.
        private_key_path: Path to RSA private key PEM file.
        base_url: API base URL.
    """

    api_key: str | None = None
    private_key_path: str | None = None
    base_url: str = field(default=KALSHI_API_BASE)
    _client: httpx.AsyncClient | None = field(default=None, repr=False)
    _private_key: Any = field(default=None, repr=False)

    def _load_private_key(self) -> Any:
        """Load RSA private key from PEM file."""
        if self._private_key is not None:
            return self._private_key

        if not self.private_key_path:
            raise ValueError("private_key_path is required for Kalshi authentication")

        key_path = Path(self.private_key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"Private key not found: {key_path}")

        with open(key_path, "rb") as f:
            self._private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
            )
        return self._private_key

    def _sign_pss_text(self, text: str) -> str:
        """Sign text using RSA-PSS and return base64 encoded signature."""
        private_key = self._load_private_key()
        message = text.encode("utf-8")
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _get_auth_headers(self, method: str, path: str) -> dict[str, str]:
        """Generate authentication headers for API request."""
        if not self.api_key:
            return {}

        timestamp_ms = str(int(time.time() * 1000))
        # Strip query params for signing and add API prefix
        path_without_query = path.split("?")[0]
        full_path = f"/trade-api/v2{path_without_query}"
        msg_string = timestamp_ms + method.upper() + full_path

        signature = self._sign_pss_text(msg_string)

        return {
            "KALSHI-ACCESS-KEY": self.api_key,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make API request.

        Args:
            method: HTTP method.
            path: API path.
            params: Query parameters.
            json_data: JSON body data.

        Returns:
            Response JSON.
        """
        client = await self._get_client()

        # Build full path with query string for signing
        full_path = path
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            full_path = f"{path}?{query_string}"

        auth_headers = self._get_auth_headers(method, full_path)

        response = await client.request(
            method=method,
            url=path,
            params=params,
            json=json_data,
            headers=auth_headers,
        )
        response.raise_for_status()

        return response.json()

    async def get_markets(
        self,
        limit: int = 100,
        status: str = "open",
    ) -> list[KalshiMarket]:
        """Get list of markets.

        Args:
            limit: Maximum number of markets to return.
            status: Market status filter ("open", "closed", etc.).

        Returns:
            List of KalshiMarket objects.
        """
        data = await self._request(
            "GET",
            "/markets",
            params={"limit": limit, "status": status},
        )

        markets = []
        for m in data.get("markets", []):
            markets.append(
                KalshiMarket(
                    ticker=m.get("ticker", ""),
                    title=m.get("title", ""),
                    yes_price=m.get("yes_price", 0.5),
                    no_price=m.get("no_price", 0.5),
                    volume=m.get("volume", 0),
                    category=m.get("category", ""),
                )
            )

        logger.info("Fetched {} markets from Kalshi", len(markets))
        return markets

    async def get_market(self, ticker: str) -> KalshiMarket | None:
        """Get a single market by ticker.

        Args:
            ticker: Market ticker.

        Returns:
            KalshiMarket or None if not found.
        """
        try:
            data = await self._request("GET", f"/markets/{ticker}")
            m = data.get("market", {})

            return KalshiMarket(
                ticker=m.get("ticker", ticker),
                title=m.get("title", ""),
                yes_price=m.get("yes_price", 0.5),
                no_price=m.get("no_price", 0.5),
                volume=m.get("volume", 0),
                category=m.get("category", ""),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_orderbook(self, ticker: str) -> dict[str, list[dict[str, Any]]]:
        """Get orderbook for a market.

        Args:
            ticker: Market ticker.

        Returns:
            Dict with 'yes' and 'no' lists of price levels.
        """
        data = await self._request("GET", f"/markets/{ticker}/orderbook")

        return data.get("orderbook", {"yes": [], "no": []})

    async def search_markets(self, query: str) -> list[KalshiMarket]:
        """Search markets by query string.

        Args:
            query: Search query.

        Returns:
            List of matching KalshiMarket objects.
        """
        data = await self._request(
            "GET",
            "/markets",
            params={"status": "open", "series_ticker": query},
        )

        markets = []
        for m in data.get("markets", []):
            markets.append(
                KalshiMarket(
                    ticker=m.get("ticker", ""),
                    title=m.get("title", ""),
                    yes_price=m.get("yes_price", 0.5),
                    no_price=m.get("no_price", 0.5),
                    volume=m.get("volume", 0),
                    category=m.get("category", ""),
                )
            )

        logger.info("Found {} markets for query '{}'", len(markets), query)
        return markets
