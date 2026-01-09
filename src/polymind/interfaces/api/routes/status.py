"""Status endpoint."""

from fastapi import APIRouter, Depends

from polymind import __version__
from polymind.interfaces.api.deps import get_cache, get_db
from polymind.storage.cache import Cache
from polymind.storage.database import Database

router = APIRouter()


@router.get("/status")
async def status(
    cache: Cache = Depends(get_cache),
    db: Database = Depends(get_db),
) -> dict:
    """Get bot status."""
    mode = await cache.get_mode()
    daily_pnl = await cache.get_daily_pnl()
    exposure = await cache.get_open_exposure()
    wallets = await db.get_all_wallets()

    return {
        "version": __version__,
        "mode": mode,
        "daily_pnl": daily_pnl,
        "open_exposure": exposure,
        "wallet_count": len(wallets),
    }
