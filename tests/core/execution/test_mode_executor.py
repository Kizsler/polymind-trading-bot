"""Tests for mode-aware executor."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from datetime import datetime, timezone

from polymind.core.execution.mode_executor import ModeAwareExecutor
from polymind.core.execution.paper import ExecutionResult
from polymind.core.execution.safety import LiveModeBlockedError
from polymind.core.brain.decision import AIDecision
from polymind.data.models import TradeSignal, SignalSource


class TestModeAwareExecutor:
    """Tests for ModeAwareExecutor."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.get_mode = AsyncMock(return_value="paper")
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        return cache

    @pytest.fixture
    def mock_paper_executor(self) -> MagicMock:
        """Create mock paper executor."""
        executor = MagicMock()
        executor.execute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                executed_size=100.0,
                executed_price=0.55,
                paper_mode=True,
                message="Paper trade executed",
            )
        )
        return executor

    @pytest.fixture
    def mock_live_executor(self) -> MagicMock:
        """Create mock live executor."""
        executor = MagicMock()
        executor.is_configured = True
        executor.submit_order = AsyncMock(
            return_value={
                "order_id": "ext_123",
                "status": "filled",
                "filled_size": 100.0,
                "filled_price": 0.55,
            }
        )
        return executor

    @pytest.fixture
    def signal(self) -> TradeSignal:
        """Create test signal."""
        return TradeSignal(
            wallet="0x1234567890",
            market_id="market_abc",
            token_id="token_123",
            side="BUY",
            size=100.0,
            price=0.55,
            source=SignalSource.CLOB,
            timestamp=datetime.now(timezone.utc),
            tx_hash="0xabcd1234",
        )

    @pytest.fixture
    def decision(self) -> AIDecision:
        """Create test decision."""
        return AIDecision(
            execute=True,
            size=100.0,
            confidence=0.8,
            reasoning="Test decision",
            urgency="normal",
        )

    @pytest.mark.asyncio
    async def test_paper_mode_uses_paper_executor(
        self,
        mock_cache: MagicMock,
        mock_paper_executor: MagicMock,
        mock_live_executor: MagicMock,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> None:
        """Test paper mode uses paper executor."""
        mock_cache.get_mode.return_value = "paper"

        executor = ModeAwareExecutor(
            cache=mock_cache,
            paper_executor=mock_paper_executor,
            live_executor=mock_live_executor,
        )

        result = await executor.execute(signal, decision)

        assert result.paper_mode is True
        mock_paper_executor.execute.assert_called_once()
        mock_live_executor.submit_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_live_mode_without_confirmation_uses_paper(
        self,
        mock_cache: MagicMock,
        mock_paper_executor: MagicMock,
        mock_live_executor: MagicMock,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> None:
        """Test live mode without confirmation falls back to paper."""
        mock_cache.get_mode.return_value = "live"
        mock_cache.get.return_value = None  # No live_confirmed

        executor = ModeAwareExecutor(
            cache=mock_cache,
            paper_executor=mock_paper_executor,
            live_executor=None,  # No live executor configured
        )

        result = await executor.execute(signal, decision)

        # Should fall back to paper mode
        assert result.paper_mode is True
        mock_paper_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_live_mode_with_confirmation_uses_live(
        self,
        mock_cache: MagicMock,
        mock_paper_executor: MagicMock,
        mock_live_executor: MagicMock,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> None:
        """Test live mode with confirmation uses live executor."""
        mock_cache.get_mode.return_value = "live"

        def get_side_effect(key: str):
            if key == "live_confirmed":
                return True
            if key == "emergency_stop":
                return None  # No emergency stop
            return None

        mock_cache.get.side_effect = get_side_effect

        executor = ModeAwareExecutor(
            cache=mock_cache,
            paper_executor=mock_paper_executor,
            live_executor=mock_live_executor,
        )

        result = await executor.execute(signal, decision)

        assert result.paper_mode is False
        mock_live_executor.submit_order.assert_called_once()
        mock_paper_executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_emergency_stop_blocks_live_execution(
        self,
        mock_cache: MagicMock,
        mock_paper_executor: MagicMock,
        mock_live_executor: MagicMock,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> None:
        """Test emergency stop blocks live execution."""
        mock_cache.get_mode.return_value = "live"

        def get_side_effect(key: str):
            if key == "live_confirmed":
                return True
            if key == "emergency_stop":
                return {"active": True, "reason": "Manual stop"}
            return None

        mock_cache.get.side_effect = get_side_effect

        executor = ModeAwareExecutor(
            cache=mock_cache,
            paper_executor=mock_paper_executor,
            live_executor=mock_live_executor,
        )

        result = await executor.execute(signal, decision)

        # Should fail due to emergency stop
        assert result.success is False
        assert "emergency" in result.message.lower()
