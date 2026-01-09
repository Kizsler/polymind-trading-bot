"""Tests for health check utilities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.utils.health import HealthChecker, HealthStatus


def test_health_status_has_required_fields() -> None:
    """HealthStatus should have component statuses."""
    status = HealthStatus(
        healthy=True,
        database=True,
        cache=True,
        message="All systems operational",
    )
    assert status.healthy is True
    assert status.database is True
    assert status.cache is True


@pytest.mark.asyncio
async def test_health_checker_reports_healthy_when_all_ok() -> None:
    """HealthChecker should report healthy when all components work."""
    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=None)

    # Set up async context manager properly
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_db.session.return_value = mock_context

    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)

    checker = HealthChecker(db=mock_db, cache=mock_cache)
    status = await checker.check()

    assert status.healthy is True
    assert status.database is True
    assert status.cache is True
    assert status.message == "All systems operational"


@pytest.mark.asyncio
async def test_health_checker_reports_unhealthy_on_cache_failure() -> None:
    """HealthChecker should report unhealthy when cache fails."""
    mock_db = AsyncMock()
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(side_effect=Exception("Connection failed"))

    checker = HealthChecker(db=mock_db, cache=mock_cache)
    status = await checker.check()

    assert status.healthy is False
    assert status.cache is False


@pytest.mark.asyncio
async def test_health_checker_reports_unhealthy_on_database_failure() -> None:
    """HealthChecker should report unhealthy when database fails."""
    mock_db = AsyncMock()
    # Make session() context manager raise an exception
    mock_db.session.return_value.__aenter__.side_effect = Exception("DB connection failed")
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)

    checker = HealthChecker(db=mock_db, cache=mock_cache)
    status = await checker.check()

    assert status.healthy is False
    assert status.database is False


@pytest.mark.asyncio
async def test_health_checker_message_lists_failed_components() -> None:
    """HealthChecker message should list failed components."""
    mock_db = AsyncMock()
    mock_db.session.return_value.__aenter__.side_effect = Exception("DB error")
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))

    checker = HealthChecker(db=mock_db, cache=mock_cache)
    status = await checker.check()

    assert "database" in status.message
    assert "cache" in status.message
