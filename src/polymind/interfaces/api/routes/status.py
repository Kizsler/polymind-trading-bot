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
    stopped = await cache.is_stopped()

    return {
        "version": __version__,
        "mode": mode,
        "daily_pnl": daily_pnl,
        "open_exposure": exposure,
        "wallet_count": len(wallets),
        "emergency_stop": stopped,
    }


@router.post("/emergency-stop")
async def emergency_stop(
    cache: Cache = Depends(get_cache),
) -> dict:
    """Activate emergency stop - halt all trading immediately."""
    await cache.set_emergency_stop(True)
    return {
        "success": True,
        "message": "Emergency stop activated. All trading halted.",
        "emergency_stop": True,
    }


@router.post("/resume-trading")
async def resume_trading(
    cache: Cache = Depends(get_cache),
) -> dict:
    """Resume trading after emergency stop."""
    await cache.set_emergency_stop(False)
    return {
        "success": True,
        "message": "Trading resumed.",
        "emergency_stop": False,
    }
