"""FastAPI dependency injection."""

from polymind.config.settings import Settings, load_settings
from polymind.storage.cache import Cache, create_cache
from polymind.storage.database import Database

_db: Database | None = None
_cache: Cache | None = None
_settings: Settings | None = None


async def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


async def get_db() -> Database:
    """Get database connection."""
    global _db
    if _db is None:
        settings = await get_settings()
        _db = Database(settings)
    return _db


async def get_cache() -> Cache:
    """Get cache connection."""
    global _cache
    if _cache is None:
        settings = await get_settings()
        _cache = await create_cache(settings.redis.url)
    return _cache
