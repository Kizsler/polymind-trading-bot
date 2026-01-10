"""Order execution manager with retry logic."""

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from polymind.core.execution.order import Order, OrderStatus
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class ExecutorProtocol(Protocol):
    """Protocol for order executors."""

    async def submit_order(
        self,
        market_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict[str, Any]:
        """Submit order to exchange."""
        ...

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get order status from exchange."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order on exchange."""
        ...


@dataclass
class OrderManager:
    """Manages order lifecycle with retry logic.

    Attributes:
        cache: Cache for order persistence.
        retry_delay: Base delay between retries in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
    """

    cache: Any
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0

    async def create_order(
        self,
        signal_id: str,
        market_id: str,
        side: str,
        size: float,
        price: float,
        max_attempts: int = 3,
    ) -> Order:
        """Create a new order.

        Args:
            signal_id: ID of originating signal.
            market_id: Market to trade.
            side: 'BUY' or 'SELL'.
            size: Trade size in dollars.
            price: Limit price.
            max_attempts: Maximum retry attempts.

        Returns:
            New Order instance.
        """
        order = Order(
            id=str(uuid.uuid4()),
            signal_id=signal_id,
            market_id=market_id,
            side=side,
            requested_size=size,
            requested_price=price,
            max_attempts=max_attempts,
        )
        await self.save_order(order)
        return order

    async def save_order(self, order: Order) -> None:
        """Persist order to cache."""
        key = f"order:{order.id}"
        await self.cache.set(key, json.dumps(order.to_dict()))

    async def get_order(self, order_id: str) -> Order | None:
        """Load order from cache."""
        key = f"order:{order_id}"
        data = await self.cache.get(key)
        if not data:
            return None
        if isinstance(data, str):
            data = json.loads(data)
        return self._order_from_dict(data)

    def _order_from_dict(self, data: dict[str, Any]) -> Order:
        """Reconstruct order from dictionary."""
        order = Order(
            signal_id=data["signal_id"],
            market_id=data["market_id"],
            side=data["side"],
            requested_size=data["requested_size"],
            requested_price=data["requested_price"],
            max_attempts=data.get("max_attempts", 3),
        )
        order.id = data.get("id")
        order.external_id = data.get("external_id")
        order.status = OrderStatus(data.get("status", "pending"))
        order.filled_size = data.get("filled_size", 0.0)
        order.filled_price = data.get("filled_price")
        order.attempts = data.get("attempts", 0)
        order.failure_reason = data.get("failure_reason")
        return order

    async def execute_with_retry(
        self,
        order: Order,
        executor: ExecutorProtocol,
    ) -> Order:
        """Execute order with retry logic.

        Args:
            order: Order to execute.
            executor: Executor to use for submission.

        Returns:
            Updated order with final status.
        """
        delay = self.retry_delay

        while order.attempts < order.max_attempts:
            try:
                logger.info(
                    "Submitting order {} (attempt {}/{})",
                    order.id,
                    order.attempts + 1,
                    order.max_attempts,
                )

                result = await executor.submit_order(
                    market_id=order.market_id,
                    side=order.side,
                    size=order.remaining_size if order.filled_size > 0 else order.requested_size,
                    price=order.requested_price,
                )

                order.mark_submitted(external_id=result["order_id"])

                # Process result
                status = result.get("status", "")
                if status == "filled":
                    order.mark_filled(
                        filled_size=result["filled_size"],
                        filled_price=result["filled_price"],
                    )
                    logger.info("Order {} filled at {}", order.id, result["filled_price"])
                    break
                elif status == "partial":
                    order.mark_partial(
                        filled_size=result["filled_size"],
                        filled_price=result["filled_price"],
                    )
                    logger.info(
                        "Order {} partially filled: {}/{}",
                        order.id,
                        result["filled_size"],
                        order.requested_size,
                    )
                    break
                else:
                    order.mark_failed(reason=f"Unexpected status: {status}")

            except Exception as e:
                order.attempts += 1  # Increment attempts on failure
                logger.warning("Order {} failed: {}", order.id, str(e))
                order.mark_failed(reason=str(e))

                if order.can_retry:
                    logger.info("Retrying order {} in {}s", order.id, delay)
                    await asyncio.sleep(delay)
                    delay *= self.backoff_multiplier
                    # Reset status to allow retry
                    order.status = OrderStatus.PENDING

        await self.save_order(order)
        return order
