"""Tests for API settings endpoint."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.deps import get_cache
from polymind.interfaces.api.main import app


@pytest.fixture
def mock_cache():
    """Mock cache dependency."""
    cache = AsyncMock()
    cache.get_settings = AsyncMock(
        return_value={
            "trading_mode": "paper",
            "auto_trade": True,
            "max_position_size": 100.0,
            "max_daily_exposure": 2000.0,
            "ai_enabled": True,
            "confidence_threshold": 0.70,
            "min_probability": 0.10,
            "max_probability": 0.90,
            "daily_loss_limit": 500.0,
        }
    )
    cache.update_settings = AsyncMock(
        return_value={
            "trading_mode": "live",
            "auto_trade": True,
            "max_position_size": 150.0,
            "max_daily_exposure": 2000.0,
            "ai_enabled": True,
            "confidence_threshold": 0.70,
            "min_probability": 0.10,
            "max_probability": 0.90,
            "daily_loss_limit": 500.0,
        }
    )
    return cache


@pytest.mark.asyncio
async def test_get_settings_returns_all_settings(mock_cache) -> None:
    """Settings endpoint should return all settings."""
    app.dependency_overrides[get_cache] = lambda: mock_cache
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/settings")

        assert response.status_code == 200
        data = response.json()
        assert "trading_mode" in data
        assert "auto_trade" in data
        assert "max_position_size" in data
        assert "ai_enabled" in data
        assert "confidence_threshold" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_settings_partial_update(mock_cache) -> None:
    """Settings endpoint should allow partial updates."""
    app.dependency_overrides[get_cache] = lambda: mock_cache
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/settings",
                json={"trading_mode": "live", "max_position_size": 150.0},
            )

        assert response.status_code == 200
        mock_cache.update_settings.assert_called_once_with(
            {"trading_mode": "live", "max_position_size": 150.0}
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_settings_empty_body(mock_cache) -> None:
    """Empty update body should just return current settings."""
    app.dependency_overrides[get_cache] = lambda: mock_cache
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put("/settings", json={})

        assert response.status_code == 200
        mock_cache.update_settings.assert_not_called()
    finally:
        app.dependency_overrides.clear()
