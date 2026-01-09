"""Integration tests for Phase 5 polish features."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.main import app as api_app
from polymind.utils.errors import PolymindError, RiskError, TradeError
from polymind.utils.health import HealthChecker, HealthStatus
from polymind.utils.logging import configure_logging, get_logger

# Logging Tests


def test_logging_configuration() -> None:
    """Logging should be configurable."""
    logger = configure_logging(level="DEBUG")
    assert logger is not None


def test_get_logger_creates_named_logger() -> None:
    """get_logger should create named loggers."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    assert logger1 is not None
    assert logger2 is not None


# Error Handling Tests


def test_error_hierarchy() -> None:
    """All custom errors should inherit from PolymindError."""
    assert issubclass(TradeError, PolymindError)
    assert issubclass(RiskError, PolymindError)


@pytest.mark.asyncio
async def test_api_handles_polymind_errors() -> None:
    """API should handle PolymindError gracefully."""
    from polymind.interfaces.api.deps import get_db

    mock_db = AsyncMock()
    mock_db.get_all_wallets = AsyncMock(side_effect=PolymindError("Test error"))

    api_app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/wallets")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
    finally:
        api_app.dependency_overrides.clear()


# Health Check Tests


@pytest.mark.asyncio
async def test_health_checker_integration() -> None:
    """HealthChecker should check all components."""
    mock_db = MagicMock()
    mock_db.session = MagicMock()

    mock_cache = MagicMock()
    mock_cache.redis = MagicMock()
    mock_cache.redis.ping = AsyncMock(return_value=True)

    checker = HealthChecker(db=mock_db, cache=mock_cache)

    # Mock the session context manager
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.session.return_value.__aexit__ = AsyncMock()

    status = await checker.check()

    assert isinstance(status, HealthStatus)
    assert status.cache is True


@pytest.mark.asyncio
async def test_detailed_health_endpoint() -> None:
    """Detailed health endpoint should return component status."""
    from polymind.interfaces.api.deps import get_cache, get_db

    mock_db = MagicMock()
    mock_cache = MagicMock()
    mock_cache.redis = MagicMock()
    mock_cache.redis.ping = AsyncMock(return_value=True)

    # Mock session
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.session.return_value.__aexit__ = AsyncMock()

    api_app.dependency_overrides[get_db] = lambda: mock_db
    api_app.dependency_overrides[get_cache] = lambda: mock_cache

    try:
        async with AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        assert "database" in data["components"]
        assert "cache" in data["components"]
    finally:
        api_app.dependency_overrides.clear()


# Runner Tests


def test_runner_can_be_imported() -> None:
    """Bot runner should be importable."""
    from polymind.runner import BotRunner, run_bot
    assert BotRunner is not None
    assert run_bot is not None
