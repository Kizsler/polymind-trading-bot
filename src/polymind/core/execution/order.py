"""Order state management for execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OrderStatus(str, Enum):
    """Order lifecycle status."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Order:
    """Represents a trade order through its lifecycle.

    Attributes:
        signal_id: ID of the originating trade signal.
        market_id: Polymarket market ID.
        side: 'BUY' or 'SELL'.
        requested_size: Requested trade size in dollars.
        requested_price: Requested limit price.
        max_attempts: Maximum retry attempts.
    """

    signal_id: str
    market_id: str
    side: str
    requested_size: float
    requested_price: float
    max_attempts: int = 3

    # State fields
    id: str | None = None
    external_id: str | None = None
    status: OrderStatus = OrderStatus.PENDING
    filled_size: float = 0.0
    filled_price: float | None = None
    attempts: int = 0
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def remaining_size(self) -> float:
        """Calculate remaining unfilled size."""
        return self.requested_size - self.filled_size

    @property
    def can_retry(self) -> bool:
        """Check if order is eligible for retry."""
        return (
            self.status == OrderStatus.FAILED
            and self.attempts < self.max_attempts
        )

    def mark_submitted(self, external_id: str) -> None:
        """Mark order as submitted to exchange."""
        self.external_id = external_id
        self.status = OrderStatus.SUBMITTED
        self.attempts += 1
        self.updated_at = datetime.now(timezone.utc)

    def mark_filled(self, filled_size: float, filled_price: float) -> None:
        """Mark order as fully filled."""
        self.filled_size = filled_size
        self.filled_price = filled_price
        self.status = OrderStatus.FILLED
        self.updated_at = datetime.now(timezone.utc)

    def mark_partial(self, filled_size: float, filled_price: float) -> None:
        """Mark order as partially filled."""
        self.filled_size = filled_size
        self.filled_price = filled_price
        self.status = OrderStatus.PARTIAL
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: str) -> None:
        """Mark order as failed."""
        self.failure_reason = reason
        self.status = OrderStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        """Mark order as cancelled."""
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Serialize order to dictionary."""
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "market_id": self.market_id,
            "side": self.side,
            "external_id": self.external_id,
            "status": self.status.value,
            "requested_size": self.requested_size,
            "requested_price": self.requested_price,
            "filled_size": self.filled_size,
            "filled_price": self.filled_price,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
