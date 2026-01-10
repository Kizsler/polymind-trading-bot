"""Risk manager for trade validation and risk controls."""

from dataclasses import replace
from enum import Enum
from typing import Protocol

from polymind.core.brain.decision import AIDecision
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class RiskViolation(Enum):
    """Types of risk violations that can block or modify trades."""

    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"
    EXPOSURE_EXCEEDED = "exposure_exceeded"
    TRADE_SIZE_EXCEEDED = "trade_size_exceeded"
    SLIPPAGE_EXCEEDED = "slippage_exceeded"


class CacheProtocol(Protocol):
    """Protocol for cache dependency injection."""

    async def get_daily_pnl(self) -> float:
        """Get current daily P&L."""
        ...

    async def get_open_exposure(self) -> float:
        """Get current open exposure."""
        ...


class RiskManager:
    """Risk manager that validates and adjusts trading decisions.

    Enforces risk limits including:
    - Maximum daily loss limit
    - Maximum total exposure limit
    - Maximum single trade size limit
    """

    def __init__(
        self,
        cache: CacheProtocol,
        max_daily_loss: float,
        max_total_exposure: float,
        max_single_trade: float,
        max_slippage: float = 0.05,  # 5% default max slippage
    ) -> None:
        """Initialize risk manager with limits.

        Args:
            cache: Cache instance for retrieving risk state
            max_daily_loss: Maximum allowed daily loss (positive number)
            max_total_exposure: Maximum total open exposure allowed
            max_single_trade: Maximum size for a single trade
            max_slippage: Maximum allowed slippage (0.05 = 5%)
        """
        self.cache = cache
        self.max_daily_loss = max_daily_loss
        self.max_total_exposure = max_total_exposure
        self.max_single_trade = max_single_trade
        self.max_slippage = max_slippage

    async def validate(self, decision: AIDecision) -> AIDecision:
        """Validate and potentially adjust a trading decision.

        Risk checks applied in order:
        1. Pass through rejections unchanged
        2. Block if daily loss limit exceeded
        3. Cap trade size at max_single_trade
        4. Reduce size if it would exceed total exposure limit

        Args:
            decision: The AI's trading decision to validate

        Returns:
            The original decision, a modified decision with adjusted size,
            or a rejection decision if risk limits are exceeded
        """
        logger.debug(
            "Starting risk validation: execute={} size={}",
            decision.execute,
            decision.size,
        )

        # Pass through rejections unchanged
        if not decision.execute:
            logger.info("Risk validation passed: decision already rejected")
            return decision

        # Check daily loss limit
        daily_pnl = await self.cache.get_daily_pnl()
        if daily_pnl <= -self.max_daily_loss:
            logger.warning(
                "Risk violation: {} (daily P&L: {:.2f}, limit: -{:.2f})",
                RiskViolation.DAILY_LOSS_EXCEEDED.value,
                daily_pnl,
                self.max_daily_loss,
            )
            return AIDecision.reject(
                f"Trade blocked: {RiskViolation.DAILY_LOSS_EXCEEDED.value} "
                f"(daily P&L: {daily_pnl:.2f}, limit: -{self.max_daily_loss:.2f})"
            )

        # Cap trade size at max_single_trade
        adjusted_size = decision.size
        if adjusted_size > self.max_single_trade:
            logger.warning(
                "Risk violation: {} (requested: {:.4f}, limit: {:.4f})",
                RiskViolation.TRADE_SIZE_EXCEEDED.value,
                adjusted_size,
                self.max_single_trade,
            )
            adjusted_size = self.max_single_trade

        # Check total exposure limit
        current_exposure = await self.cache.get_open_exposure()
        remaining_capacity = self.max_total_exposure - current_exposure

        if remaining_capacity <= 0:
            logger.warning(
                "Risk violation: {} (current exposure: {:.2f}, limit: {:.2f})",
                RiskViolation.EXPOSURE_EXCEEDED.value,
                current_exposure,
                self.max_total_exposure,
            )
            return AIDecision.reject(
                f"Trade blocked: {RiskViolation.EXPOSURE_EXCEEDED.value} "
                f"(current exposure: {current_exposure:.2f}, "
                f"limit: {self.max_total_exposure:.2f})"
            )

        # Reduce size if it would exceed remaining capacity
        if adjusted_size > remaining_capacity:
            logger.warning(
                "Risk adjustment: reducing size from {:.4f} to {:.4f} "
                "(remaining capacity: {:.4f})",
                adjusted_size,
                remaining_capacity,
                remaining_capacity,
            )
            adjusted_size = remaining_capacity

        # Return modified decision if size was adjusted
        if adjusted_size != decision.size:
            logger.info(
                "Risk validation complete: size adjusted from {:.4f} to {:.4f}",
                decision.size,
                adjusted_size,
            )
            return replace(
                decision,
                size=adjusted_size,
                reasoning=f"{decision.reasoning} [Size adjusted by risk manager]",
            )

        logger.info("Risk validation complete: decision approved without changes")
        return decision

    def validate_slippage(
        self, decision: AIDecision, spread: float
    ) -> AIDecision:
        """Validate trade against slippage limits.

        Should be called before the main validate() method.

        Args:
            decision: The AI's trading decision
            spread: Current market spread (0.05 = 5%)

        Returns:
            Original decision if OK, rejection if slippage too high
        """
        if not decision.execute:
            return decision

        if spread > self.max_slippage:
            logger.warning(
                "Risk violation: {} (spread: {:.2%}, limit: {:.2%})",
                RiskViolation.SLIPPAGE_EXCEEDED.value,
                spread,
                self.max_slippage,
            )
            return AIDecision.reject(
                f"Trade blocked: {RiskViolation.SLIPPAGE_EXCEEDED.value} "
                f"(spread: {spread:.2%}, limit: {self.max_slippage:.2%})"
            )

        return decision
