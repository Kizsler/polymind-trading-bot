"""Tests for API status endpoint."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.deps import get_cache, get_db
from polymind.interfaces.api.main import app


@pytest.fixture
def mock_deps():
    """Mock API dependencies."""
    mock_cache = AsyncMock()
    mock_cache.get_mode = AsyncMock(return_value="paper")
    mock_cache.get_daily_pnl = AsyncMock(return_value=-50.0)
    mock_cache.get_open_exposure = AsyncMock(return_value=500.0)

    mock_db = AsyncMock()
    mock_db.get_all_wallets = AsyncMock(return_value=[])

    return {"cache": mock_cache, "db": mock_db}


@pytest.mark.asyncio
async def test_status_endpoint_returns_mode(mock_deps) -> None:
    """Status endpoint should return current mode."""
    app.dependency_overrides[get_cache] = lambda: mock_deps["cache"]
    app.dependency_overrides[get_db] = lambda: mock_deps["db"]
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "paper"
        assert "daily_pnl" in data
    finally:
        app.dependency_overrides.clear()
