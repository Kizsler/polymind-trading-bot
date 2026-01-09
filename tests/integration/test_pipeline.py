"""End-to-end integration tests for the trading pipeline."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from polymind.core.brain import (
    AIDecision,
    ClaudeClient,
    DecisionBrain,
    DecisionContext,
    DecisionContextBuilder,
    Urgency,
)
from polymind.core.execution import ExecutionResult, PaperExecutor
from polymind.core.risk import RiskManager
from polymind.data.models import SignalSource, TradeSignal


@pytest.fixture
def sample_signal() -> TradeSignal:
    """Create a sample trade signal for testing."""
    return TradeSignal(
        wallet="0xsmarttrader123",
        market_id="0xelection2024",
        token_id="yes_token_123",
        side="YES",
        size=100.0,
        price=0.55,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc123def456",
    )


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Create a mock cache with reasonable defaults."""
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=0.0)  # No losses yet
    cache.get_open_exposure = AsyncMock(return_value=0.0)  # No open positions
    cache.update_open_exposure = AsyncMock(return_value=100.0)
    return cache


@pytest.fixture
def mock_market_service() -> AsyncMock:
    """Create a mock market service."""
    service = AsyncMock()
    service.get_liquidity = AsyncMock(return_value=50000.0)  # Good liquidity
    service.get_spread = AsyncMock(return_value=0.02)  # 2% spread
    return service


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock database."""
    db = AsyncMock()
    db.get_wallet_metrics = AsyncMock(return_value={
        "win_rate": 0.65,
        "avg_roi": 0.12,
        "total_trades": 50,
        "recent_performance": 0.08,
    })
    return db


# Test Context Building


@pytest.mark.asyncio
async def test_context_builder_assembles_all_data(
    sample_signal: TradeSignal,
    mock_cache: AsyncMock,
    mock_market_service: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """Context builder should assemble data from all sources."""
    builder = DecisionContextBuilder(
        cache=mock_cache,
        market_service=mock_market_service,
        db=mock_db,
        max_daily_loss=500.0,
    )

    context = await builder.build(sample_signal)

    assert context.signal_wallet == sample_signal.wallet
    assert context.signal_market_id == sample_signal.market_id
    assert context.wallet_win_rate == 0.65
    assert context.market_liquidity == 50000.0
    assert context.risk_max_daily_loss == 500.0


# Test Risk Manager


@pytest.mark.asyncio
async def test_risk_manager_approves_within_limits(mock_cache: AsyncMock) -> None:
    """Risk manager should approve trades within limits."""
    manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.8,
        reasoning="Good opportunity",
    )

    validated = await manager.validate(decision)

    assert validated.execute is True
    assert validated.size == 50.0


@pytest.mark.asyncio
async def test_risk_manager_caps_large_trades(mock_cache: AsyncMock) -> None:
    """Risk manager should cap trades exceeding max_single_trade."""
    manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(
        size=200.0,  # Exceeds max_single_trade
        confidence=0.8,
        reasoning="Large opportunity",
    )

    validated = await manager.validate(decision)

    assert validated.execute is True
    assert validated.size == 100.0  # Capped to max


@pytest.mark.asyncio
async def test_risk_manager_blocks_after_daily_loss() -> None:
    """Risk manager should block trades when daily loss exceeded."""
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=-600.0)  # Lost $600
    cache.get_open_exposure = AsyncMock(return_value=0.0)

    manager = RiskManager(
        cache=cache,
        max_daily_loss=500.0,  # Limit is $500
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.8,
        reasoning="Another trade",
    )

    validated = await manager.validate(decision)

    assert validated.execute is False
    assert "daily_loss_exceeded" in validated.reasoning


# Test Paper Executor


@pytest.mark.asyncio
async def test_paper_executor_simulates_trade(
    sample_signal: TradeSignal,
    mock_cache: AsyncMock,
) -> None:
    """Paper executor should simulate trade execution."""
    executor = PaperExecutor(cache=mock_cache)

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.8,
        reasoning="Execute this",
    )

    result = await executor.execute(sample_signal, decision)

    assert result.success is True
    assert result.paper_mode is True
    assert result.executed_size == 50.0


# Test Full Pipeline


@pytest.mark.asyncio
async def test_full_pipeline_approve_and_execute(
    sample_signal: TradeSignal,
    mock_cache: AsyncMock,
    mock_market_service: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """Full pipeline should process signal through to execution."""
    # Create context builder
    context_builder = DecisionContextBuilder(
        cache=mock_cache,
        market_service=mock_market_service,
        db=mock_db,
        max_daily_loss=500.0,
    )

    # Create mock Claude client that approves
    mock_claude = AsyncMock()
    mock_claude.evaluate = AsyncMock(return_value=AIDecision.approve(
        size=50.0,
        confidence=0.75,
        reasoning="High win rate wallet, good liquidity",
    ))

    # Create risk manager
    risk_manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    # Create paper executor
    executor = PaperExecutor(cache=mock_cache)

    # Assemble brain
    brain = DecisionBrain(
        context_builder=context_builder,
        claude_client=mock_claude,
        risk_manager=risk_manager,
        executor=executor,
    )

    # Process signal
    result = await brain.process(sample_signal)

    # Verify full pipeline executed
    assert result.success is True
    assert result.paper_mode is True
    assert result.executed_size == 50.0
    mock_claude.evaluate.assert_called_once()


@pytest.mark.asyncio
async def test_full_pipeline_reject_by_ai(
    sample_signal: TradeSignal,
    mock_cache: AsyncMock,
    mock_market_service: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """Pipeline should handle AI rejection gracefully."""
    context_builder = DecisionContextBuilder(
        cache=mock_cache,
        market_service=mock_market_service,
        db=mock_db,
        max_daily_loss=500.0,
    )

    # Claude rejects the trade
    mock_claude = AsyncMock()
    mock_claude.evaluate = AsyncMock(return_value=AIDecision.reject(
        "Low confidence - wallet has poor recent performance"
    ))

    risk_manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    executor = PaperExecutor(cache=mock_cache)

    brain = DecisionBrain(
        context_builder=context_builder,
        claude_client=mock_claude,
        risk_manager=risk_manager,
        executor=executor,
    )

    result = await brain.process(sample_signal)

    assert result.success is False
    assert "rejected" in result.message.lower()


@pytest.mark.asyncio
async def test_full_pipeline_reject_by_risk(
    sample_signal: TradeSignal,
    mock_market_service: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """Pipeline should handle risk rejection after AI approval."""
    # Cache shows we've already hit daily loss limit
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=-600.0)
    cache.get_open_exposure = AsyncMock(return_value=0.0)

    context_builder = DecisionContextBuilder(
        cache=cache,
        market_service=mock_market_service,
        db=mock_db,
        max_daily_loss=500.0,
    )

    # Claude approves
    mock_claude = AsyncMock()
    mock_claude.evaluate = AsyncMock(return_value=AIDecision.approve(
        size=50.0,
        confidence=0.8,
        reasoning="Looks good",
    ))

    risk_manager = RiskManager(
        cache=cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    executor = PaperExecutor(cache=cache)

    brain = DecisionBrain(
        context_builder=context_builder,
        claude_client=mock_claude,
        risk_manager=risk_manager,
        executor=executor,
    )

    result = await brain.process(sample_signal)

    # AI approved but risk manager blocked
    assert result.success is False
    assert "daily_loss_exceeded" in result.message


# Test Signal Flow


@pytest.mark.asyncio
async def test_signal_to_context_to_decision() -> None:
    """Test the flow from signal to context to decision."""
    signal = TradeSignal(
        wallet="0xprofitabletrader",
        market_id="0xprediction123",
        token_id="token_abc",
        side="NO",
        size=75.0,
        price=0.40,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xdef789",
    )

    # Build context
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=-50.0)
    cache.get_open_exposure = AsyncMock(return_value=200.0)

    market_service = AsyncMock()
    market_service.get_liquidity = AsyncMock(return_value=100000.0)
    market_service.get_spread = AsyncMock(return_value=0.01)

    db = AsyncMock()
    db.get_wallet_metrics = AsyncMock(return_value={
        "win_rate": 0.70,
        "avg_roi": 0.15,
        "total_trades": 100,
        "recent_performance": 0.10,
    })

    builder = DecisionContextBuilder(
        cache=cache,
        market_service=market_service,
        db=db,
        max_daily_loss=500.0,
    )

    context = await builder.build(signal)

    # Verify context has all the data
    assert context.signal_wallet == "0xprofitabletrader"
    assert context.signal_side == "NO"
    assert context.wallet_win_rate == 0.70
    assert context.market_liquidity == 100000.0
    assert context.risk_daily_pnl == -50.0
    assert context.risk_open_exposure == 200.0

    # Context can be serialized for Claude
    context_dict = context.to_dict()
    assert "signal" in context_dict
    assert "wallet_metrics" in context_dict
    assert "market_data" in context_dict
    assert "risk_state" in context_dict


# Additional Edge Case Tests


@pytest.mark.asyncio
async def test_pipeline_with_unknown_wallet(
    sample_signal: TradeSignal,
    mock_cache: AsyncMock,
    mock_market_service: AsyncMock,
) -> None:
    """Pipeline should handle unknown wallet gracefully with default metrics."""
    # Database returns None for unknown wallet
    mock_db = AsyncMock()
    mock_db.get_wallet_metrics = AsyncMock(return_value=None)

    context_builder = DecisionContextBuilder(
        cache=mock_cache,
        market_service=mock_market_service,
        db=mock_db,
        max_daily_loss=500.0,
    )

    context = await context_builder.build(sample_signal)

    # Should use default values for unknown wallet
    assert context.wallet_win_rate == 0.0
    assert context.wallet_avg_roi == 0.0
    assert context.wallet_total_trades == 0
    assert context.wallet_recent_performance == 0.0


@pytest.mark.asyncio
async def test_pipeline_risk_caps_to_remaining_exposure() -> None:
    """Risk manager should cap trade to remaining exposure capacity."""
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=0.0)
    cache.get_open_exposure = AsyncMock(return_value=1950.0)  # Near limit

    manager = RiskManager(
        cache=cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,  # Only $50 remaining
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(
        size=100.0,  # Would exceed remaining capacity
        confidence=0.8,
        reasoning="Good trade",
    )

    validated = await manager.validate(decision)

    assert validated.execute is True
    assert validated.size == 50.0  # Capped to remaining capacity


@pytest.mark.asyncio
async def test_pipeline_risk_blocks_at_max_exposure() -> None:
    """Risk manager should block trades when at max exposure."""
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=0.0)
    cache.get_open_exposure = AsyncMock(return_value=2000.0)  # At limit

    manager = RiskManager(
        cache=cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.8,
        reasoning="Good trade",
    )

    validated = await manager.validate(decision)

    assert validated.execute is False
    assert "exposure_exceeded" in validated.reasoning


@pytest.mark.asyncio
async def test_executor_rejects_non_execute_decision(
    sample_signal: TradeSignal,
    mock_cache: AsyncMock,
) -> None:
    """Paper executor should reject decisions with execute=False."""
    executor = PaperExecutor(cache=mock_cache)

    decision = AIDecision.reject("Trade not recommended")

    result = await executor.execute(sample_signal, decision)

    assert result.success is False
    assert result.executed_size == 0.0
    assert "rejected" in result.message.lower()


@pytest.mark.asyncio
async def test_decision_urgency_propagates() -> None:
    """Decision urgency should be preserved through the pipeline."""
    decision = AIDecision.approve(
        size=50.0,
        confidence=0.9,
        reasoning="Time sensitive",
        urgency=Urgency.HIGH,
    )

    assert decision.urgency == Urgency.HIGH
    assert decision.to_dict()["urgency"] == "high"

    # Parsing should preserve urgency
    parsed = AIDecision.from_dict(decision.to_dict())
    assert parsed.urgency == Urgency.HIGH


@pytest.mark.asyncio
async def test_execution_result_serialization() -> None:
    """ExecutionResult should serialize properly."""
    result = ExecutionResult(
        success=True,
        executed_size=50.0,
        executed_price=0.65,
        paper_mode=True,
        message="Trade executed successfully",
    )

    data = result.to_dict()

    assert data["success"] is True
    assert data["executed_size"] == 50.0
    assert data["executed_price"] == 0.65
    assert data["paper_mode"] is True
    assert "successfully" in data["message"]
