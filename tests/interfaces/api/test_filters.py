"""Tests for API filters endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.deps import get_filter_manager
from polymind.interfaces.api.main import app
from polymind.core.intelligence.filters import (
    FilterType,
    FilterAction,
    MarketFilter,
)


@pytest.fixture
def mock_filter() -> MarketFilter:
    """Create mock filter."""
    return MarketFilter(
        id=1,
        filter_type=FilterType.MARKET_ID,
        value="market_abc",
        action=FilterAction.DENY,
    )


@pytest.fixture
def mock_filter_manager(mock_filter: MarketFilter) -> MagicMock:
    """Mock filter manager."""
    manager = MagicMock()
    manager.get_filters = AsyncMock(return_value=[mock_filter])
    manager.add_filter = AsyncMock(return_value=mock_filter)
    manager.remove_filter = AsyncMock(return_value=True)
    return manager


@pytest.mark.asyncio
async def test_filters_list_returns_filters(mock_filter_manager: MagicMock) -> None:
    """Filters list should return all filters."""
    app.dependency_overrides[get_filter_manager] = lambda: mock_filter_manager
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/filters")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["filter_type"] == "market_id"
        assert data[0]["value"] == "market_abc"
        assert data[0]["action"] == "deny"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_filters_add_creates_filter(mock_filter_manager: MagicMock) -> None:
    """Add filter should create and return filter."""
    app.dependency_overrides[get_filter_manager] = lambda: mock_filter_manager
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/filters",
                json={
                    "filter_type": "market_id",
                    "value": "market_abc",
                    "action": "deny",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["filter_type"] == "market_id"
        mock_filter_manager.add_filter.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_filters_add_category(mock_filter_manager: MagicMock) -> None:
    """Add filter should support category type."""
    category_filter = MarketFilter(
        id=2,
        filter_type=FilterType.CATEGORY,
        value="crypto",
        action=FilterAction.ALLOW,
    )
    mock_filter_manager.add_filter.return_value = category_filter

    app.dependency_overrides[get_filter_manager] = lambda: mock_filter_manager
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/filters",
                json={
                    "filter_type": "category",
                    "value": "crypto",
                    "action": "allow",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["filter_type"] == "category"
        assert data["action"] == "allow"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_filters_delete_removes_filter(mock_filter_manager: MagicMock) -> None:
    """Delete filter should remove filter."""
    app.dependency_overrides[get_filter_manager] = lambda: mock_filter_manager
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/filters/1")

        assert response.status_code == 204
        mock_filter_manager.remove_filter.assert_called_once_with(filter_id=1)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_filters_delete_not_found(mock_filter_manager: MagicMock) -> None:
    """Delete filter should return 404 if not found."""
    mock_filter_manager.remove_filter.return_value = False

    app.dependency_overrides[get_filter_manager] = lambda: mock_filter_manager
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/filters/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Filter not found"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_filters_invalid_filter_type(mock_filter_manager: MagicMock) -> None:
    """Add filter should reject invalid filter type."""
    app.dependency_overrides[get_filter_manager] = lambda: mock_filter_manager
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/filters",
                json={
                    "filter_type": "invalid_type",
                    "value": "test",
                    "action": "deny",
                },
            )

        assert response.status_code == 422  # Validation error
    finally:
        app.dependency_overrides.clear()
