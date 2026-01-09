"""Polymarket Gamma API client for market metadata."""

from typing import Any

import httpx

from polymind.data.polymarket.exceptions import PolymarketAPIError
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class GammaClient:
    """Client for Polymarket Gamma API (market discovery and metadata)."""

    def __init__(self, base_url: str = "https://gamma-api.polymarket.com") -> None:
        """Initialize Gamma API client.

        Args:
            base_url: Base URL for Gamma API.
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

    async def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True,
    ) -> list[dict[str, Any]]:
        """Get markets from Gamma API.

        Args:
            limit: Maximum number of markets to return.
            offset: Offset for pagination.
            active: Only return active markets.

        Returns:
            List of market dictionaries.
        """
        try:
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            if active:
                params["active"] = "true"

            response = await self._http.get("/markets", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch markets: {}", str(e))
            raise PolymarketAPIError(f"Failed to fetch markets: {e}") from e

    async def get_market(self, condition_id: str) -> dict[str, Any] | None:
        """Get a specific market by condition ID.

        Args:
            condition_id: The market's condition ID.

        Returns:
            Market dictionary or None if not found.
        """
        try:
            response = await self._http.get(f"/markets/{condition_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch market {}: {}", condition_id, str(e))
            raise PolymarketAPIError(f"Failed to fetch market {condition_id}: {e}") from e

    async def get_market_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Get a market by its slug.

        Args:
            slug: The market's URL slug.

        Returns:
            Market dictionary or None if not found.
        """
        try:
            response = await self._http.get(f"/markets/slug/{slug}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch market by slug {}: {}", slug, str(e))
            raise PolymarketAPIError(f"Failed to fetch market by slug {slug}: {e}") from e

    async def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True,
    ) -> list[dict[str, Any]]:
        """Get events (groups of related markets).

        Args:
            limit: Maximum number of events to return.
            offset: Offset for pagination.
            active: Only return active events.

        Returns:
            List of event dictionaries.
        """
        try:
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            if active:
                params["active"] = "true"

            response = await self._http.get("/events", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch events: {}", str(e))
            raise PolymarketAPIError(f"Failed to fetch events: {e}") from e

    async def search_markets(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search markets by query string.

        Args:
            query: Search query.
            limit: Maximum results to return.

        Returns:
            List of matching market dictionaries.
        """
        try:
            params: dict[str, Any] = {"query": query, "limit": limit}
            response = await self._http.get("/markets", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to search markets: {}", str(e))
            raise PolymarketAPIError(f"Failed to search markets: {e}") from e
