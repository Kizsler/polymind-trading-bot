"""Tests for API health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok() -> None:
    """Health endpoint should return status ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_endpoint_includes_version() -> None:
    """Health endpoint should include version."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    data = response.json()
    assert "version" in data
