"""Tests for execution safety guards."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.execution.safety import SafetyGuard, LiveModeBlockedError


class TestSafetyGuard:
    """Tests for SafetyGuard."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.get = AsyncMock()
        cache.set = AsyncMock()
        return cache

    @pytest.mark.asyncio
    async def test_check_live_mode_without_credentials(self, mock_cache: MagicMock) -> None:
        """Test live mode blocked without credentials."""
        guard = SafetyGuard(cache=mock_cache)

        with pytest.raises(LiveModeBlockedError, match="credentials"):
            await guard.check_live_mode_allowed(
                has_credentials=False,
                live_confirmed=True,
            )

    @pytest.mark.asyncio
    async def test_check_live_mode_without_confirmation(self, mock_cache: MagicMock) -> None:
        """Test live mode blocked without confirmation."""
        guard = SafetyGuard(cache=mock_cache)

        with pytest.raises(LiveModeBlockedError, match="confirmation"):
            await guard.check_live_mode_allowed(
                has_credentials=True,
                live_confirmed=False,
            )

    @pytest.mark.asyncio
    async def test_check_live_mode_allowed(self, mock_cache: MagicMock) -> None:
        """Test live mode allowed with all requirements."""
        guard = SafetyGuard(cache=mock_cache)

        # Should not raise
        await guard.check_live_mode_allowed(
            has_credentials=True,
            live_confirmed=True,
        )

    @pytest.mark.asyncio
    async def test_emergency_stop_activates(self, mock_cache: MagicMock) -> None:
        """Test emergency stop activation."""
        guard = SafetyGuard(cache=mock_cache)

        await guard.activate_emergency_stop(reason="Manual trigger")

        mock_cache.set.assert_called()
        assert guard.is_stopped

    @pytest.mark.asyncio
    async def test_emergency_stop_blocks_execution(self, mock_cache: MagicMock) -> None:
        """Test that emergency stop blocks execution."""
        guard = SafetyGuard(cache=mock_cache)
        await guard.activate_emergency_stop(reason="Test")

        with pytest.raises(LiveModeBlockedError, match="emergency"):
            await guard.check_execution_allowed()

    @pytest.mark.asyncio
    async def test_reset_emergency_stop(self, mock_cache: MagicMock) -> None:
        """Test resetting emergency stop."""
        guard = SafetyGuard(cache=mock_cache)
        await guard.activate_emergency_stop(reason="Test")

        assert guard.is_stopped

        await guard.reset_emergency_stop()

        assert not guard.is_stopped

    @pytest.mark.asyncio
    async def test_first_live_trade_warning(self, mock_cache: MagicMock) -> None:
        """Test first live trade warning check."""
        guard = SafetyGuard(cache=mock_cache)
        mock_cache.get.return_value = None  # No previous live trades

        needs_warning = await guard.check_first_live_trade()
        assert needs_warning is True

        # Simulate acknowledgment
        await guard.acknowledge_first_live_trade()
        mock_cache.get.return_value = True

        needs_warning = await guard.check_first_live_trade()
        assert needs_warning is False
