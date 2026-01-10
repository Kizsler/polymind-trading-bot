"""Safety guards for trade execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class LiveModeBlockedError(Exception):
    """Raised when live mode execution is blocked."""

    pass


@dataclass
class SafetyGuard:
    """Guards against unsafe execution conditions.

    Provides multiple layers of safety:
    - Credential verification
    - Live mode confirmation
    - Emergency stop
    - First trade warning

    Attributes:
        cache: Cache for persisting safety state.
    """

    cache: Any
    _stopped: bool = field(default=False, repr=False)
    _stop_reason: str | None = field(default=None, repr=False)
    _stop_time: datetime | None = field(default=None, repr=False)

    @property
    def is_stopped(self) -> bool:
        """Check if emergency stop is active."""
        return self._stopped

    async def check_live_mode_allowed(
        self,
        has_credentials: bool,
        live_confirmed: bool,
    ) -> None:
        """Verify all requirements for live mode.

        Args:
            has_credentials: Whether API credentials are configured.
            live_confirmed: Whether user has confirmed live mode.

        Raises:
            LiveModeBlockedError: If any requirement not met.
        """
        if not has_credentials:
            raise LiveModeBlockedError(
                "Live mode requires API credentials. "
                "Configure POLYMIND_POLYMARKET_API_KEY and POLYMIND_POLYMARKET_API_SECRET."
            )

        if not live_confirmed:
            raise LiveModeBlockedError(
                "Live mode requires explicit confirmation. "
                "Set live_mode_confirmed=true in settings."
            )

        await self.check_execution_allowed()

    async def check_execution_allowed(self) -> None:
        """Check if execution is currently allowed.

        Raises:
            LiveModeBlockedError: If emergency stop is active.
        """
        if self._stopped:
            raise LiveModeBlockedError(
                f"Execution blocked by emergency stop: {self._stop_reason}"
            )

    async def activate_emergency_stop(self, reason: str) -> None:
        """Activate emergency stop.

        Args:
            reason: Reason for the stop.
        """
        self._stopped = True
        self._stop_reason = reason
        self._stop_time = datetime.now(timezone.utc)

        logger.warning("EMERGENCY STOP ACTIVATED: {}", reason)

        await self.cache.set(
            "emergency_stop",
            {
                "active": True,
                "reason": reason,
                "time": self._stop_time.isoformat(),
            },
        )

    async def reset_emergency_stop(self) -> None:
        """Reset emergency stop."""
        self._stopped = False
        self._stop_reason = None
        self._stop_time = None

        logger.info("Emergency stop reset")

        await self.cache.set("emergency_stop", {"active": False})

    async def check_first_live_trade(self) -> bool:
        """Check if this is the first live trade.

        Returns:
            True if first trade warning should be shown.
        """
        acknowledged = await self.cache.get("first_live_trade_acknowledged")
        return not acknowledged

    async def acknowledge_first_live_trade(self) -> None:
        """Acknowledge first live trade warning."""
        await self.cache.set("first_live_trade_acknowledged", True)
        logger.info("First live trade warning acknowledged")
