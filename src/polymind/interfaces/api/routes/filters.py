"""Filters endpoints for market allow/deny lists."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from polymind.core.intelligence.filters import (
    FilterAction,
    FilterType,
    MarketFilterManager,
)
from polymind.interfaces.api.deps import get_filter_manager

router = APIRouter(prefix="/filters", tags=["filters"])


class FilterCreate(BaseModel):
    """Request to create a filter."""

    filter_type: FilterType
    value: str
    action: FilterAction


class FilterResponse(BaseModel):
    """Filter response."""

    id: int
    filter_type: FilterType
    value: str
    action: FilterAction


@router.get("", response_model=list[FilterResponse])
async def list_filters(
    manager: MarketFilterManager = Depends(get_filter_manager),
) -> list[dict]:
    """List all market filters."""
    filters = await manager.get_filters()
    return [
        {
            "id": f.id,
            "filter_type": f.filter_type,
            "value": f.value,
            "action": f.action,
        }
        for f in filters
    ]


@router.post("", response_model=FilterResponse, status_code=status.HTTP_201_CREATED)
async def add_filter(
    filter_data: FilterCreate,
    manager: MarketFilterManager = Depends(get_filter_manager),
) -> dict:
    """Add a new market filter."""
    created = await manager.add_filter(
        filter_type=filter_data.filter_type,
        value=filter_data.value,
        action=filter_data.action,
    )
    return {
        "id": created.id,
        "filter_type": created.filter_type,
        "value": created.value,
        "action": created.action,
    }


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_filter(
    filter_id: int,
    manager: MarketFilterManager = Depends(get_filter_manager),
) -> None:
    """Remove a market filter."""
    removed = await manager.remove_filter(filter_id=filter_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Filter not found")
