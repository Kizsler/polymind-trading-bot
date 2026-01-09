"""Tests for Redis cache layer."""

from unittest.mock import AsyncMock

import pytest

from polymind.storage.cache import Cache


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.mark.asyncio
async def test_cache_get_returns_none_when_missing(mock_redis):
    """Cache get should return None for missing keys."""
    cache = Cache(mock_redis)
    result = await cache.get("missing_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_stores_value(mock_redis):
    """Cache set should store JSON-serialized value."""
    cache = Cache(mock_redis)
    await cache.set("key", {"value": 123})
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_cache_get_daily_pnl_returns_float(mock_redis):
    """Daily PnL should return float."""
    mock_redis.get = AsyncMock(return_value=b"-150.50")
    cache = Cache(mock_redis)
    result = await cache.get_daily_pnl()
    assert result == -150.50


@pytest.mark.asyncio
async def test_cache_update_daily_pnl(mock_redis):
    """Should update daily PnL atomically."""
    mock_redis.incrbyfloat = AsyncMock(return_value=-50.0)
    cache = Cache(mock_redis)
    result = await cache.update_daily_pnl(-50.0)
    assert result == -50.0
