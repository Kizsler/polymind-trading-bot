"""FastAPI dependency injection."""

from polymind.config.settings import Settings, load_settings
from polymind.core.intelligence.filters import MarketFilterManager
from polymind.data.kalshi.client import KalshiClient
from polymind.data.polymarket.client import PolymarketClient
from polymind.services.arbitrage import ArbitrageMonitorService
from polymind.storage.cache import Cache, create_cache
from polymind.storage.database import Database

_db: Database | None = None
_cache: Cache | None = None
_settings: Settings | None = None
_filter_manager: MarketFilterManager | None = None
_arbitrage_service: ArbitrageMonitorService | None = None
_kalshi_client: KalshiClient | None = None
_polymarket_client: PolymarketClient | None = None


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


async def get_filter_manager() -> MarketFilterManager:
    """Get filter manager."""
    global _filter_manager
    if _filter_manager is None:
        db = await get_db()
        _filter_manager = MarketFilterManager(db=db)
    return _filter_manager


async def get_arbitrage_service() -> ArbitrageMonitorService:
    """Get arbitrage service for manual scans."""
    global _arbitrage_service, _kalshi_client, _polymarket_client

    if _arbitrage_service is None:
        settings = await get_settings()

        if _kalshi_client is None:
            _kalshi_client = KalshiClient(
                api_key=settings.kalshi.api_key or None,
                private_key_path=settings.kalshi.private_key_path or None,
            )
        if _polymarket_client is None:
            _polymarket_client = PolymarketClient(settings=settings)

        db = await get_db()

        _arbitrage_service = ArbitrageMonitorService(
            kalshi_client=_kalshi_client,
            polymarket_client=_polymarket_client,
            db=db,
            min_spread=settings.arbitrage.min_spread,
            max_signal_size=settings.arbitrage.max_signal_size,
        )

    return _arbitrage_service
