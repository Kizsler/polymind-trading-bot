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

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None
    ) -> bool:
        """Set a value in cache."""
        serialized = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        if ttl:
            return await self.redis.setex(key, ttl, serialized)
        return await self.redis.set(key, serialized)

    async def delete(self, key: str) -> int:
        """Delete a key from cache."""
        return await self.redis.delete(key)

    # Risk state

    async def get_daily_pnl(self) -> float:
        """Get current daily P&L."""
        value = await self.redis.get(f"{self.PREFIX_RISK}:daily_pnl")
        return float(value) if value else 0.0

    async def update_daily_pnl(self, delta: float) -> float:
        """Update daily P&L atomically."""
        return await self.redis.incrbyfloat(f"{self.PREFIX_RISK}:daily_pnl", delta)

    async def reset_daily_pnl(self) -> None:
        """Reset daily P&L to zero."""
        await self.redis.set(f"{self.PREFIX_RISK}:daily_pnl", "0.0")

    async def get_open_exposure(self) -> float:
        """Get current open exposure."""
        value = await self.redis.get(f"{self.PREFIX_RISK}:open_exposure")
        return float(value) if value else 0.0

    async def update_open_exposure(self, delta: float) -> float:
        """Update open exposure atomically."""
        return await self.redis.incrbyfloat(f"{self.PREFIX_RISK}:open_exposure", delta)

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
            f"{self.PREFIX_WALLET}:{address}:last_trade",
            str(trade_id)
        )

    async def get_wallet_last_trade(self, address: str) -> int | None:
        """Get last trade ID for a wallet."""
        value = await self.redis.get(f"{self.PREFIX_WALLET}:{address}:last_trade")
        return int(value) if value else None

    # Market state

    async def set_market_price(self, market_id: str, price: float) -> None:
        """Cache current market price."""
        await self.redis.setex(
            f"{self.PREFIX_MARKET}:{market_id}:price",
            60,  # 1 minute TTL
            str(price)
        )

    async def get_market_price(self, market_id: str) -> float | None:
        """Get cached market price."""
        value = await self.redis.get(f"{self.PREFIX_MARKET}:{market_id}:price")
        return float(value) if value else None


async def create_cache(redis_url: str) -> Cache:
    """Create a cache instance."""
    redis = Redis.from_url(redis_url)
    return Cache(redis)
