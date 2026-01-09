"""Tests for bot runner."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.runner import BotRunner


def test_bot_runner_has_required_methods() -> None:
    """BotRunner should have start, stop, and run methods."""
    runner = BotRunner.__new__(BotRunner)
    assert hasattr(runner, "start")
    assert hasattr(runner, "stop")
    assert hasattr(runner, "run")


@pytest.mark.asyncio
async def test_bot_runner_initializes_components() -> None:
    """BotRunner should initialize all components."""
    with patch("polymind.runner.load_settings") as mock_settings:
        with patch("polymind.runner.Database") as mock_db:
            with patch("polymind.runner.create_cache") as mock_cache:
                mock_settings.return_value = MagicMock()
                mock_settings.return_value.database = MagicMock()
                mock_settings.return_value.redis = MagicMock()
                mock_settings.return_value.redis.url = "redis://localhost"
                mock_settings.return_value.log_level = "INFO"
                mock_settings.return_value.mode = "paper"
                mock_db.return_value = AsyncMock()
                mock_cache.return_value = AsyncMock()

                runner = BotRunner()
                await runner.start()

                mock_settings.assert_called_once()


@pytest.mark.asyncio
async def test_bot_runner_stop_closes_connections() -> None:
    """BotRunner stop should close all connections."""
    import asyncio

    runner = BotRunner.__new__(BotRunner)
    runner._db = AsyncMock()
    runner._cache = AsyncMock()
    runner._data_api = AsyncMock()
    runner._monitor = AsyncMock()
    runner._shutdown_event = asyncio.Event()
    runner._stopping = False

    await runner.stop()

    runner._db.close.assert_called_once()
    runner._cache.close.assert_called_once()
    assert runner._shutdown_event.is_set()
    assert runner._stopping is True


@pytest.mark.asyncio
async def test_bot_runner_is_running_property() -> None:
    """BotRunner should have is_running property."""
    import asyncio

    runner = BotRunner.__new__(BotRunner)
    runner._shutdown_event = asyncio.Event()

    # Not set means running
    assert runner.is_running is True

    # Set means stopped
    runner._shutdown_event.set()
    assert runner.is_running is False


@pytest.mark.asyncio
async def test_bot_runner_stop_handles_none_connections() -> None:
    """BotRunner stop should handle None connections gracefully."""
    import asyncio

    runner = BotRunner.__new__(BotRunner)
    runner._db = None
    runner._cache = None
    runner._data_api = None
    runner._monitor = None
    runner._shutdown_event = asyncio.Event()
    runner._stopping = False

    # Should not raise
    await runner.stop()

    assert runner._shutdown_event.is_set()
    assert runner._stopping is True


@pytest.mark.asyncio
async def test_bot_runner_stop_prevents_double_stop() -> None:
    """BotRunner stop should only run once (guard against double-stop)."""
    import asyncio

    runner = BotRunner.__new__(BotRunner)
    runner._db = AsyncMock()
    runner._cache = AsyncMock()
    runner._data_api = AsyncMock()
    runner._monitor = AsyncMock()
    runner._shutdown_event = asyncio.Event()
    runner._stopping = False

    # First stop
    await runner.stop()
    assert runner._stopping is True
    runner._db.close.assert_called_once()
    runner._cache.close.assert_called_once()

    # Reset mocks to verify they don't get called again
    runner._db.close.reset_mock()
    runner._cache.close.reset_mock()

    # Second stop should be a no-op
    await runner.stop()
    runner._db.close.assert_not_called()
    runner._cache.close.assert_not_called()
