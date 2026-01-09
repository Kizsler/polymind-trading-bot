"""Paper trading execution engine for simulated trades."""

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from polymind.core.brain.decision import AIDecision
from polymind.data.models import TradeSignal

logger = logging.getLogger(__name__)


class CacheProtocol(Protocol):
    """Protocol for cache dependency injection in paper executor."""

    async def update_open_exposure(self, delta: float) -> float:
        """Update open exposure atomically.

        Args:
            delta: Amount to add to current exposure (positive or negative)

        Returns:
            Updated exposure value
        """
        ...


@dataclass
class ExecutionResult:
    """Result of a trade execution attempt.

    Contains the outcome of executing a trade, whether simulated (paper)
    or live, including execution price and size details.
    """

    success: bool
    executed_size: float
    executed_price: float
    paper_mode: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize ExecutionResult to dictionary.

        Returns:
            Dictionary representation of the execution result
        """
        return {
            "success": self.success,
            "executed_size": self.executed_size,
            "executed_price": self.executed_price,
            "paper_mode": self.paper_mode,
            "message": self.message,
        }


class PaperExecutor:
    """Paper trading executor that simulates trade execution.

    Simulates trades without placing real orders, tracking exposure
    via the cache layer for risk management purposes.
    """

    def __init__(self, cache: CacheProtocol) -> None:
        """Initialize paper executor with cache for exposure tracking.

        Args:
            cache: Cache instance for updating exposure state
        """
        self.cache = cache

    async def execute(
        self, signal: TradeSignal, decision: AIDecision
    ) -> ExecutionResult:
        """Execute a paper trade based on signal and AI decision.

        Args:
            signal: The trade signal to execute
            decision: The AI decision containing execution parameters

        Returns:
            ExecutionResult indicating success/failure and execution details
        """
        # Reject if AI decision is not to execute
        if not decision.execute:
            logger.info(
                "Paper trade rejected: decision.execute=False, reason=%s",
                decision.reasoning,
            )
            return ExecutionResult(
                success=False,
                executed_size=0.0,
                executed_price=0.0,
                paper_mode=True,
                message=f"Trade rejected: {decision.reasoning}",
            )

        # Simulate trade at signal price with decision size
        executed_size = decision.size
        executed_price = signal.price

        # Update exposure tracking in cache
        await self.cache.update_open_exposure(executed_size)

        logger.info(
            "Paper trade executed: market=%s, side=%s, size=%.4f, price=%.4f",
            signal.market_id,
            signal.side,
            executed_size,
            executed_price,
        )

        return ExecutionResult(
            success=True,
            executed_size=executed_size,
            executed_price=executed_price,
            paper_mode=True,
            message=(
                f"Paper trade executed: {signal.side} {executed_size:.4f} "
                f"@ {executed_price:.4f}"
            ),
        )
