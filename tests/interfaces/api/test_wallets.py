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
    wallet.scale_factor = 1.0
    wallet.max_trade_size = None
    wallet.min_confidence = 0.0
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
    db.get_wallet_by_address = AsyncMock(return_value=mock_wallet)
    db.update_wallet_controls = AsyncMock(return_value=True)
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


@pytest.mark.asyncio
async def test_get_wallet_controls(mock_db) -> None:
    """Get wallet controls should return control settings."""
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/wallets/0x1234567890abcdef/controls")

        assert response.status_code == 200
        data = response.json()
        assert data["address"] == "0x1234567890abcdef"
        assert data["enabled"] is True
        assert data["scale_factor"] == 1.0
        assert data["max_trade_size"] is None
        assert data["min_confidence"] == 0.0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_wallet_controls_not_found(mock_db) -> None:
    """Get wallet controls should return 404 if wallet not found."""
    mock_db.get_wallet_by_address = AsyncMock(return_value=None)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/wallets/0xunknown/controls")

        assert response.status_code == 404
        assert response.json()["detail"] == "Wallet not found"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_wallet_controls(mock_db, mock_wallet) -> None:
    """Update wallet controls should modify and return settings."""
    # Update mock to reflect new values after update
    updated_wallet = MagicMock()
    updated_wallet.address = "0x1234567890abcdef"
    updated_wallet.enabled = False
    updated_wallet.scale_factor = 0.5
    updated_wallet.max_trade_size = 100.0
    updated_wallet.min_confidence = 0.7

    # First call returns original, second returns updated
    mock_db.get_wallet_by_address = AsyncMock(
        side_effect=[mock_wallet, updated_wallet]
    )

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/wallets/0x1234567890abcdef/controls",
                json={
                    "enabled": False,
                    "scale_factor": 0.5,
                    "max_trade_size": 100.0,
                    "min_confidence": 0.7,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["scale_factor"] == 0.5
        assert data["max_trade_size"] == 100.0
        assert data["min_confidence"] == 0.7
        mock_db.update_wallet_controls.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_wallet_controls_partial(mock_db, mock_wallet) -> None:
    """Update wallet controls should allow partial updates."""
    updated_wallet = MagicMock()
    updated_wallet.address = "0x1234567890abcdef"
    updated_wallet.enabled = True
    updated_wallet.scale_factor = 2.0
    updated_wallet.max_trade_size = None
    updated_wallet.min_confidence = 0.0

    mock_db.get_wallet_by_address = AsyncMock(
        side_effect=[mock_wallet, updated_wallet]
    )

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/wallets/0x1234567890abcdef/controls",
                json={"scale_factor": 2.0},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["scale_factor"] == 2.0
        # Other fields unchanged
        assert data["enabled"] is True
        mock_db.update_wallet_controls.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_wallet_controls_not_found(mock_db) -> None:
    """Update wallet controls should return 404 if wallet not found."""
    mock_db.get_wallet_by_address = AsyncMock(return_value=None)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/wallets/0xunknown/controls",
                json={"enabled": False},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Wallet not found"
    finally:
        app.dependency_overrides.clear()
