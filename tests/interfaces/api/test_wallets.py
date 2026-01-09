"""Tests for API wallets endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.deps import get_db
from polymind.interfaces.api.main import app


@pytest.fixture
def mock_wallet():
    """Create mock wallet."""
    wallet = MagicMock()
    wallet.id = 1
    wallet.address = "0x1234567890abcdef"
    wallet.alias = "whale.eth"
    wallet.enabled = True
    wallet.metrics = MagicMock()
    wallet.metrics.win_rate = 0.72
    wallet.metrics.total_pnl = 1500.0
    return wallet


@pytest.fixture
def mock_db(mock_wallet):
    """Mock database."""
    db = AsyncMock()
    db.get_all_wallets = AsyncMock(return_value=[mock_wallet])
    db.add_wallet = AsyncMock(return_value=mock_wallet)
    db.remove_wallet = AsyncMock(return_value=True)
    return db


@pytest.mark.asyncio
async def test_wallets_list_returns_wallets(mock_db) -> None:
    """Wallets list should return all tracked wallets."""
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/wallets")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["address"] == "0x1234567890abcdef"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_wallets_add_creates_wallet(mock_db) -> None:
    """Add wallet should create and return wallet."""
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/wallets",
                json={"address": "0x1234567890abcdef", "alias": "test"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["address"] == "0x1234567890abcdef"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_wallets_delete_removes_wallet(mock_db) -> None:
    """Delete wallet should remove wallet."""
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/wallets/0x1234567890abcdef")

        assert response.status_code == 204
    finally:
        app.dependency_overrides.clear()
