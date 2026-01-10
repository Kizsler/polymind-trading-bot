"""Tests for auto-disable logic."""

import pytest

from polymind.core.intelligence.auto_disable import AutoDisableChecker


class TestAutoDisableChecker:
    """Tests for AutoDisableChecker."""

    @pytest.fixture
    def checker(self) -> AutoDisableChecker:
        """Create checker with default config."""
        return AutoDisableChecker(
            min_confidence=0.3,
            max_drawdown=-0.20,
            inactive_days=30,
        )

    @pytest.mark.asyncio
    async def test_should_disable_low_confidence(self, checker: AutoDisableChecker) -> None:
        """Test disable on low confidence."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.2,
            drawdown_7d=-0.10,
            last_trade_days_ago=5,
        )
        assert result.should_disable is True
        assert "confidence" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_should_disable_high_drawdown(self, checker: AutoDisableChecker) -> None:
        """Test disable on high drawdown."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.5,
            drawdown_7d=-0.25,
            last_trade_days_ago=5,
        )
        assert result.should_disable is True
        assert "drawdown" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_should_disable_inactive(self, checker: AutoDisableChecker) -> None:
        """Test disable on inactivity."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.5,
            drawdown_7d=-0.05,
            last_trade_days_ago=45,
        )
        assert result.should_disable is True
        assert "inactive" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_should_not_disable_healthy(self, checker: AutoDisableChecker) -> None:
        """Test no disable for healthy wallet."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.7,
            drawdown_7d=-0.05,
            last_trade_days_ago=5,
        )
        assert result.should_disable is False
        assert result.reason is None

    @pytest.mark.asyncio
    async def test_boundary_confidence(self, checker: AutoDisableChecker) -> None:
        """Test exact boundary on confidence threshold."""
        # Exactly at threshold should not disable
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.3,
            drawdown_7d=-0.10,
            last_trade_days_ago=5,
        )
        assert result.should_disable is False

    @pytest.mark.asyncio
    async def test_boundary_drawdown(self, checker: AutoDisableChecker) -> None:
        """Test exact boundary on drawdown threshold."""
        # Exactly at threshold should not disable
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.5,
            drawdown_7d=-0.20,
            last_trade_days_ago=5,
        )
        assert result.should_disable is False

    @pytest.mark.asyncio
    async def test_boundary_inactive(self, checker: AutoDisableChecker) -> None:
        """Test exact boundary on inactive days threshold."""
        # Exactly at threshold should not disable
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.5,
            drawdown_7d=-0.10,
            last_trade_days_ago=30,
        )
        assert result.should_disable is False

    @pytest.mark.asyncio
    async def test_priority_confidence_over_drawdown(self, checker: AutoDisableChecker) -> None:
        """Test confidence check happens first."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.1,  # Would trigger
            drawdown_7d=-0.30,  # Would also trigger
            last_trade_days_ago=5,
        )
        assert result.should_disable is True
        # Confidence is checked first
        assert "confidence" in result.reason.lower()
