"""Trade signal data models."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class SignalSource(Enum):
    """Source of a trade signal."""

    CLOB = "clob"
    CHAIN = "chain"
    ARBITRAGE = "arbitrage"


class TradeAction(Enum):
    """Action type for a trade (buy or sell)."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class TradeSignal:
    """Trade signal detected from a tracked wallet.

    Represents a detected trade that can be deduplicated across
    different signal sources (CLOB and blockchain).
    """

    wallet: str
    market_id: str
    token_id: str
    side: str  # YES or NO (the outcome)
    action: TradeAction  # BUY or SELL
    size: float
    price: float
    source: SignalSource
    timestamp: datetime
    tx_hash: str

    @property
    def dedup_id(self) -> str:
        """Generate unique ID for deduplication.

        The ID is based on wallet, market, side, action, size, and timestamp
        rounded to the nearest minute. Source is excluded so the same
        trade detected from both CLOB and chain will have the same ID.
        """
        ts_rounded = self.timestamp.replace(second=0, microsecond=0)
        key = (
            f"{self.wallet}:{self.market_id}:{self.side}:{self.action.value}"
            f":{self.size}:{ts_rounded.isoformat()}"
        )
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TradeSignal":
        """Create TradeSignal from dictionary.

        Args:
            data: Dictionary containing trade signal data.

        Returns:
            TradeSignal instance.
        """
        source_str = data["source"]
        source = SignalSource(source_str)

        # Parse action - default to BUY for backwards compatibility
        action_str = data.get("action", "BUY")
        action = TradeAction(action_str)

        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            wallet=data["wallet"],
            market_id=data["market_id"],
            token_id=data["token_id"],
            side=data["side"],
            action=action,
            size=float(data["size"]),
            price=float(data["price"]),
            source=source,
            timestamp=timestamp,
            tx_hash=data["tx_hash"],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert TradeSignal to dictionary.

        Returns:
            Dictionary representation of the signal.
        """
        return {
            "wallet": self.wallet,
            "market_id": self.market_id,
            "token_id": self.token_id,
            "side": self.side,
            "action": self.action.value,
            "size": self.size,
            "price": self.price,
            "source": self.source.value,
            "timestamp": self.timestamp.isoformat(),
            "tx_hash": self.tx_hash,
        }
