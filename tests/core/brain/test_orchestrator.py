"""Tests for decision brain orchestrator."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision, Urgency
from polymind.core.brain.orchestrator import DecisionBrain
from polymind.core.execution.paper import ExecutionResult
from polymind.data.models import SignalSource, TradeSignal


@pytest.fixture
def sample_signal():
    """Create sample trade signal for testing."""
    return TradeSignal(
        wallet="0x1234567890abcdef1234567890abcdef12345678",
        market_id="btc-50k-friday",
        token_id="token-123",
        side="YES",
        size=100.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime(2025, 1, 15, 10, 30, 0),
        tx_hash="0xabcdef1234567890",
    )


@pytest.fixture
def sample_context():
    """Create sample decision context for testing."""
    return DecisionContext(
        signal_wallet="0x1234567890abcdef1234567890abcdef12345678",
        signal_market_id="btc-50k-friday",
        signal_side="YES",
        signal_size=100.0,
        signal_price=0.65,
        wallet_win_rate=0.72,
        wallet_avg_roi=0.15,
        wallet_total_trades=50,
        wallet_recent_performance=0.08,
        market_liquidity=50000.0,
        market_spread=0.02,
        risk_daily_pnl=-50.0,
        risk_open_exposure=1000.0,
        risk_max_daily_loss=500.0,
    )


@pytest.fixture
def mock_context_builder(sample_context):
    """Create mock context builder."""
    builder = AsyncMock()
    builder.build = AsyncMock(return_value=sample_context)
    return builder


@pytest.fixture
def mock_claude_client():
    """Create mock Claude client with approval decision."""
    client = AsyncMock()
    client.evaluate = AsyncMock(
        return_value=AIDecision.approve(
            size=75.0,
            confidence=0.85,
            reasoning="Strong signal from high-performing wallet",
            urgency=Urgency.HIGH,
        )
    )
    return client


@pytest.fixture
def mock_risk_manager():
    """Create mock risk manager that passes through decisions."""

    async def pass_through(decision):
        return decision

    def slippage_pass_through(decision, spread):
        return decision

    manager = AsyncMock()
    manager.validate = AsyncMock(side_effect=pass_through)
    manager.validate_slippage = slippage_pass_through
    return manager


@pytest.fixture
def mock_executor():
    """Create mock executor."""
    executor = AsyncMock()
    executor.execute = AsyncMock(
        return_value=ExecutionResult(
            success=True,
            executed_size=75.0,
            executed_price=0.65,
            paper_mode=True,
            message="Paper trade executed: YES 75.0000 @ 0.6500",
        )
    )
    return executor


@pytest.fixture
def decision_brain(
    mock_context_builder, mock_claude_client, mock_risk_manager, mock_executor
):
    """Create decision brain with all mock dependencies."""
    return DecisionBrain(
        context_builder=mock_context_builder,
        claude_client=mock_claude_client,
        risk_manager=mock_risk_manager,
        executor=mock_executor,
    )


class TestDecisionBrain:
    """Tests for DecisionBrain class."""

    @pytest.mark.asyncio
    async def test_brain_processes_signal(
        self,
        decision_brain,
        sample_signal,
        sample_context,
        mock_context_builder,
        mock_claude_client,
        mock_risk_manager,
        mock_executor,
    ):
        """Full pipeline success - signal processed through all stages."""
        result = await decision_brain.process(sample_signal)

        # Verify successful execution
        assert result.success is True
        assert result.executed_size == 75.0
        assert result.executed_price == 0.65
        assert result.paper_mode is True

        # Verify context builder was called with signal
        mock_context_builder.build.assert_called_once_with(sample_signal)

        # Verify Claude client was called with context
        mock_claude_client.evaluate.assert_called_once_with(sample_context)

        # Verify risk manager was called with AI decision
        mock_risk_manager.validate.assert_called_once()
        validated_call_arg = mock_risk_manager.validate.call_args[0][0]
        assert validated_call_arg.execute is True
        assert validated_call_arg.size == 75.0

        # Verify executor was called with signal and validated decision
        mock_executor.execute.assert_called_once()
        executor_call_args = mock_executor.execute.call_args[0]
        assert executor_call_args[0] == sample_signal
        assert executor_call_args[1].execute is True
        assert executor_call_args[1].size == 75.0

    @pytest.mark.asyncio
    async def test_brain_stops_on_risk_rejection(
        self,
        sample_signal,
        sample_context,
        mock_context_builder,
        mock_claude_client,
        mock_executor,
    ):
        """Stops if risk manager rejects the decision."""
        # Create risk manager that rejects the trade
        mock_risk_manager = AsyncMock()
        mock_risk_manager.validate = AsyncMock(
            return_value=AIDecision.reject(
                "Trade blocked: daily_loss_exceeded "
                "(daily P&L: -550.00, limit: -500.00)"
            )
        )
        mock_risk_manager.validate_slippage = lambda decision, spread: decision

        brain = DecisionBrain(
            context_builder=mock_context_builder,
            claude_client=mock_claude_client,
            risk_manager=mock_risk_manager,
            executor=mock_executor,
        )

        result = await brain.process(sample_signal)

        # Verify rejection result
        assert result.success is False
        assert result.executed_size == 0.0
        assert result.executed_price == 0.0
        assert result.paper_mode is True
        assert "Trade rejected" in result.message
        assert "daily_loss_exceeded" in result.message

        # Verify executor was NOT called
        mock_executor.execute.assert_not_called()

        # Verify other components were still called
        mock_context_builder.build.assert_called_once_with(sample_signal)
        mock_claude_client.evaluate.assert_called_once_with(sample_context)
        mock_risk_manager.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_brain_stops_on_ai_rejection(
        self,
        sample_signal,
        sample_context,
        mock_context_builder,
        mock_risk_manager,
        mock_executor,
    ):
        """Stops if AI client rejects the decision."""
        # Create Claude client that rejects the trade
        mock_claude_client = AsyncMock()
        mock_claude_client.evaluate = AsyncMock(
            return_value=AIDecision.reject("Wallet has insufficient track record")
        )

        brain = DecisionBrain(
            context_builder=mock_context_builder,
            claude_client=mock_claude_client,
            risk_manager=mock_risk_manager,
            executor=mock_executor,
        )

        result = await brain.process(sample_signal)

        # Verify rejection result
        assert result.success is False
        assert result.executed_size == 0.0
        assert "Trade rejected" in result.message
        assert "insufficient track record" in result.message

        # Verify executor was NOT called
        mock_executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_brain_handles_risk_size_adjustment(
        self,
        sample_signal,
        sample_context,
        mock_context_builder,
        mock_claude_client,
        mock_executor,
    ):
        """Risk manager adjusts size but still approves."""
        # Create Claude client that approves with large size
        mock_claude_client.evaluate = AsyncMock(
            return_value=AIDecision.approve(
                size=500.0,
                confidence=0.85,
                reasoning="Strong signal",
            )
        )

        # Create risk manager that reduces size
        mock_risk_manager = AsyncMock()
        mock_risk_manager.validate = AsyncMock(
            return_value=AIDecision.approve(
                size=200.0,  # Reduced from 500 to 200
                confidence=0.85,
                reasoning="Strong signal [Size adjusted by risk manager]",
            )
        )
        mock_risk_manager.validate_slippage = lambda decision, spread: decision

        # Create executor that returns adjusted size
        mock_executor.execute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                executed_size=200.0,
                executed_price=0.65,
                paper_mode=True,
                message="Paper trade executed: YES 200.0000 @ 0.6500",
            )
        )

        brain = DecisionBrain(
            context_builder=mock_context_builder,
            claude_client=mock_claude_client,
            risk_manager=mock_risk_manager,
            executor=mock_executor,
        )

        result = await brain.process(sample_signal)

        # Verify successful execution with adjusted size
        assert result.success is True
        assert result.executed_size == 200.0

        # Verify executor received the risk-adjusted decision
        mock_executor.execute.assert_called_once()
        executor_call_args = mock_executor.execute.call_args[0]
        assert executor_call_args[1].size == 200.0
        assert "Size adjusted by risk manager" in executor_call_args[1].reasoning

    @pytest.mark.asyncio
    async def test_brain_pipeline_order(
        self,
        decision_brain,
        sample_signal,
        mock_context_builder,
        mock_claude_client,
        mock_risk_manager,
        mock_executor,
    ):
        """Verify components are called in correct order."""
        call_order = []

        async def track_context_build(signal):
            call_order.append("context_builder")
            return DecisionContext(
                signal_wallet=signal.wallet,
                signal_market_id=signal.market_id,
                signal_side=signal.side,
                signal_size=signal.size,
                signal_price=signal.price,
                wallet_win_rate=0.72,
                wallet_avg_roi=0.15,
                wallet_total_trades=50,
                wallet_recent_performance=0.08,
                market_liquidity=50000.0,
                market_spread=0.02,
                risk_daily_pnl=-50.0,
                risk_open_exposure=1000.0,
                risk_max_daily_loss=500.0,
            )

        async def track_claude_evaluate(context):
            call_order.append("claude_client")
            return AIDecision.approve(
                size=75.0,
                confidence=0.85,
                reasoning="Approved",
            )

        async def track_risk_validate(decision):
            call_order.append("risk_manager")
            return decision

        def track_slippage_validate(decision, spread):
            call_order.append("slippage_check")
            return decision

        async def track_execute(signal, decision):
            call_order.append("executor")
            return ExecutionResult(
                success=True,
                executed_size=75.0,
                executed_price=0.65,
                paper_mode=True,
                message="Executed",
            )

        mock_context_builder.build = AsyncMock(side_effect=track_context_build)
        mock_claude_client.evaluate = AsyncMock(side_effect=track_claude_evaluate)
        mock_risk_manager.validate = AsyncMock(side_effect=track_risk_validate)
        mock_risk_manager.validate_slippage = track_slippage_validate
        mock_executor.execute = AsyncMock(side_effect=track_execute)

        await decision_brain.process(sample_signal)

        assert call_order == [
            "context_builder",
            "claude_client",
            "slippage_check",
            "risk_manager",
            "executor",
        ]
