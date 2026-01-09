"""CLI context management for database and cache connections."""

from dataclasses import dataclass

from polymind.config.settings import Settings, load_settings
from polymind.storage.cache import Cache, create_cache
from polymind.storage.database import Database


@dataclass
class CLIContext:
    """Context holding CLI dependencies."""

    db: Database
    cache: Cache
    settings: Settings


_context: CLIContext | None = None


async def get_context() -> CLIContext:
    """Get or create CLI context with database and cache connections.

    Returns:
        CLIContext with active connections.
    """
    global _context

    if _context is None:
        settings = load_settings()
        db = Database(settings)
        cache = await create_cache(settings.redis.url)
        _context = CLIContext(db=db, cache=cache, settings=settings)

    return _context


async def close_context() -> None:
    """Close all connections in CLI context."""
    global _context

    if _context is not None:
        await _context.db.close()
        await _context.cache.close()
        _context = None
