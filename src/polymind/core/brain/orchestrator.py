"""Decision brain orchestrator for coordinating trading decisions."""

from typing import Protocol

from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision
from polymind.core.execution.paper import ExecutionResult
from polymind.data.models import TradeSignal
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


class DecisionBrain:
    """Orchestrator for the AI-powered trading decision pipeline.

    Coordinates the flow from signal detection through execution:
    1. Build context from incoming signal
    2. Get AI decision from Claude
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
    ) -> None:
        """Initialize the decision brain with all dependencies.

        Args:
            context_builder: Builds decision context from signals
            claude_client: AI client for evaluating trades
            risk_manager: Validates and adjusts decisions for risk
            executor: Executes approved trades
        """
        self._context_builder = context_builder
        self._claude_client = claude_client
        self._risk_manager = risk_manager
        self._executor = executor

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
            "Processing signal: wallet={} market={} side={} size={}",
            signal.wallet[:10],
            signal.market_id,
            signal.side,
            signal.size,
        )

        # Step 1: Build context from signal
        context = await self._context_builder.build(signal)
        logger.debug("Context built for signal: market={}", signal.market_id)

        # Step 2: Get AI decision from Claude
        decision = await self._claude_client.evaluate(context)
        logger.info(
            "AI decision: execute={} size={} confidence={}",
            decision.execute,
            decision.size,
            decision.confidence,
        )

        # Step 3: Validate with risk manager
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
