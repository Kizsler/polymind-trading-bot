"""Health check endpoint."""

from fastapi import APIRouter

from polymind import __version__

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Health check endpoint.

    Returns:
        Health status with version info.
    """
    return {
        "status": "ok",
        "version": __version__,
    }
