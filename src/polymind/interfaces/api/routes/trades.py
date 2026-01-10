"""Trades endpoint."""

from fastapi import APIRouter, Depends, Query

from polymind.interfaces.api.deps import get_db
from polymind.storage.database import Database

router = APIRouter()


@router.get("/trades")
async def get_trades(
    limit: int = Query(default=50, ge=1, le=500),
    executed_only: bool = Query(default=False),
    db: Database = Depends(get_db),
) -> list[dict]:
    """Get recent trades.

    Args:
        limit: Maximum number of trades to return (1-500)
        executed_only: If true, only return executed trades

    Returns:
        List of trades with wallet and decision info
    """
    trades = await db.get_recent_trades(limit=limit, executed_only=executed_only)

    return [
        {
            "id": str(trade.id),
            "wallet": trade.wallet.address if trade.wallet else None,
            "wallet_alias": trade.wallet.alias if trade.wallet else None,
            "market_id": trade.market_id,
            "side": trade.side,
            "size": trade.size,
            "price": trade.price,
            "timestamp": trade.detected_at.isoformat(),
            "decision": "COPY" if trade.ai_decision else "SKIP",
            "executed": trade.executed,
            "pnl": trade.pnl,
        }
        for trade in trades
    ]
