"""Markets endpoint for fetching market metadata."""

from fastapi import APIRouter, HTTPException
import httpx

from polymind.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# In-memory cache for market metadata to avoid repeated API calls
_market_cache: dict[str, dict] = {}

GAMMA_API_URL = "https://gamma-api.polymarket.com"


@router.get("/markets/{market_id}")
async def get_market(market_id: str) -> dict:
    """Get market metadata by condition ID.

    Args:
        market_id: The market's condition ID.

    Returns:
        Market metadata including title, end_date, etc.
    """
    # Check cache first
    if market_id in _market_cache:
        return _market_cache[market_id]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{GAMMA_API_URL}/markets/{market_id}")

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Market not found")

            response.raise_for_status()
            data = response.json()

            # Extract the fields we care about
            market_data = {
                "condition_id": data.get("conditionId") or data.get("condition_id") or market_id,
                "question": data.get("question", "Unknown Market"),
                "description": data.get("description", ""),
                "end_date": data.get("endDate") or data.get("end_date"),
                "resolution_date": data.get("resolutionDate") or data.get("resolution_date"),
                "active": data.get("active", False),
                "closed": data.get("closed", False),
                "image": data.get("image"),
                "icon": data.get("icon"),
            }

            # Cache it
            _market_cache[market_id] = market_data

            return market_data

    except httpx.HTTPError as e:
        logger.error("Failed to fetch market {}: {}", market_id, str(e))
        raise HTTPException(status_code=502, detail=f"Failed to fetch market data: {e}") from e


@router.post("/markets/batch")
async def get_markets_batch(market_ids: list[str]) -> dict[str, dict]:
    """Get multiple markets by condition IDs.

    Args:
        market_ids: List of market condition IDs.

    Returns:
        Dictionary mapping market_id to market metadata.
    """
    results: dict[str, dict] = {}

    for market_id in market_ids[:50]:  # Limit to 50 to avoid abuse
        # Check cache first
        if market_id in _market_cache:
            results[market_id] = _market_cache[market_id]
            continue

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{GAMMA_API_URL}/markets/{market_id}")

                if response.status_code == 404:
                    results[market_id] = {"error": "not_found", "question": market_id[:30] + "..."}
                    continue

                response.raise_for_status()
                data = response.json()

                market_data = {
                    "condition_id": data.get("conditionId") or data.get("condition_id") or market_id,
                    "question": data.get("question", "Unknown Market"),
                    "description": data.get("description", ""),
                    "end_date": data.get("endDate") or data.get("end_date"),
                    "resolution_date": data.get("resolutionDate") or data.get("resolution_date"),
                    "active": data.get("active", False),
                    "closed": data.get("closed", False),
                    "image": data.get("image"),
                    "icon": data.get("icon"),
                }

                # Cache it
                _market_cache[market_id] = market_data
                results[market_id] = market_data

        except httpx.HTTPError as e:
            logger.error("Failed to fetch market {}: {}", market_id, str(e))
            results[market_id] = {"error": "fetch_failed", "question": market_id[:30] + "..."}

    return results
