"""Settings endpoint."""

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from polymind.interfaces.api.deps import get_cache
from polymind.interfaces.api.websocket import manager
from polymind.storage.cache import Cache

router = APIRouter()


class SettingsUpdate(BaseModel):
    """Request body for updating settings."""

    trading_mode: str | None = None
    auto_trade: bool | None = None
    max_position_size: float | None = None
    max_daily_exposure: float | None = None
    ai_enabled: bool | None = None
    confidence_threshold: float | None = None
    min_probability: float | None = None
    max_probability: float | None = None
    daily_loss_limit: float | None = None
    starting_balance: float | None = None
    max_slippage: float | None = None
    copy_percentage: float | None = None


@router.get("/settings")
async def get_settings(cache: Cache = Depends(get_cache)) -> dict:
    """Get all bot settings."""
    return await cache.get_settings()


@router.put("/settings")
async def update_settings(
    updates: SettingsUpdate,
    background_tasks: BackgroundTasks,
    cache: Cache = Depends(get_cache),
) -> dict:
    """Update bot settings.

    Only provided fields will be updated.
    """
    # Filter out None values
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_dict:
        return await cache.get_settings()

    result = await cache.update_settings(update_dict)

    # Broadcast settings update to WebSocket clients
    background_tasks.add_task(manager.broadcast, "settings", result)

    return result
