"""FastAPI application setup."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from polymind import __version__
from polymind.interfaces.api.routes import health, status, wallets
from polymind.utils.errors import PolymindError
from polymind.utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="PolyMind API",
    description="AI-powered prediction market trading bot API",
    version=__version__,
)


@app.exception_handler(PolymindError)
async def polymind_exception_handler(
    request: Request,
    exc: PolymindError,
) -> JSONResponse:
    """Handle PolyMind exceptions."""
    logger.error("API error: {} path={}", str(exc), request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__},
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception("Unexpected error: {} path={}", str(exc), request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# Include routers
app.include_router(health.router)
app.include_router(status.router)
app.include_router(wallets.router)
