"""Mode-aware executor that switches between paper and live."""

from dataclasses import dataclass
from typing import Any

from polymind.core.brain.decision import AIDecision
from polymind.core.execution.paper import ExecutionResult
from polymind.core.execution.safety import SafetyGuard, LiveModeBlockedError
from polymind.data.models import TradeSignal
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModeAwareExecutor:
    """Executor that switches between paper and live based on mode setting.

    This executor wraps both paper and live executors, selecting the appropriate
    one based on the current mode from cache. It also enforces safety checks
    before live execution.

    Attributes:
        cache: Cache for reading mode and safety state.
        paper_executor: Executor for paper trading.
        live_executor: Executor for live trading (optional).
    """

    cache: Any
    paper_executor: Any
    live_executor: Any = None

    async def execute(
        self,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> ExecutionResult:
        """Execute trade using appropriate executor based on mode.

        Args:
            signal: Trade signal to execute.
            decision: AI decision with execution parameters.

        Returns:
            ExecutionResult from paper or live execution.
        """
        mode = await self.cache.get_mode()

        if mode == "live":
            return await self._execute_live(signal, decision)
        else:
            return await self._execute_paper(signal, decision)

    async def _execute_paper(
        self,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> ExecutionResult:
        """Execute in paper mode."""
        logger.debug("Executing in paper mode")
        return await self.paper_executor.execute(signal, decision)

    async def _execute_live(
        self,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> ExecutionResult:
        """Execute in live mode with safety checks.

        Falls back to paper mode if:
        - Live executor not configured
        - Live mode not confirmed
        - Emergency stop active
        """
        # Check if live executor is configured
        if not self.live_executor or not getattr(self.live_executor, "is_configured", False):
            logger.warning("Live executor not configured, falling back to paper mode")
            return await self._execute_paper(signal, decision)

        # Check if live mode is confirmed
        live_confirmed = await self.cache.get("live_confirmed")
        if not live_confirmed:
            logger.warning("Live mode not confirmed, falling back to paper mode")
            return await self._execute_paper(signal, decision)

        # Check emergency stop
        emergency_stop = await self.cache.get("emergency_stop")
        if emergency_stop and emergency_stop.get("active"):
            reason = emergency_stop.get("reason", "Unknown")
            logger.warning("Emergency stop active: {}", reason)
            return ExecutionResult(
                success=False,
                executed_size=0.0,
                executed_price=0.0,
                paper_mode=False,
                message=f"Execution blocked by emergency stop: {reason}",
            )

        # Execute live trade
        logger.info(
            "Executing LIVE trade: market={} side={} size={}",
            signal.market_id,
            signal.side,
            decision.size,
        )

        try:
            result = await self.live_executor.submit_order(
                market_id=signal.market_id,
                side=signal.side,
                size=decision.size,
                price=decision.size / 100,  # Placeholder price calculation
            )

            return ExecutionResult(
                success=result["status"] in ("filled", "partial"),
                executed_size=result.get("filled_size", 0.0),
                executed_price=result.get("filled_price", 0.0),
                paper_mode=False,
                message=f"Live trade {result['status']}",
            )
        except Exception as e:
            logger.error("Live execution failed: {}", str(e))
            return ExecutionResult(
                success=False,
                executed_size=0.0,
                executed_price=0.0,
                paper_mode=False,
                message=f"Live execution failed: {str(e)}",
            )
