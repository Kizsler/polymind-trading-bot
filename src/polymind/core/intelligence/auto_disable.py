"""Auto-disable logic for underperforming wallets."""

from dataclasses import dataclass

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DisableCheckResult:
    """Result of disable check."""

    should_disable: bool
    reason: str | None = None


@dataclass
class AutoDisableChecker:
    """Checks if wallets should be auto-disabled.

    Attributes:
        min_confidence: Minimum confidence score threshold.
        max_drawdown: Maximum allowed drawdown (negative float, e.g., -0.20).
        inactive_days: Days of inactivity before disable.
    """

    min_confidence: float = 0.3
    max_drawdown: float = -0.20
    inactive_days: int = 30

    async def check_wallet(
        self,
        wallet_address: str,
        confidence_score: float,
        drawdown_7d: float,
        last_trade_days_ago: int,
    ) -> DisableCheckResult:
        """Check if wallet should be disabled.

        Args:
            wallet_address: Wallet address.
            confidence_score: Current confidence score (0-1).
            drawdown_7d: 7-day drawdown as negative float.
            last_trade_days_ago: Days since last trade.

        Returns:
            DisableCheckResult indicating if disable is needed.
        """
        # Check confidence
        if confidence_score < self.min_confidence:
            logger.warning(
                "Wallet {} below confidence threshold: {:.2f} < {:.2f}",
                wallet_address[:10],
                confidence_score,
                self.min_confidence,
            )
            return DisableCheckResult(
                should_disable=True,
                reason=f"Confidence score {confidence_score:.2f} below threshold {self.min_confidence}",
            )

        # Check drawdown
        if drawdown_7d < self.max_drawdown:
            logger.warning(
                "Wallet {} exceeds drawdown limit: {:.1%} < {:.1%}",
                wallet_address[:10],
                drawdown_7d,
                self.max_drawdown,
            )
            return DisableCheckResult(
                should_disable=True,
                reason=f"Drawdown {drawdown_7d:.1%} exceeds limit {self.max_drawdown:.1%}",
            )

        # Check inactivity
        if last_trade_days_ago > self.inactive_days:
            logger.warning(
                "Wallet {} inactive for {} days (limit: {})",
                wallet_address[:10],
                last_trade_days_ago,
                self.inactive_days,
            )
            return DisableCheckResult(
                should_disable=True,
                reason=f"Inactive for {last_trade_days_ago} days",
            )

        return DisableCheckResult(should_disable=False)
