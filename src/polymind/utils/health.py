"""Health check utilities."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HealthStatus:
    """Health status of the system."""

    healthy: bool
    database: bool
    cache: bool
    message: str


class HealthChecker:
    """Check health of system components."""

    def __init__(self, db: Any, cache: Any) -> None:
        """Initialize health checker.

        Args:
            db: Database instance.
            cache: Cache instance.
        """
        self._db = db
        self._cache = cache

    async def check(self) -> HealthStatus:
        """Check health of all components.

        Returns:
            HealthStatus with component statuses.
        """
        db_ok = await self._check_database()
        cache_ok = await self._check_cache()

        healthy = db_ok and cache_ok

        if healthy:
            message = "All systems operational"
        else:
            failed = []
            if not db_ok:
                failed.append("database")
            if not cache_ok:
                failed.append("cache")
            message = f"Components unhealthy: {', '.join(failed)}"

        return HealthStatus(
            healthy=healthy,
            database=db_ok,
            cache=cache_ok,
            message=message,
        )

    async def _check_database(self) -> bool:
        """Check database connectivity."""
        try:
            # Try a simple query
            async with self._db.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database health check failed: {}", str(e))
            return False

    async def _check_cache(self) -> bool:
        """Check cache connectivity."""
        try:
            # Use ping if available, otherwise try set/get cycle
            if hasattr(self._cache, "redis") and hasattr(self._cache.redis, "ping"):
                await self._cache.redis.ping()
            else:
                # Fallback: do a set/get to verify connectivity
                await self._cache.set("health:check", "ok", ttl=10)
            return True
        except Exception as e:
            logger.error("Cache health check failed: {}", str(e))
            return False
