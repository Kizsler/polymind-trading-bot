"""Arbitrage endpoints for cross-platform trading."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from polymind.interfaces.api.deps import get_arbitrage_service, get_db
from polymind.services.arbitrage import ArbitrageMonitorService
from polymind.storage.database import Database

router = APIRouter(prefix="/arbitrage", tags=["arbitrage"])


class MappingCreate(BaseModel):
    """Request to create a market mapping."""
    polymarket_id: str | None = None
    kalshi_id: str | None = None
    description: str | None = None
    active: bool = True


class MappingResponse(BaseModel):
    """Market mapping response."""
    id: int
    polymarket_id: str | None
    kalshi_id: str | None
    description: str | None
    active: bool
    created_at: str


class OpportunityResponse(BaseModel):
    """Arbitrage opportunity response."""
    polymarket_id: str
    kalshi_id: str
    spread: float
    direction: str
    poly_price: float
    kalshi_price: float
    confidence: float


class ScanResponse(BaseModel):
    """Manual scan response."""
    opportunities: list[OpportunityResponse]
    scanned_at: str


@router.get("/mappings", response_model=list[MappingResponse])
async def list_mappings(db: Database = Depends(get_db)) -> list[dict]:
    """List all market mappings."""
    mappings = await db.get_all_market_mappings()
    return [
        {
            "id": m.id,
            "polymarket_id": m.polymarket_id,
            "kalshi_id": m.kalshi_id,
            "description": m.description,
            "active": m.active,
            "created_at": m.created_at.isoformat(),
        }
        for m in mappings
    ]


@router.post("/mappings", response_model=MappingResponse, status_code=status.HTTP_201_CREATED)
async def add_mapping(
    mapping: MappingCreate,
    db: Database = Depends(get_db),
) -> dict:
    """Add a new market mapping."""
    if not mapping.polymarket_id and not mapping.kalshi_id:
        raise HTTPException(
            status_code=400,
            detail="At least one of polymarket_id or kalshi_id is required",
        )

    created = await db.add_market_mapping(
        polymarket_id=mapping.polymarket_id,
        kalshi_id=mapping.kalshi_id,
        description=mapping.description,
        active=mapping.active,
    )
    return {
        "id": created.id,
        "polymarket_id": created.polymarket_id,
        "kalshi_id": created.kalshi_id,
        "description": created.description,
        "active": created.active,
        "created_at": created.created_at.isoformat(),
    }


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_mapping(
    mapping_id: int,
    db: Database = Depends(get_db),
) -> None:
    """Remove a market mapping."""
    removed = await db.remove_market_mapping(mapping_id=mapping_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Mapping not found")


@router.get("/opportunities", response_model=list[OpportunityResponse])
async def list_opportunities(
    service: ArbitrageMonitorService = Depends(get_arbitrage_service),
) -> list[dict]:
    """List current arbitrage opportunities.

    Triggers a scan and returns any opportunities found.
    """
    opportunities = await service.scan()

    return [
        {
            "polymarket_id": opp["polymarket_id"],
            "kalshi_id": opp["kalshi_id"],
            "spread": opp["spread"],
            "direction": opp["direction"],
            "poly_price": opp["poly_price"],
            "kalshi_price": opp["kalshi_price"],
            "confidence": min(abs(opp["spread"]) / 0.10, 1.0),
        }
        for opp in opportunities
    ]


@router.post("/scan", response_model=ScanResponse)
async def scan_opportunities(
    service: ArbitrageMonitorService = Depends(get_arbitrage_service),
) -> dict:
    """Trigger manual scan for arbitrage opportunities."""
    opportunities = await service.scan()

    return {
        "opportunities": [
            {
                "polymarket_id": opp["polymarket_id"],
                "kalshi_id": opp["kalshi_id"],
                "spread": opp["spread"],
                "direction": opp["direction"],
                "poly_price": opp["poly_price"],
                "kalshi_price": opp["kalshi_price"],
                "confidence": min(abs(opp["spread"]) / 0.10, 1.0),
            }
            for opp in opportunities
        ],
        "scanned_at": datetime.now().isoformat(),
    }
