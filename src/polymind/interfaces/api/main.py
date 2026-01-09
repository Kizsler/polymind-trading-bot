"""FastAPI application setup."""

from fastapi import FastAPI

from polymind import __version__
from polymind.interfaces.api.routes import health

app = FastAPI(
    title="PolyMind API",
    description="AI-powered prediction market trading bot API",
    version=__version__,
)

# Include routers
app.include_router(health.router)
