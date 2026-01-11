"""FastAPI application setup."""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from polymind import __version__
from polymind.interfaces.api.routes import arbitrage, filters, health, markets, orders, settings, status, trades, wallets
from polymind.interfaces.api.websocket import manager
from polymind.utils.errors import PolymindError
from polymind.utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="PolyMind API",
    description="AI-powered prediction market trading bot API",
    version=__version__,
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(arbitrage.router)
app.include_router(filters.router)
app.include_router(health.router)
app.include_router(markets.router)
app.include_router(orders.router)
app.include_router(settings.router)
app.include_router(status.router)
app.include_router(trades.router)
app.include_router(wallets.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle any incoming messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
