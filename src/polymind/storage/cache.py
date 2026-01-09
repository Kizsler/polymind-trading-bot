"""Redis cache layer for real-time state."""

import json
from typing import Any

from redis.asyncio import Redis


class Cache:
    """Redis cache for real-time trading state."""

    # Key prefixes
    PREFIX_WALLET = "wallet"
    PREFIX_MARKET = "market"
    PREFIX_RISK = "risk"
    PREFIX_SYSTEM = "system"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def close(self) -> None:
        """Close Redis connection."""
        try:
            await self.redis.aclose()
        except RuntimeError:
            # Ignore "Event loop is closed" on Windows
            pass

    # Generic operations

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value.decode() if isinstance(value, bytes) else value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in cache."""
        serialized = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        if ttl:
            result = await self.redis.setex(key, ttl, serialized)
            return bool(result)
        result = await self.redis.set(key, serialized)
        return bool(result)

    async def delete(self, key: str) -> int:
        """Delete a key from cache."""
        result = await self.redis.delete(key)
        return int(result)

    # Risk state

    async def get_daily_pnl(self) -> float:
        """Get current daily P&L."""
        value = await self.redis.get(f"{self.PREFIX_RISK}:daily_pnl")
        return float(value) if value else 0.0

    async def update_daily_pnl(self, delta: float) -> float:
        """Update daily P&L atomically."""
        result = await self.redis.incrbyfloat(f"{self.PREFIX_RISK}:daily_pnl", delta)
        return float(result)

    async def reset_daily_pnl(self) -> None:
        """Reset daily P&L to zero."""
        await self.redis.set(f"{self.PREFIX_RISK}:daily_pnl", "0.0")

    async def get_open_exposure(self) -> float:
        """Get current open exposure."""
        value = await self.redis.get(f"{self.PREFIX_RISK}:open_exposure")
        return float(value) if value else 0.0

    async def update_open_exposure(self, delta: float) -> float:
        """Update open exposure atomically."""
        key = f"{self.PREFIX_RISK}:open_exposure"
        result = await self.redis.incrbyfloat(key, delta)
        return float(result)

    # System state

    async def get_mode(self) -> str:
        """Get current trading mode."""
        value = await self.redis.get(f"{self.PREFIX_SYSTEM}:mode")
        return value.decode() if value else "paper"

    async def set_mode(self, mode: str) -> None:
        """Set trading mode."""
        await self.redis.set(f"{self.PREFIX_SYSTEM}:mode", mode)

    # Wallet state

    async def set_wallet_last_trade(self, address: str, trade_id: int) -> None:
        """Record last trade for a wallet."""
        await self.redis.set(
            f"{self.PREFIX_WALLET}:{address}:last_trade", str(trade_id)
        )

    async def get_wallet_last_trade(self, address: str) -> int | None:
        """Get last trade ID for a wallet."""
        value = await self.redis.get(f"{self.PREFIX_WALLET}:{address}:last_trade")
        return int(value) if value else None

    # Market state

    async def set_market_price(self, market_id: str, price: float) -> None:
        """Cache current market price."""
        await self.redis.setex(
            f"{self.PREFIX_MARKET}:{market_id}:price", 60, str(price)  # 1 minute TTL
        )

    async def get_market_price(self, market_id: str) -> float | None:
        """Get cached market price."""
        value = await self.redis.get(f"{self.PREFIX_MARKET}:{market_id}:price")
        return float(value) if value else None


async def create_cache(redis_url: str) -> Cache:
    """Create a cache instance."""
    redis = Redis.from_url(redis_url)
    return Cache(redis)
