"""Decision brain orchestrator for coordinating trading decisions."""

from typing import Protocol

from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision
from polymind.core.execution.paper import ExecutionResult
from polymind.data.models import TradeAction, TradeSignal
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class ContextBuilderProtocol(Protocol):
    """Protocol for context builder dependency injection."""

    async def build(self, signal: TradeSignal) -> DecisionContext:
        """Build decision context from a trade signal.

        Args:
            signal: The incoming trade signal

        Returns:
            DecisionContext with all relevant data for decision making
        """
        ...


class ClaudeClientProtocol(Protocol):
    """Protocol for Claude client dependency injection."""

    async def evaluate(self, context: DecisionContext) -> AIDecision:
        """Evaluate a decision context and return an AI decision.

        Args:
            context: DecisionContext containing all relevant data

        Returns:
            AIDecision with execute decision, sizing, and reasoning
        """
        ...


class RiskManagerProtocol(Protocol):
    """Protocol for risk manager dependency injection."""

    async def validate(self, decision: AIDecision) -> AIDecision:
        """Validate and potentially adjust a trading decision.

        Args:
            decision: The AI's trading decision to validate

        Returns:
            The original decision, a modified decision with adjusted size,
            or a rejection decision if risk limits are exceeded
        """
        ...

    def validate_slippage(self, decision: AIDecision, spread: float) -> AIDecision:
        """Validate trade against slippage limits.

        Args:
            decision: The AI's trading decision
            spread: Current market spread (0.05 = 5%)

        Returns:
            Original decision if OK, rejection if slippage too high
        """
        ...


class ExecutorProtocol(Protocol):
    """Protocol for trade executor dependency injection."""

    async def execute(
        self, signal: TradeSignal, decision: AIDecision
    ) -> ExecutionResult:
        """Execute a trade based on signal and AI decision.

        Args:
            signal: The trade signal to execute
            decision: The AI decision containing execution parameters

        Returns:
            ExecutionResult indicating success/failure and execution details
        """
        ...


class CacheProtocol(Protocol):
    """Protocol for cache access."""

    async def get_settings(self) -> dict:
        """Get current settings."""
        ...


class DecisionBrain:
    """Orchestrator for the AI-powered trading decision pipeline.

    Coordinates the flow from signal detection through execution:
    1. Build context from incoming signal
    2. Get AI decision from Claude (or bypass if AI disabled)
    3. Validate decision with risk manager
    4. Execute trade if approved

    Uses dependency injection via Protocol classes for flexibility
    and testability.
    """

    def __init__(
        self,
        context_builder: ContextBuilderProtocol,
        claude_client: ClaudeClientProtocol,
        risk_manager: RiskManagerProtocol,
        executor: ExecutorProtocol,
        cache: CacheProtocol | None = None,
    ) -> None:
        """Initialize the decision brain with all dependencies.

        Args:
            context_builder: Builds decision context from signals
            claude_client: AI client for evaluating trades
            risk_manager: Validates and adjusts decisions for risk
            executor: Executes approved trades
            cache: Cache for settings access
        """
        self._context_builder = context_builder
        self._claude_client = claude_client
        self._risk_manager = risk_manager
        self._executor = executor
        self._cache = cache

    async def process(self, signal: TradeSignal) -> ExecutionResult:
        """Process a trade signal through the full decision pipeline.

        Pipeline steps:
        1. Build context from signal with wallet metrics, market data, risk state
        2. Get AI decision from Claude based on context
        3. Validate decision with risk manager (may adjust size or reject)
        4. If rejected after risk validation, return failure result
        5. Execute trade and return result

        Args:
            signal: The incoming trade signal to process

        Returns:
            ExecutionResult indicating success/failure and execution details
        """
        logger.info(
            "Processing signal: wallet={} market={} side={} action={} size={}",
            signal.wallet[:10],
            signal.market_id,
            signal.side,
            signal.action.value,
            signal.size,
        )

        # Check if AI is enabled
        ai_enabled = True
        copy_percentage = 1.0
        if self._cache:
            settings = await self._cache.get_settings()
            ai_enabled = settings.get("ai_enabled", True)
            copy_percentage = settings.get("copy_percentage", 1.0)

        # Step 1: Build context from signal
        context = await self._context_builder.build(signal)
        logger.debug("Context built for signal: market={}", signal.market_id)

        # Step 2: Get AI decision from Claude OR bypass if AI disabled
        if ai_enabled:
            decision = await self._claude_client.evaluate(context)
            logger.info(
                "AI decision: execute={} size={} confidence={}",
                decision.execute,
                decision.size,
                decision.confidence,
            )
        else:
            # AI disabled - copy trade directly with configured percentage
            copy_size = signal.size * copy_percentage
            action_str = "SELL" if signal.action == TradeAction.SELL else "BUY"
            decision = AIDecision(
                execute=True,
                size=copy_size,
                confidence=1.0,
                urgency=1.0,
                reasoning=f"Direct copy trade (AI disabled). {action_str} {signal.side} - Copying {copy_percentage*100:.0f}% of ${signal.size:.2f} = ${copy_size:.2f}",
            )
            logger.info(
                "Direct copy (AI disabled): {} {} size=${} ({}% of ${})",
                action_str,
                signal.side,
                copy_size,
                copy_percentage * 100,
                signal.size,
            )

        # Step 3a: Check slippage before full risk validation
        spread = context.market_spread
        decision = self._risk_manager.validate_slippage(decision, spread)
        if not decision.execute:
            logger.warning("Trade rejected due to slippage: {}", decision.reasoning)
            return ExecutionResult(
                success=False,
                executed_size=0.0,
                executed_price=0.0,
                paper_mode=True,
                message=f"Trade rejected: {decision.reasoning}",
            )

        # Step 3b: Validate with risk manager (exposure, daily loss, size limits)
        # Skip exposure validation for SELL orders since they REDUCE exposure
        is_sell = signal.action == TradeAction.SELL
        if is_sell:
            # SELL orders always allowed (they reduce exposure)
            validated_decision = decision
            logger.info("SELL order - skipping exposure validation (reduces exposure)")
        else:
            # BUY orders need full risk validation
            validated_decision = await self._risk_manager.validate(decision)

        # Step 4: If rejected after risk validation, return failure result
        if not validated_decision.execute:
            logger.warning(
                "Trade rejected by risk manager: {}",
                validated_decision.reasoning,
            )
            return ExecutionResult(
                success=False,
                executed_size=0.0,
                executed_price=0.0,
                paper_mode=True,
                message=f"Trade rejected: {validated_decision.reasoning}",
            )

        # Step 5: Execute trade and return result
        result = await self._executor.execute(signal, validated_decision)
        logger.info(
            "Trade execution result: success={} size={} price={}",
            result.success,
            result.executed_size,
            result.executed_price,
        )
        return result
