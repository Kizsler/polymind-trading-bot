"""Paper trading execution engine for simulated trades."""

from dataclasses import dataclass
from typing import Any, Protocol

from polymind.core.brain.decision import AIDecision
from polymind.data.models import TradeAction, TradeSignal
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


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

    async def update_daily_pnl(self, delta: float) -> float:
        """Update daily P&L atomically.

        Args:
            delta: Amount to add to current P&L (positive or negative)

        Returns:
            Updated P&L value
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

        Handles both BUY and SELL actions:
        - BUY: Adds to exposure (costs money to enter position)
        - SELL: Reduces exposure and realizes P&L (exits position)

        Args:
            signal: The trade signal to execute
            decision: The AI decision containing execution parameters

        Returns:
            ExecutionResult indicating success/failure and execution details
        """
        is_sell = signal.action == TradeAction.SELL
        action_str = "SELL" if is_sell else "BUY"

        logger.debug(
            "Starting paper execution: market={} side={} action={} size={}",
            signal.market_id,
            signal.side,
            action_str,
            decision.size,
        )

        # Reject if AI decision is not to execute
        if not decision.execute:
            logger.info(
                "Paper trade rejected: decision.execute=False, reason={}",
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
        # BUY: positive exposure (entering position)
        # SELL: negative exposure (exiting position) and realize P&L
        if is_sell:
            # Selling reduces exposure
            exposure_delta = -executed_size
            await self.cache.update_open_exposure(exposure_delta)

            # Estimate P&L from the sell
            # In prediction markets: P&L = shares * (sell_price - entry_price)
            # Since we don't track entry price, we estimate based on price
            # For simplicity: assume average entry at 0.50, so P&L = size * (price - 0.5)
            # This is a rough estimate - proper tracking would need position management
            estimated_pnl = executed_size * (executed_price - 0.5)
            await self.cache.update_daily_pnl(estimated_pnl)

            logger.info(
                "Paper SELL executed: market={} side={} size={:.4f} price={:.4f} est_pnl={:.2f}",
                signal.market_id,
                signal.side,
                executed_size,
                executed_price,
                estimated_pnl,
            )
        else:
            # Buying increases exposure
            await self.cache.update_open_exposure(executed_size)

            logger.info(
                "Paper BUY executed: market={} side={} size={:.4f} price={:.4f}",
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
                f"Paper trade executed: {action_str} {signal.side} {executed_size:.4f} "
                f"@ {executed_price:.4f}"
            ),
        )
