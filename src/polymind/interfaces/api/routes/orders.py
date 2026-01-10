"""Orders endpoints for order lifecycle tracking."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from polymind.interfaces.api.deps import get_db
from polymind.storage.database import Database

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderResponse(BaseModel):
    """Order response."""
    id: int
    external_id: str | None
    signal_id: str | None
    market_id: str
    side: str
    status: str
    requested_size: float
    filled_size: float
    requested_price: float
    filled_price: float | None
    attempts: int
    max_attempts: int
    failure_reason: str | None
    created_at: str
    updated_at: str


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    db: Database = Depends(get_db),
) -> list[dict]:
    """List orders with optional status filter."""
    orders = await db.get_orders(status=status_filter, limit=limit)
    return [
        {
            "id": o.id,
            "external_id": o.external_id,
            "signal_id": o.signal_id,
            "market_id": o.market_id,
            "side": o.side,
            "status": o.status,
            "requested_size": o.requested_size,
            "filled_size": o.filled_size,
            "requested_price": o.requested_price,
            "filled_price": o.filled_price,
            "attempts": o.attempts,
            "max_attempts": o.max_attempts,
            "failure_reason": o.failure_reason,
            "created_at": o.created_at.isoformat(),
            "updated_at": o.updated_at.isoformat(),
        }
        for o in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: Database = Depends(get_db),
) -> dict:
    """Get a specific order by ID."""
    order = await db.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "id": order.id,
        "external_id": order.external_id,
        "signal_id": order.signal_id,
        "market_id": order.market_id,
        "side": order.side,
        "status": order.status,
        "requested_size": order.requested_size,
        "filled_size": order.filled_size,
        "requested_price": order.requested_price,
        "filled_price": order.filled_price,
        "attempts": order.attempts,
        "max_attempts": order.max_attempts,
        "failure_reason": order.failure_reason,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    }


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    db: Database = Depends(get_db),
) -> dict:
    """Cancel a pending or submitted order."""
    order = await db.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ("pending", "submitted"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status '{order.status}'",
        )

    updated = await db.update_order_status(order_id, "cancelled")

    return {
        "id": updated.id,
        "external_id": updated.external_id,
        "signal_id": updated.signal_id,
        "market_id": updated.market_id,
        "side": updated.side,
        "status": updated.status,
        "requested_size": updated.requested_size,
        "filled_size": updated.filled_size,
        "requested_price": updated.requested_price,
        "filled_price": updated.filled_price,
        "attempts": updated.attempts,
        "max_attempts": updated.max_attempts,
        "failure_reason": updated.failure_reason,
        "created_at": updated.created_at.isoformat(),
        "updated_at": updated.updated_at.isoformat(),
    }
