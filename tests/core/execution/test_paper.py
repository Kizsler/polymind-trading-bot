"""Tests for paper trading execution engine."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from polymind.core.brain.decision import AIDecision, Urgency
from polymind.core.execution.paper import ExecutionResult, PaperExecutor
from polymind.data.models import SignalSource, TradeSignal


@pytest.fixture
def mock_cache():
    """Create mock cache with default behavior."""
    cache = AsyncMock()
    cache.update_open_exposure = AsyncMock(return_value=100.0)
    return cache


@pytest.fixture
def paper_executor(mock_cache):
    """Create paper executor with mock cache."""
    return PaperExecutor(cache=mock_cache)


@pytest.fixture
def sample_signal():
    """Create a sample trade signal for testing."""
    return TradeSignal(
        wallet="0x1234567890abcdef1234567890abcdef12345678",
        market_id="market-123",
        token_id="token-456",
        side="buy",
        size=50.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        tx_hash="0xabcdef123456",
    )


@pytest.fixture
def approve_decision():
    """Create an approval decision for testing."""
    return AIDecision.approve(
        size=100.0,
        confidence=0.85,
        reasoning="Strong signal from tracked wallet",
        urgency=Urgency.NORMAL,
    )


@pytest.fixture
def reject_decision():
    """Create a rejection decision for testing."""
    return AIDecision.reject("Market conditions unfavorable")


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_execution_result_to_dict(self):
        """Verify ExecutionResult serialization to dictionary."""
        result = ExecutionResult(
            success=True,
            executed_size=100.0,
            executed_price=0.65,
            paper_mode=True,
            message="Paper trade executed successfully",
        )

        data = result.to_dict()

        assert data == {
            "success": True,
            "executed_size": 100.0,
            "executed_price": 0.65,
            "paper_mode": True,
            "message": "Paper trade executed successfully",
        }

    def test_execution_result_to_dict_failure(self):
        """Verify ExecutionResult serialization for failed execution."""
        result = ExecutionResult(
            success=False,
            executed_size=0.0,
            executed_price=0.0,
            paper_mode=True,
            message="Trade rejected: insufficient confidence",
        )

        data = result.to_dict()

        assert data["success"] is False
        assert data["executed_size"] == 0.0
        assert data["executed_price"] == 0.0
        assert data["paper_mode"] is True
        assert "rejected" in data["message"]

    def test_execution_result_attributes(self):
        """Verify ExecutionResult dataclass attributes."""
        result = ExecutionResult(
            success=True,
            executed_size=50.5,
            executed_price=0.72,
            paper_mode=False,
            message="Live trade executed",
        )

        assert result.success is True
        assert result.executed_size == 50.5
        assert result.executed_price == 0.72
        assert result.paper_mode is False
        assert result.message == "Live trade executed"


class TestPaperExecutor:
    """Tests for PaperExecutor class."""

    @pytest.mark.asyncio
    async def test_paper_executor_simulates_trade(
        self, paper_executor, sample_signal, approve_decision
    ):
        """Verify paper executor returns success result for approved trades."""
        result = await paper_executor.execute(sample_signal, approve_decision)

        assert result.success is True
        assert result.executed_size == approve_decision.size
        assert result.executed_price == sample_signal.price
        assert result.paper_mode is True
        assert "Paper trade executed" in result.message
        assert "buy" in result.message
        assert "100.0000" in result.message
        assert "0.6500" in result.message

    @pytest.mark.asyncio
    async def test_paper_executor_updates_exposure(
        self, paper_executor, mock_cache, sample_signal, approve_decision
    ):
        """Verify paper executor updates exposure via cache."""
        await paper_executor.execute(sample_signal, approve_decision)

        mock_cache.update_open_exposure.assert_called_once_with(approve_decision.size)

    @pytest.mark.asyncio
    async def test_paper_executor_rejects_non_execute(
        self, paper_executor, mock_cache, sample_signal, reject_decision
    ):
        """Verify paper executor returns failure for rejected decisions."""
        result = await paper_executor.execute(sample_signal, reject_decision)

        assert result.success is False
        assert result.executed_size == 0.0
        assert result.executed_price == 0.0
        assert result.paper_mode is True
        assert "rejected" in result.message.lower()
        assert "Market conditions unfavorable" in result.message
        # Should not update exposure for rejected trades
        mock_cache.update_open_exposure.assert_not_called()

    @pytest.mark.asyncio
    async def test_paper_executor_uses_decision_size(
        self, paper_executor, sample_signal
    ):
        """Verify executor uses AI decision size, not signal size."""
        # Signal has size 50, decision has different size
        decision = AIDecision.approve(
            size=75.0,
            confidence=0.90,
            reasoning="Custom size from AI",
        )

        result = await paper_executor.execute(sample_signal, decision)

        assert result.executed_size == 75.0
        assert result.executed_size != sample_signal.size

    @pytest.mark.asyncio
    async def test_paper_executor_uses_signal_price(
        self, paper_executor, sample_signal, approve_decision
    ):
        """Verify executor uses signal price for execution."""
        result = await paper_executor.execute(sample_signal, approve_decision)

        assert result.executed_price == sample_signal.price
        assert result.executed_price == 0.65

    @pytest.mark.asyncio
    async def test_paper_executor_always_paper_mode(
        self, paper_executor, sample_signal, approve_decision
    ):
        """Verify paper executor always returns paper_mode=True."""
        result = await paper_executor.execute(sample_signal, approve_decision)

        assert result.paper_mode is True

    @pytest.mark.asyncio
    async def test_paper_executor_with_high_urgency(
        self, paper_executor, sample_signal
    ):
        """Verify executor handles high urgency decisions."""
        decision = AIDecision.approve(
            size=200.0,
            confidence=0.95,
            reasoning="Urgent opportunity",
            urgency=Urgency.HIGH,
        )

        result = await paper_executor.execute(sample_signal, decision)

        assert result.success is True
        assert result.executed_size == 200.0

    @pytest.mark.asyncio
    async def test_paper_executor_with_sell_signal(self, paper_executor, mock_cache):
        """Verify executor handles sell signals correctly."""
        sell_signal = TradeSignal(
            wallet="0x1234",
            market_id="market-abc",
            token_id="token-xyz",
            side="sell",
            size=30.0,
            price=0.80,
            source=SignalSource.CHAIN,
            timestamp=datetime(2024, 1, 15, 14, 0, 0),
            tx_hash="0xsellhash",
        )
        decision = AIDecision.approve(
            size=25.0,
            confidence=0.80,
            reasoning="Exit position",
        )

        result = await paper_executor.execute(sell_signal, decision)

        assert result.success is True
        assert "sell" in result.message
        assert result.executed_price == 0.80
