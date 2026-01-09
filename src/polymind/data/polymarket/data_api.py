"""Polymarket Data API client for wallet activity."""

from typing import Any

import httpx

from polymind.data.polymarket.exceptions import PolymarketAPIError
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class DataAPIClient:
    """Client for Polymarket Data API (wallet activity and positions)."""

    def __init__(self, base_url: str = "https://data-api.polymarket.com") -> None:
        """Initialize Data API client.

        Args:
            base_url: Base URL for Data API.
        """
        self.base_url = base_url
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()

    async def get_wallet_trades(
        self,
        wallet: str,
        limit: int = 100,
        since_timestamp: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get trades for a wallet.

        Args:
            wallet: Wallet address.
            limit: Maximum number of trades to return.
            since_timestamp: Only return trades after this Unix timestamp.

        Returns:
            List of trade dictionaries.
        """
        try:
            params: dict[str, Any] = {
                "user": wallet.lower(),
                "limit": limit,
            }
            if since_timestamp:
                params["startTs"] = since_timestamp

            response = await self._http.get("/trades", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch trades for {}: {}", wallet, str(e))
            raise PolymarketAPIError(f"Failed to fetch trades for {wallet}: {e}") from e

    async def get_wallet_positions(
        self,
        wallet: str,
    ) -> list[dict[str, Any]]:
        """Get current positions for a wallet.

        Args:
            wallet: Wallet address.

        Returns:
            List of position dictionaries.
        """
        try:
            params = {"user": wallet.lower()}
            response = await self._http.get("/positions", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch positions for {}: {}", wallet, str(e))
            raise PolymarketAPIError(f"Failed to fetch positions for {wallet}: {e}") from e

    async def get_wallet_activity(
        self,
        wallet: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get recent activity for a wallet.

        Args:
            wallet: Wallet address.
            limit: Maximum number of activity items to return.

        Returns:
            List of activity dictionaries.
        """
        try:
            params = {"user": wallet.lower(), "limit": limit}
            response = await self._http.get("/activity", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch activity for {}: {}", wallet, str(e))
            raise PolymarketAPIError(f"Failed to fetch activity for {wallet}: {e}") from e

    async def get_market_holders(
        self,
        market_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get top holders for a market.

        Args:
            market_id: Market condition ID.
            limit: Maximum number of holders to return.

        Returns:
            List of holder dictionaries with wallet and position size.
        """
        try:
            params = {"market": market_id, "limit": limit}
            response = await self._http.get("/holders", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch holders for {}: {}", market_id, str(e))
            raise PolymarketAPIError(f"Failed to fetch holders for {market_id}: {e}") from e
