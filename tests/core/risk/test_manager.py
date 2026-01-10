"""Tests for risk manager."""

from unittest.mock import AsyncMock

import pytest

from polymind.core.brain.decision import AIDecision, Urgency
from polymind.core.risk.manager import RiskManager, RiskViolation


@pytest.fixture
def mock_cache():
    """Create mock cache with default values."""
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=0.0)
    cache.get_open_exposure = AsyncMock(return_value=0.0)
    return cache


@pytest.fixture
def risk_manager(mock_cache):
    """Create risk manager with standard limits."""
    return RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=300.0,
    )


class TestRiskViolationEnum:
    """Tests for RiskViolation enum."""

    def test_risk_violation_enum(self):
        """Verify enum values are correct."""
        assert RiskViolation.DAILY_LOSS_EXCEEDED.value == "daily_loss_exceeded"
        assert RiskViolation.EXPOSURE_EXCEEDED.value == "exposure_exceeded"
        assert RiskViolation.TRADE_SIZE_EXCEEDED.value == "trade_size_exceeded"

    def test_risk_violation_enum_members(self):
        """Verify all expected members exist."""
        members = list(RiskViolation)
        assert len(members) == 4
        assert RiskViolation.DAILY_LOSS_EXCEEDED in members
        assert RiskViolation.EXPOSURE_EXCEEDED in members
        assert RiskViolation.TRADE_SIZE_EXCEEDED in members
        assert RiskViolation.SLIPPAGE_EXCEEDED in members


class TestRiskManager:
    """Tests for RiskManager class."""

    @pytest.mark.asyncio
    async def test_risk_manager_allows_valid_trade(self, risk_manager, mock_cache):
        """Trade within limits passes through unchanged."""
        decision = AIDecision.approve(
            size=100.0,
            confidence=0.85,
            reasoning="Valid trade opportunity",
            urgency=Urgency.NORMAL,
        )

        result = await risk_manager.validate(decision)

        assert result.execute is True
        assert result.size == 100.0
        assert result.confidence == 0.85
        assert result.reasoning == "Valid trade opportunity"
        mock_cache.get_daily_pnl.assert_called_once()
        mock_cache.get_open_exposure.assert_called_once()

    @pytest.mark.asyncio
    async def test_risk_manager_passes_through_rejections(
        self, risk_manager, mock_cache
    ):
        """Rejection decisions pass through unchanged."""
        decision = AIDecision.reject("AI rejected this trade")

        result = await risk_manager.validate(decision)

        assert result.execute is False
        assert result.size == 0.0
        assert result.reasoning == "AI rejected this trade"
        # Should not check risk state for rejections
        mock_cache.get_daily_pnl.assert_not_called()
        mock_cache.get_open_exposure.assert_not_called()

    @pytest.mark.asyncio
    async def test_risk_manager_blocks_over_daily_loss(self, risk_manager, mock_cache):
        """Blocks trade when daily loss limit exceeded."""
        # Set P&L to exceed the -500 limit
        mock_cache.get_daily_pnl = AsyncMock(return_value=-550.0)

        decision = AIDecision.approve(
            size=100.0,
            confidence=0.90,
            reasoning="Should be blocked",
        )

        result = await risk_manager.validate(decision)

        assert result.execute is False
        assert result.size == 0.0
        assert "daily_loss_exceeded" in result.reasoning
        assert "-550.00" in result.reasoning
        assert "-500.00" in result.reasoning

    @pytest.mark.asyncio
    async def test_risk_manager_blocks_at_exact_daily_loss(
        self, risk_manager, mock_cache
    ):
        """Blocks trade when daily loss is exactly at the limit."""
        mock_cache.get_daily_pnl = AsyncMock(return_value=-500.0)

        decision = AIDecision.approve(
            size=100.0,
            confidence=0.90,
            reasoning="At exact limit",
        )

        result = await risk_manager.validate(decision)

        assert result.execute is False
        assert "daily_loss_exceeded" in result.reasoning

    @pytest.mark.asyncio
    async def test_risk_manager_allows_trade_just_below_daily_loss(
        self, risk_manager, mock_cache
    ):
        """Allows trade when daily loss is just below the limit."""
        mock_cache.get_daily_pnl = AsyncMock(return_value=-499.99)

        decision = AIDecision.approve(
            size=100.0,
            confidence=0.90,
            reasoning="Just below limit",
        )

        result = await risk_manager.validate(decision)

        assert result.execute is True
        assert result.size == 100.0

    @pytest.mark.asyncio
    async def test_risk_manager_reduces_oversized_trade(self, risk_manager, mock_cache):
        """Caps trade at max_single_trade limit."""
        decision = AIDecision.approve(
            size=500.0,  # Exceeds max_single_trade of 300
            confidence=0.85,
            reasoning="Large trade",
        )

        result = await risk_manager.validate(decision)

        assert result.execute is True
        assert result.size == 300.0  # Capped at max_single_trade
        assert "Size adjusted by risk manager" in result.reasoning

    @pytest.mark.asyncio
    async def test_risk_manager_blocks_over_total_exposure(
        self, risk_manager, mock_cache
    ):
        """Blocks trade when total exposure is already at limit."""
        mock_cache.get_open_exposure = AsyncMock(return_value=2000.0)

        decision = AIDecision.approve(
            size=100.0,
            confidence=0.90,
            reasoning="Should be blocked due to exposure",
        )

        result = await risk_manager.validate(decision)

        assert result.execute is False
        assert result.size == 0.0
        assert "exposure_exceeded" in result.reasoning

    @pytest.mark.asyncio
    async def test_risk_manager_reduces_for_remaining_capacity(
        self, risk_manager, mock_cache
    ):
        """Reduces trade size to fit remaining exposure capacity."""
        mock_cache.get_open_exposure = AsyncMock(return_value=1900.0)

        decision = AIDecision.approve(
            size=200.0,  # Would exceed total exposure limit of 2000
            confidence=0.85,
            reasoning="Should be reduced",
        )

        result = await risk_manager.validate(decision)

        assert result.execute is True
        assert result.size == 100.0  # Reduced to remaining capacity
        assert "Size adjusted by risk manager" in result.reasoning

    @pytest.mark.asyncio
    async def test_risk_manager_applies_both_caps(self, risk_manager, mock_cache):
        """Applies both max_single_trade and exposure caps correctly."""
        mock_cache.get_open_exposure = AsyncMock(return_value=1800.0)

        decision = AIDecision.approve(
            size=500.0,  # Exceeds max_single_trade (300) and remaining capacity (200)
            confidence=0.85,
            reasoning="Should be double-capped",
        )

        result = await risk_manager.validate(decision)

        # First capped to max_single_trade (300), then to remaining capacity (200)
        assert result.execute is True
        assert result.size == 200.0
        assert "Size adjusted by risk manager" in result.reasoning

    @pytest.mark.asyncio
    async def test_risk_manager_preserves_decision_attributes(
        self, risk_manager, mock_cache
    ):
        """Preserves non-size attributes when adjusting trade."""
        decision = AIDecision.approve(
            size=500.0,
            confidence=0.95,
            reasoning="Original reasoning",
            urgency=Urgency.HIGH,
        )

        result = await risk_manager.validate(decision)

        assert result.execute is True
        assert result.confidence == 0.95
        assert result.urgency == Urgency.HIGH
        assert "Original reasoning" in result.reasoning

    @pytest.mark.asyncio
    async def test_risk_manager_with_positive_pnl(self, risk_manager, mock_cache):
        """Allows trades when daily P&L is positive."""
        mock_cache.get_daily_pnl = AsyncMock(return_value=200.0)

        decision = AIDecision.approve(
            size=100.0,
            confidence=0.85,
            reasoning="Profitable day",
        )

        result = await risk_manager.validate(decision)

        assert result.execute is True
        assert result.size == 100.0

    @pytest.mark.asyncio
    async def test_risk_manager_with_zero_exposure(self, risk_manager, mock_cache):
        """Handles zero current exposure correctly."""
        mock_cache.get_open_exposure = AsyncMock(return_value=0.0)

        decision = AIDecision.approve(
            size=250.0,
            confidence=0.85,
            reasoning="First trade of day",
        )

        result = await risk_manager.validate(decision)

        assert result.execute is True
        assert result.size == 250.0
