"""Live executor for Polymarket CLOB API."""

from dataclasses import dataclass, field
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class LiveExecutorError(Exception):
    """Error in live execution."""

    pass


@dataclass
class LiveExecutor:
    """Executes real trades on Polymarket via CLOB API.

    This executor is dormant until wallet credentials are configured.
    It wraps the Polymarket CLOB client for order submission.

    Attributes:
        api_key: Polymarket API key.
        api_secret: Polymarket API secret.
        api_passphrase: Polymarket API passphrase.
    """

    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    _clob_client: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate credentials and initialize client."""
        if not self.api_key or not self.api_secret:
            raise LiveExecutorError(
                "Live executor requires API credentials. "
                "Set POLYMIND_POLYMARKET_API_KEY and POLYMIND_POLYMARKET_API_SECRET."
            )
        # Client will be lazily initialized when needed
        # For now, we don't import the actual CLOB client to keep deps minimal

    @property
    def is_configured(self) -> bool:
        """Check if executor is properly configured."""
        return bool(self.api_key and self.api_secret)

    async def submit_order(
        self,
        market_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict[str, Any]:
        """Submit order to Polymarket.

        Args:
            market_id: Market/token ID to trade.
            side: 'BUY' or 'SELL'.
            size: Trade size in dollars.
            price: Limit price.

        Returns:
            Order result with order_id, status, filled_size, filled_price.
        """
        logger.info(
            "Submitting live order: market={} side={} size={} price={}",
            market_id,
            side,
            size,
            price,
        )

        # Call CLOB API
        response = await self._clob_client.create_order(
            token_id=market_id,
            side=side.upper(),
            size=size,
            price=price,
        )

        return self._parse_order_response(response)

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get order status from Polymarket.

        Args:
            order_id: External order ID.

        Returns:
            Order status with filled_size and filled_price.
        """
        response = await self._clob_client.get_order(order_id)
        return self._parse_order_response(response)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order on Polymarket.

        Args:
            order_id: External order ID.

        Returns:
            True if cancelled successfully.
        """
        response = await self._clob_client.cancel_order(order_id)
        return response.get("success", False)

    def _parse_order_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse CLOB API response to standard format.

        Args:
            response: Raw CLOB API response.

        Returns:
            Normalized order result.
        """
        clob_status = response.get("status", "").upper()
        matched_amount = float(response.get("matchedAmount", 0))
        average_price = float(response.get("averagePrice", 0))

        # Map CLOB statuses to our statuses
        if clob_status == "MATCHED":
            status = "filled"
        elif clob_status in ("OPEN", "PENDING") and matched_amount > 0:
            status = "partial"
        elif clob_status in ("CANCELLED", "EXPIRED"):
            status = "cancelled"
        elif clob_status in ("REJECTED", "FAILED"):
            status = "failed"
        else:
            status = "pending"

        return {
            "order_id": response.get("orderID", ""),
            "status": status,
            "filled_size": matched_amount,
            "filled_price": average_price if matched_amount > 0 else None,
        }
