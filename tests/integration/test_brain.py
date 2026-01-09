"""Integration tests for AI decision brain."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from polymind.core.brain import (
    AIDecision,
    DecisionBrain,
    DecisionContext,
)
from polymind.core.execution import PaperExecutor
from polymind.core.risk import RiskManager
from polymind.data.models import SignalSource, TradeSignal


def test_decision_context_builds_correctly() -> None:
    """Context should build complete structure."""
    context = DecisionContext(
        signal_wallet="0x123",
        signal_market_id="market1",
        signal_side="YES",
        signal_size=100.0,
        signal_price=0.65,
        wallet_win_rate=0.72,
        wallet_avg_roi=1.34,
        wallet_total_trades=156,
        wallet_recent_performance=0.75,
        market_liquidity=25000.0,
        market_spread=0.02,
        risk_daily_pnl=-120.0,
        risk_open_exposure=800.0,
        risk_max_daily_loss=500.0,
    )

    data = context.to_dict()

    assert "signal" in data
    assert "wallet_metrics" in data
    assert "market_data" in data
    assert "risk_state" in data


def test_ai_decision_lifecycle() -> None:
    """Decision should support full lifecycle."""
    # Create decision from dict
    decision = AIDecision.from_dict({
        "execute": True,
        "size": 50.0,
        "confidence": 0.85,
        "urgency": "high",
        "reasoning": "Good opportunity",
    })

    assert decision.execute is True

    # Convert back to dict
    data = decision.to_dict()
    assert data["size"] == 50.0

    # Create rejection
    rejection = AIDecision.reject("Not a good trade")
    assert rejection.execute is False


@pytest.mark.asyncio
async def test_risk_manager_validates_decisions() -> None:
    """Risk manager should validate AI decisions."""
    mock_cache = AsyncMock()
    mock_cache.get_daily_pnl = AsyncMock(return_value=-100.0)
    mock_cache.get_open_exposure = AsyncMock(return_value=500.0)

    manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.85,
        reasoning="Good trade",
    )

    result = await manager.validate(decision)

    assert result.execute is True
    assert result.size == 50.0


@pytest.mark.asyncio
async def test_paper_executor_simulates_trades() -> None:
    """Paper executor should simulate trade execution."""
    mock_cache = AsyncMock()
    mock_cache.update_open_exposure = AsyncMock(return_value=100.0)

    executor = PaperExecutor(cache=mock_cache)

    signal = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc123",
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.85,
        reasoning="Good trade",
    )

    result = await executor.execute(signal, decision)

    assert result.success is True
    assert result.paper_mode is True
    assert result.executed_size == 50.0


@pytest.mark.asyncio
async def test_full_brain_pipeline() -> None:
    """Full brain pipeline should work end-to-end."""
    # Mock all dependencies
    mock_context = DecisionContext(
        signal_wallet="0x123",
        signal_market_id="market1",
        signal_side="YES",
        signal_size=100.0,
        signal_price=0.65,
        wallet_win_rate=0.72,
        wallet_avg_roi=1.34,
        wallet_total_trades=156,
        wallet_recent_performance=0.75,
        market_liquidity=25000.0,
        market_spread=0.02,
        risk_daily_pnl=-120.0,
        risk_open_exposure=800.0,
        risk_max_daily_loss=500.0,
    )

    mock_context_builder = AsyncMock()
    mock_context_builder.build = AsyncMock(return_value=mock_context)

    mock_claude = AsyncMock()
    mock_claude.evaluate = AsyncMock(
        return_value=AIDecision.approve(
            size=50.0,
            confidence=0.85,
            reasoning="Good trade",
        )
    )

    mock_cache = AsyncMock()
    mock_cache.get_daily_pnl = AsyncMock(return_value=-100.0)
    mock_cache.get_open_exposure = AsyncMock(return_value=500.0)
    mock_cache.update_open_exposure = AsyncMock(return_value=550.0)

    risk_manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    executor = PaperExecutor(cache=mock_cache)

    brain = DecisionBrain(
        context_builder=mock_context_builder,
        claude_client=mock_claude,
        risk_manager=risk_manager,
        executor=executor,
    )

    signal = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc123",
    )

    result = await brain.process(signal)

    assert result.success is True
    assert result.executed_size == 50.0
    assert result.paper_mode is True
