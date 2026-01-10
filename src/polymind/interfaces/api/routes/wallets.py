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


class WalletDetailResponse(BaseModel):
    """Detailed wallet response with metrics and controls."""
    id: int
    address: str
    alias: str | None
    enabled: bool
    scale_factor: float
    max_trade_size: float | None
    min_confidence: float
    win_rate: float | None = None
    avg_roi: float | None = None
    total_trades: int = 0
    total_pnl: float | None = None
    created_at: str


class WalletControlsResponse(BaseModel):
    """Wallet controls response."""
    address: str
    enabled: bool
    scale_factor: float
    max_trade_size: float | None
    min_confidence: float


class WalletControlsUpdate(BaseModel):
    """Request to update wallet controls."""
    enabled: bool | None = None
    scale_factor: float | None = None
    max_trade_size: float | None = None
    min_confidence: float | None = None


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


@router.get("/{address}", response_model=WalletDetailResponse)
async def get_wallet_detail(
    address: str,
    db: Database = Depends(get_db),
) -> dict:
    """Get detailed wallet information including metrics and controls."""
    wallet = await db.get_wallet_by_address(address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "id": wallet.id,
        "address": wallet.address,
        "alias": wallet.alias,
        "enabled": wallet.enabled,
        "scale_factor": wallet.scale_factor,
        "max_trade_size": wallet.max_trade_size,
        "min_confidence": wallet.min_confidence,
        "win_rate": wallet.metrics.win_rate if wallet.metrics else None,
        "avg_roi": wallet.metrics.avg_roi if wallet.metrics else None,
        "total_trades": wallet.metrics.total_trades if wallet.metrics else 0,
        "total_pnl": wallet.metrics.total_pnl if wallet.metrics else None,
        "created_at": wallet.created_at.isoformat(),
    }


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


@router.get("/{address}/controls", response_model=WalletControlsResponse)
async def get_wallet_controls(
    address: str,
    db: Database = Depends(get_db),
) -> dict:
    """Get wallet control settings."""
    wallet = await db.get_wallet_by_address(address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "address": wallet.address,
        "enabled": wallet.enabled,
        "scale_factor": wallet.scale_factor,
        "max_trade_size": wallet.max_trade_size,
        "min_confidence": wallet.min_confidence,
    }


@router.put("/{address}/controls", response_model=WalletControlsResponse)
@router.patch("/{address}/controls", response_model=WalletControlsResponse)
async def update_wallet_controls(
    address: str,
    controls: WalletControlsUpdate,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
) -> dict:
    """Update wallet control settings."""
    wallet = await db.get_wallet_by_address(address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # Build update dict from non-None values
    updates = {k: v for k, v in controls.model_dump().items() if v is not None}

    if updates:
        await db.update_wallet_controls(address, updates)
        # Refresh wallet data
        wallet = await db.get_wallet_by_address(address)

    result = {
        "address": wallet.address,
        "enabled": wallet.enabled,
        "scale_factor": wallet.scale_factor,
        "max_trade_size": wallet.max_trade_size,
        "min_confidence": wallet.min_confidence,
    }

    # Broadcast wallet updated to WebSocket clients
    background_tasks.add_task(manager.broadcast, "wallet", {"action": "controls_updated", **result})

    return result
