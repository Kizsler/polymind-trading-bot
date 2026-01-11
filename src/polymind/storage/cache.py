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

    # Emergency stop

    async def is_stopped(self) -> bool:
        """Check if emergency stop is active."""
        value = await self.redis.get(f"{self.PREFIX_SYSTEM}:emergency_stop")
        return value is not None and value.decode().lower() == "true"

    async def set_emergency_stop(self, stopped: bool) -> None:
        """Set emergency stop state.

        Args:
            stopped: True to stop all trading, False to resume.
        """
        await self.redis.set(
            f"{self.PREFIX_SYSTEM}:emergency_stop",
            "true" if stopped else "false",
        )

    # Settings

    async def get_settings(self) -> dict:
        """Get all bot settings."""
        defaults = {
            "trading_mode": "paper",
            "auto_trade": True,
            "max_position_size": 100.0,
            "max_daily_exposure": 2000.0,
            "ai_enabled": True,
            "confidence_threshold": 0.70,
            "min_probability": 0.10,
            "max_probability": 0.90,
            "daily_loss_limit": 500.0,
            "starting_balance": 1000.0,
            "max_slippage": 0.03,
            "copy_percentage": 1.0,
        }

        settings = {}
        for key, default in defaults.items():
            value = await self.redis.get(f"{self.PREFIX_SYSTEM}:settings:{key}")
            if value is None:
                settings[key] = default
            else:
                # Parse based on default type
                if isinstance(default, bool):
                    settings[key] = value.decode().lower() == "true"
                elif isinstance(default, float):
                    settings[key] = float(value)
                else:
                    settings[key] = value.decode() if isinstance(value, bytes) else value

        return settings

    async def update_settings(self, updates: dict) -> dict:
        """Update bot settings."""
        for key, value in updates.items():
            await self.redis.set(
                f"{self.PREFIX_SYSTEM}:settings:{key}",
                str(value).lower() if isinstance(value, bool) else str(value),
            )
        return await self.get_settings()

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
