"""Health check endpoint."""

from fastapi import APIRouter, Depends

from polymind import __version__
from polymind.interfaces.api.deps import get_cache, get_db
from polymind.storage.cache import Cache
from polymind.storage.database import Database
from polymind.utils.health import HealthChecker

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Basic health check.

    Returns:
        Health status with version info.
    """
    return {
        "status": "ok",
        "version": __version__,
    }


@router.get("/health/detailed")
async def detailed_health(
    db: Database = Depends(get_db),
    cache: Cache = Depends(get_cache),
) -> dict:
    """Detailed health check with component status.

    Returns:
        Detailed health status with component breakdown.
    """
    checker = HealthChecker(db=db, cache=cache)
    status = await checker.check()

    return {
        "status": "ok" if status.healthy else "degraded",
        "version": __version__,
        "components": {
            "database": "ok" if status.database else "error",
            "cache": "ok" if status.cache else "error",
        },
        "message": status.message,
    }
