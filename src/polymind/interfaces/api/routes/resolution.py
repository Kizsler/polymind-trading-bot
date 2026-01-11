"""Resolution tracking endpoint for calculating PnL."""

import httpx
from fastapi import APIRouter, Depends

from polymind.interfaces.api.deps import get_db
from polymind.storage.database import Database
from polymind.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

CLOB_API_URL = "https://clob.polymarket.com"


def map_outcome_to_side(outcome: str) -> str:
    """Map CLOB outcome to our YES/NO side."""
    outcome_lower = outcome.lower()
    if outcome_lower in ("yes", "up"):
        return "YES"
    return "NO"


@router.post("/resolution/calculate")
async def calculate_pnl(db: Database = Depends(get_db)) -> dict:
    """Calculate PnL for all resolved markets.

    Fetches market resolution data and updates trade PnL.
    """
    # Get all trades with null PnL that were executed
    trades = await db.get_trades_without_pnl()

    if not trades:
        return {"message": "No trades pending PnL calculation", "updated": 0}

    # Get unique market IDs
    market_ids = list(set(t.market_id for t in trades))
    logger.info("Checking {} markets for resolution", len(market_ids))

    # Fetch market data for each
    market_data = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for market_id in market_ids:
            try:
                response = await client.get(f"{CLOB_API_URL}/markets/{market_id}")
                if response.status_code == 200:
                    market_data[market_id] = response.json()
            except Exception as e:
                logger.error("Failed to fetch market {}: {}", market_id, str(e))

    # Calculate PnL for resolved markets
    updates = []
    for trade in trades:
        market = market_data.get(trade.market_id)
        if not market:
            continue

        # Only process closed markets
        if not market.get("closed"):
            continue

        # Find the winner
        tokens = market.get("tokens", [])
        winning_side = None
        for token in tokens:
            if token.get("winner"):
                winning_side = map_outcome_to_side(token.get("outcome", ""))
                break

        if not winning_side:
            continue

        # Calculate PnL
        # If our side won: PnL = size * (1 - entry_price)
        # If our side lost: PnL = -size * entry_price
        entry_price = trade.price
        size = trade.executed_size or trade.size

        if trade.side == winning_side:
            pnl = size * (1.0 - entry_price)
        else:
            pnl = -size * entry_price

        updates.append({
            "trade_id": trade.id,
            "pnl": round(pnl, 4),
            "market_title": market.get("question", ""),
        })

    # Update trades in database
    updated_count = 0
    for update in updates:
        try:
            await db.update_trade_pnl(update["trade_id"], update["pnl"])
            updated_count += 1
        except Exception as e:
            logger.error("Failed to update trade {}: {}", update["trade_id"], str(e))

    total_pnl = sum(u["pnl"] for u in updates)

    return {
        "message": f"Calculated PnL for {updated_count} trades",
        "updated": updated_count,
        "total_pnl": round(total_pnl, 2),
        "details": updates[:20],  # Show first 20
    }


@router.get("/resolution/summary")
async def get_pnl_summary(db: Database = Depends(get_db)) -> dict:
    """Get PnL summary for all resolved trades."""
    summary = await db.get_pnl_summary()
    return summary
