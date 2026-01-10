"""Wallets endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from polymind.interfaces.api.deps import get_db
from polymind.interfaces.api.websocket import manager
from polymind.storage.database import Database

router = APIRouter(prefix="/wallets", tags=["wallets"])


class WalletCreate(BaseModel):
    """Request to create a wallet."""
    address: str
    alias: str | None = None


class WalletResponse(BaseModel):
    """Wallet response."""
    id: int
    address: str
    alias: str | None
    enabled: bool
    win_rate: float | None = None
    total_pnl: float | None = None


@router.get("", response_model=list[WalletResponse])
async def list_wallets(db: Database = Depends(get_db)) -> list[dict]:
    """List all tracked wallets."""
    wallets = await db.get_all_wallets()
    return [
        {
            "id": w.id,
            "address": w.address,
            "alias": w.alias,
            "enabled": w.enabled,
            "win_rate": w.metrics.win_rate if w.metrics else None,
            "total_pnl": w.metrics.total_pnl if w.metrics else None,
        }
        for w in wallets
    ]


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def add_wallet(
    wallet: WalletCreate,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
) -> dict:
    """Add a wallet to track."""
    created = await db.add_wallet(address=wallet.address, alias=wallet.alias)
    result = {
        "id": created.id,
        "address": created.address,
        "alias": created.alias,
        "enabled": created.enabled,
        "win_rate": None,
        "total_pnl": None,
    }

    # Broadcast wallet added to WebSocket clients
    background_tasks.add_task(manager.broadcast, "wallet", {"action": "added", "wallet": result})

    return result


@router.delete("/{address}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_wallet(
    address: str,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
) -> None:
    """Remove a wallet from tracking."""
    removed = await db.remove_wallet(address=address)
    if not removed:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # Broadcast wallet removed to WebSocket clients
    background_tasks.add_task(manager.broadcast, "wallet", {"action": "removed", "address": address})
