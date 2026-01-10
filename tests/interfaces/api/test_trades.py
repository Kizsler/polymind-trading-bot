"""Tests for API trades endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.deps import get_db
from polymind.interfaces.api.main import app


def _make_mock_trade(
    id: int = 1,
    wallet_address: str = "0x123",
    wallet_alias: str | None = "TestWallet",
    market_id: str = "market-1",
    side: str = "YES",
    size: float = 100.0,
    price: float = 0.65,
    ai_decision: bool = True,
    executed: bool = True,
    pnl: float | None = 5.0,
) -> MagicMock:
    """Create a mock Trade object."""
    trade = MagicMock()
    trade.id = id
    trade.market_id = market_id
    trade.side = side
    trade.size = size
    trade.price = price
    trade.detected_at = datetime(2025, 1, 9, 12, 0, 0, tzinfo=UTC)
    trade.ai_decision = ai_decision
    trade.executed = executed
    trade.pnl = pnl

    trade.wallet = MagicMock()
    trade.wallet.address = wallet_address
    trade.wallet.alias = wallet_alias

    return trade


@pytest.fixture
def mock_db():
    """Mock database dependency."""
    db = AsyncMock()
    db.get_recent_trades = AsyncMock(return_value=[])
    return db


@pytest.mark.asyncio
async def test_trades_endpoint_returns_list(mock_db) -> None:
    """Trades endpoint should return a list."""
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/trades")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trades_endpoint_returns_trade_data(mock_db) -> None:
    """Trades endpoint should return properly formatted trades."""
    mock_db.get_recent_trades.return_value = [
        _make_mock_trade(
            id=1,
            wallet_address="0xabc",
            wallet_alias="CopyWhale",
            market_id="btc-above-50k",
            side="YES",
            size=250.0,
            price=0.72,
            ai_decision=True,
            executed=True,
            pnl=18.0,
        )
    ]

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/trades")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        trade = data[0]
        assert trade["id"] == "1"
        assert trade["wallet"] == "0xabc"
        assert trade["wallet_alias"] == "CopyWhale"
        assert trade["market_id"] == "btc-above-50k"
        assert trade["side"] == "YES"
        assert trade["size"] == 250.0
        assert trade["price"] == 0.72
        assert trade["decision"] == "COPY"
        assert trade["executed"] is True
        assert trade["pnl"] == 18.0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trades_endpoint_skip_decision(mock_db) -> None:
    """Trades with ai_decision=False should show decision=SKIP."""
    mock_db.get_recent_trades.return_value = [
        _make_mock_trade(ai_decision=False, executed=False, pnl=None)
    ]

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/trades")

        assert response.status_code == 200
        data = response.json()
        assert data[0]["decision"] == "SKIP"
        assert data[0]["executed"] is False
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trades_endpoint_limit_param(mock_db) -> None:
    """Trades endpoint should pass limit to database."""
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.get("/trades?limit=25")

        mock_db.get_recent_trades.assert_called_once_with(limit=25, executed_only=False)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trades_endpoint_executed_only_param(mock_db) -> None:
    """Trades endpoint should pass executed_only to database."""
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.get("/trades?executed_only=true")

        mock_db.get_recent_trades.assert_called_once_with(limit=50, executed_only=True)
    finally:
        app.dependency_overrides.clear()
