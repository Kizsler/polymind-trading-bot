# Phase 5: Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add production-ready logging, error handling, and the main bot runner to make PolyMind operational.

**Architecture:** Structured logging with loguru, centralized error handling, and a main runner that orchestrates all components.

**Tech Stack:** loguru (logging), structlog patterns, asyncio (runner)

---

## Task 1: Structured Logging Setup

**Files:**
- Create: `src/polymind/utils/__init__.py`
- Create: `src/polymind/utils/logging.py`
- Create: `tests/utils/__init__.py`
- Create: `tests/utils/test_logging.py`

**Step 1: Write failing test for logging**

Create `tests/utils/__init__.py`:
```python
"""Utility tests."""
```

Create `tests/utils/test_logging.py`:
```python
"""Tests for logging utilities."""

import pytest

from polymind.utils.logging import configure_logging, get_logger


def test_configure_logging_returns_logger() -> None:
    """configure_logging should return a configured logger."""
    logger = configure_logging(level="DEBUG")
    assert logger is not None


def test_get_logger_returns_child_logger() -> None:
    """get_logger should return a named logger."""
    logger = get_logger("test.module")
    assert logger is not None


def test_logger_has_expected_methods() -> None:
    """Logger should have standard logging methods."""
    logger = get_logger("test")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_logging.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement logging utilities**

Create `src/polymind/utils/__init__.py`:
```python
"""Utility modules for PolyMind."""

from polymind.utils.logging import configure_logging, get_logger

__all__ = ["configure_logging", "get_logger"]
```

Create `src/polymind/utils/logging.py`:
```python
"""Structured logging configuration."""

import sys
from typing import Any

from loguru import logger


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
) -> Any:
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        json_format: Use JSON format for structured logging.

    Returns:
        Configured logger instance.
    """
    # Remove default handler
    logger.remove()

    # Define format
    if json_format:
        log_format = "{message}"
        logger.add(
            sys.stderr,
            format=log_format,
            level=level,
            serialize=True,
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stderr,
            format=log_format,
            level=level,
            colorize=True,
        )

    return logger


def get_logger(name: str) -> Any:
    """Get a named logger.

    Args:
        name: Logger name (usually module name).

    Returns:
        Logger instance bound to the name.
    """
    return logger.bind(name=name)
```

Add `loguru` to pyproject.toml dependencies:
```toml
"loguru>=0.7.0",
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/utils/test_logging.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/polymind/utils/ tests/utils/ pyproject.toml
git commit -m "feat: add structured logging with loguru"
```

---

## Task 2: Add Logging to Core Components

**Files:**
- Modify: `src/polymind/core/brain/orchestrator.py`
- Modify: `src/polymind/core/risk/manager.py`
- Modify: `src/polymind/core/execution/paper.py`

**Step 1: Add logging to DecisionBrain**

Update `src/polymind/core/brain/orchestrator.py` to add logging:

```python
"""Decision brain orchestrator."""

from typing import Protocol

from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision
from polymind.core.execution.paper import ExecutionResult
from polymind.data.models import TradeSignal
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


# ... existing Protocol definitions ...


class DecisionBrain:
    """Orchestrates the AI decision pipeline."""

    def __init__(
        self,
        context_builder: ContextBuilderProtocol,
        claude_client: ClaudeClientProtocol,
        risk_manager: RiskManagerProtocol,
        executor: ExecutorProtocol,
    ) -> None:
        """Initialize the decision brain."""
        self._context_builder = context_builder
        self._claude = claude_client
        self._risk = risk_manager
        self._executor = executor

    async def process(self, signal: TradeSignal) -> ExecutionResult:
        """Process a trade signal through the decision pipeline."""
        logger.info(
            "Processing signal",
            wallet=signal.wallet[:10],
            market=signal.market_id,
            side=signal.side,
            size=signal.size,
        )

        # Build context
        context = await self._context_builder.build(signal)
        logger.debug("Context built", wallet=signal.wallet[:10])

        # Get AI decision
        decision = await self._claude.evaluate(context)
        logger.info(
            "AI decision",
            execute=decision.execute,
            size=decision.size,
            confidence=decision.confidence,
        )

        # Validate with risk manager
        validated = await self._risk.validate(decision)

        if not validated.execute:
            logger.warning(
                "Trade rejected by risk manager",
                reason=validated.reasoning,
            )
            return ExecutionResult(
                success=False,
                executed_size=0.0,
                executed_price=0.0,
                paper_mode=True,
                message=validated.reasoning,
            )

        # Execute trade
        result = await self._executor.execute(signal, validated)
        logger.info(
            "Trade executed",
            success=result.success,
            size=result.executed_size,
            paper_mode=result.paper_mode,
        )

        return result
```

**Step 2: Add logging to RiskManager**

Update `src/polymind/core/risk/manager.py` to add logging at key decision points.

**Step 3: Add logging to PaperExecutor**

Update `src/polymind/core/execution/paper.py` to add logging for executions.

**Step 4: Run tests**

Run: `pytest tests/core/ -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/polymind/core/
git commit -m "feat: add logging to core components"
```

---

## Task 3: Error Handling Middleware

**Files:**
- Create: `src/polymind/utils/errors.py`
- Modify: `src/polymind/interfaces/api/main.py`
- Create: `tests/utils/test_errors.py`

**Step 1: Write failing test**

Create `tests/utils/test_errors.py`:
```python
"""Tests for error handling utilities."""

import pytest

from polymind.utils.errors import PolymindError, TradeError, RiskError, ConfigError


def test_polymind_error_is_exception() -> None:
    """PolymindError should be an Exception."""
    error = PolymindError("test error")
    assert isinstance(error, Exception)
    assert str(error) == "test error"


def test_trade_error_inherits_from_polymind_error() -> None:
    """TradeError should inherit from PolymindError."""
    error = TradeError("trade failed")
    assert isinstance(error, PolymindError)


def test_risk_error_inherits_from_polymind_error() -> None:
    """RiskError should inherit from PolymindError."""
    error = RiskError("risk limit exceeded")
    assert isinstance(error, PolymindError)


def test_config_error_inherits_from_polymind_error() -> None:
    """ConfigError should inherit from PolymindError."""
    error = ConfigError("invalid config")
    assert isinstance(error, PolymindError)
```

**Step 2: Implement error classes**

Create `src/polymind/utils/errors.py`:
```python
"""Custom exception classes for PolyMind."""


class PolymindError(Exception):
    """Base exception for all PolyMind errors."""

    pass


class TradeError(PolymindError):
    """Error during trade execution."""

    pass


class RiskError(PolymindError):
    """Risk limit or validation error."""

    pass


class ConfigError(PolymindError):
    """Configuration error."""

    pass


class DataError(PolymindError):
    """Data fetching or processing error."""

    pass


class APIError(PolymindError):
    """External API error."""

    pass
```

Update `src/polymind/utils/__init__.py`:
```python
"""Utility modules for PolyMind."""

from polymind.utils.errors import (
    APIError,
    ConfigError,
    DataError,
    PolymindError,
    RiskError,
    TradeError,
)
from polymind.utils.logging import configure_logging, get_logger

__all__ = [
    "configure_logging",
    "get_logger",
    "PolymindError",
    "TradeError",
    "RiskError",
    "ConfigError",
    "DataError",
    "APIError",
]
```

**Step 3: Add API error handler**

Update `src/polymind/interfaces/api/main.py`:
```python
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
    logger.error("API error", error=str(exc), path=request.url.path)
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
    logger.exception("Unexpected error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# Include routers
app.include_router(health.router)
app.include_router(status.router)
app.include_router(wallets.router)
```

**Step 4: Run tests**

Run: `pytest tests/utils/test_errors.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/polymind/utils/ src/polymind/interfaces/api/main.py tests/utils/
git commit -m "feat: add error handling with custom exceptions"
```

---

## Task 4: Main Bot Runner

**Files:**
- Create: `src/polymind/runner.py`
- Create: `tests/test_runner.py`
- Modify: `src/polymind/interfaces/cli/main.py`

**Step 1: Write failing test**

Create `tests/test_runner.py`:
```python
"""Tests for bot runner."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.runner import BotRunner


def test_bot_runner_has_required_methods() -> None:
    """BotRunner should have start, stop, and run methods."""
    runner = BotRunner.__new__(BotRunner)
    assert hasattr(runner, "start")
    assert hasattr(runner, "stop")
    assert hasattr(runner, "run")


@pytest.mark.asyncio
async def test_bot_runner_initializes_components() -> None:
    """BotRunner should initialize all components."""
    with patch("polymind.runner.load_settings") as mock_settings:
        with patch("polymind.runner.Database") as mock_db:
            with patch("polymind.runner.create_cache") as mock_cache:
                mock_settings.return_value = MagicMock()
                mock_settings.return_value.database = MagicMock()
                mock_settings.return_value.redis = MagicMock()
                mock_settings.return_value.redis.url = "redis://localhost"
                mock_cache.return_value = AsyncMock()

                runner = BotRunner()
                await runner.start()

                mock_settings.assert_called_once()


@pytest.mark.asyncio
async def test_bot_runner_stop_closes_connections() -> None:
    """BotRunner stop should close all connections."""
    runner = BotRunner.__new__(BotRunner)
    runner._db = AsyncMock()
    runner._cache = AsyncMock()
    runner._running = True

    await runner.stop()

    runner._db.close.assert_called_once()
    runner._cache.close.assert_called_once()
    assert runner._running is False
```

**Step 2: Implement bot runner**

Create `src/polymind/runner.py`:
```python
"""Main bot runner for PolyMind."""

import asyncio
import signal
from typing import Any

from polymind.config.settings import Settings, load_settings
from polymind.storage.cache import Cache, create_cache
from polymind.storage.database import Database
from polymind.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


class BotRunner:
    """Main bot runner that orchestrates all components."""

    def __init__(self) -> None:
        """Initialize the bot runner."""
        self._settings: Settings | None = None
        self._db: Database | None = None
        self._cache: Cache | None = None
        self._running: bool = False

    async def start(self) -> None:
        """Start the bot and initialize all components."""
        logger.info("Starting PolyMind...")

        # Load settings
        self._settings = load_settings()

        # Configure logging
        configure_logging(level=self._settings.log_level)

        # Initialize database
        self._db = Database(self._settings)
        await self._db.create_tables()
        logger.info("Database connected")

        # Initialize cache
        self._cache = await create_cache(self._settings.redis.url)
        logger.info("Cache connected")

        # Set initial mode
        await self._cache.set_mode(self._settings.mode)
        logger.info(f"Mode set to: {self._settings.mode}")

        self._running = True
        logger.info("PolyMind started successfully")

    async def stop(self) -> None:
        """Stop the bot and close all connections."""
        logger.info("Stopping PolyMind...")
        self._running = False

        if self._cache:
            await self._cache.close()
            logger.info("Cache closed")

        if self._db:
            await self._db.close()
            logger.info("Database closed")

        logger.info("PolyMind stopped")

    async def run(self) -> None:
        """Run the main bot loop."""
        await self.start()

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        try:
            while self._running:
                # Main loop - process signals, check wallets, etc.
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    @property
    def is_running(self) -> bool:
        """Check if bot is running."""
        return self._running


def run_bot() -> None:
    """Entry point to run the bot."""
    runner = BotRunner()
    asyncio.run(runner.run())
```

**Step 3: Update CLI start command**

Update `src/polymind/interfaces/cli/main.py` to use the runner:
```python
@app.command()
def start() -> None:
    """Start the trading bot."""
    from polymind.runner import run_bot

    console.print(
        Panel.fit(
            "[bold green]Starting PolyMind...[/bold green]\n"
            "Press Ctrl+C to stop",
            title="PolyMind",
        )
    )

    try:
        run_bot()
    except KeyboardInterrupt:
        console.print("[yellow]Shutting down...[/yellow]")
```

**Step 4: Run tests**

Run: `pytest tests/test_runner.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/polymind/runner.py src/polymind/interfaces/cli/main.py tests/test_runner.py
git commit -m "feat: add main bot runner with graceful shutdown"
```

---

## Task 5: Health Checks and Monitoring

**Files:**
- Create: `src/polymind/utils/health.py`
- Modify: `src/polymind/interfaces/api/routes/health.py`
- Create: `tests/utils/test_health.py`

**Step 1: Write failing test**

Create `tests/utils/test_health.py`:
```python
"""Tests for health check utilities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.utils.health import HealthChecker, HealthStatus


def test_health_status_has_required_fields() -> None:
    """HealthStatus should have component statuses."""
    status = HealthStatus(
        healthy=True,
        database=True,
        cache=True,
        message="All systems operational",
    )
    assert status.healthy is True
    assert status.database is True
    assert status.cache is True


@pytest.mark.asyncio
async def test_health_checker_reports_healthy_when_all_ok() -> None:
    """HealthChecker should report healthy when all components work."""
    mock_db = AsyncMock()
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)

    checker = HealthChecker(db=mock_db, cache=mock_cache)
    status = await checker.check()

    assert status.healthy is True


@pytest.mark.asyncio
async def test_health_checker_reports_unhealthy_on_cache_failure() -> None:
    """HealthChecker should report unhealthy when cache fails."""
    mock_db = AsyncMock()
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(side_effect=Exception("Connection failed"))

    checker = HealthChecker(db=mock_db, cache=mock_cache)
    status = await checker.check()

    assert status.healthy is False
    assert status.cache is False
```

**Step 2: Implement health checker**

Create `src/polymind/utils/health.py`:
```python
"""Health check utilities."""

from dataclasses import dataclass
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HealthStatus:
    """Health status of the system."""

    healthy: bool
    database: bool
    cache: bool
    message: str


class HealthChecker:
    """Check health of system components."""

    def __init__(self, db: Any, cache: Any) -> None:
        """Initialize health checker.

        Args:
            db: Database instance.
            cache: Cache instance.
        """
        self._db = db
        self._cache = cache

    async def check(self) -> HealthStatus:
        """Check health of all components.

        Returns:
            HealthStatus with component statuses.
        """
        db_ok = await self._check_database()
        cache_ok = await self._check_cache()

        healthy = db_ok and cache_ok

        if healthy:
            message = "All systems operational"
        else:
            failed = []
            if not db_ok:
                failed.append("database")
            if not cache_ok:
                failed.append("cache")
            message = f"Components unhealthy: {', '.join(failed)}"

        return HealthStatus(
            healthy=healthy,
            database=db_ok,
            cache=cache_ok,
            message=message,
        )

    async def _check_database(self) -> bool:
        """Check database connectivity."""
        try:
            # Try a simple query
            async with self._db.session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False

    async def _check_cache(self) -> bool:
        """Check cache connectivity."""
        try:
            await self._cache.get("health:check")
            return True
        except Exception as e:
            logger.error("Cache health check failed", error=str(e))
            return False
```

Update `src/polymind/utils/__init__.py` to export health utilities.

**Step 3: Update health endpoint**

Update `src/polymind/interfaces/api/routes/health.py`:
```python
"""Health check endpoint."""

from fastapi import APIRouter, Depends

from polymind import __version__
from polymind.interfaces.api.deps import get_cache, get_db
from polymind.storage.cache import Cache
from polymind.storage.database import Database
from polymind.utils.health import HealthChecker

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Basic health check."""
    return {
        "status": "ok",
        "version": __version__,
    }


@router.get("/health/detailed")
async def detailed_health(
    db: Database = Depends(get_db),
    cache: Cache = Depends(get_cache),
) -> dict:
    """Detailed health check with component status."""
    checker = HealthChecker(db=db, cache=cache)
    status = await checker.check()

    return {
        "status": "ok" if status.healthy else "degraded",
        "version": __version__,
        "components": {
            "database": "ok" if status.database else "error",
            "cache": "ok" if status.cache else "error",
        },
        "message": status.message,
    }
```

**Step 4: Run tests**

Run: `pytest tests/utils/test_health.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/polymind/utils/ src/polymind/interfaces/api/routes/health.py tests/utils/
git commit -m "feat: add health checks with detailed component status"
```

---

## Task 6: Integration Tests for Polish Features

**Files:**
- Create: `tests/integration/test_polish.py`

**Step 1: Write integration tests**

Create `tests/integration/test_polish.py`:
```python
"""Integration tests for Phase 5 polish features."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.main import app as api_app
from polymind.utils.errors import PolymindError, TradeError, RiskError
from polymind.utils.health import HealthChecker, HealthStatus
from polymind.utils.logging import configure_logging, get_logger


# Logging Tests


def test_logging_configuration() -> None:
    """Logging should be configurable."""
    logger = configure_logging(level="DEBUG")
    assert logger is not None


def test_get_logger_creates_named_logger() -> None:
    """get_logger should create named loggers."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    assert logger1 is not None
    assert logger2 is not None


# Error Handling Tests


def test_error_hierarchy() -> None:
    """All custom errors should inherit from PolymindError."""
    assert issubclass(TradeError, PolymindError)
    assert issubclass(RiskError, PolymindError)


@pytest.mark.asyncio
async def test_api_handles_polymind_errors() -> None:
    """API should handle PolymindError gracefully."""
    from polymind.interfaces.api.deps import get_db

    mock_db = AsyncMock()
    mock_db.get_all_wallets = AsyncMock(side_effect=PolymindError("Test error"))

    api_app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/wallets")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
    finally:
        api_app.dependency_overrides.clear()


# Health Check Tests


@pytest.mark.asyncio
async def test_health_checker_integration() -> None:
    """HealthChecker should check all components."""
    mock_db = MagicMock()
    mock_db.session = MagicMock()

    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)

    checker = HealthChecker(db=mock_db, cache=mock_cache)

    # Mock the session context manager
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.session.return_value.__aexit__ = AsyncMock()

    status = await checker.check()

    assert isinstance(status, HealthStatus)
    assert status.cache is True


@pytest.mark.asyncio
async def test_detailed_health_endpoint() -> None:
    """Detailed health endpoint should return component status."""
    from polymind.interfaces.api.deps import get_cache, get_db

    mock_db = MagicMock()
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)

    # Mock session
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.session.return_value.__aexit__ = AsyncMock()

    api_app.dependency_overrides[get_db] = lambda: mock_db
    api_app.dependency_overrides[get_cache] = lambda: mock_cache

    try:
        async with AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        assert "database" in data["components"]
        assert "cache" in data["components"]
    finally:
        api_app.dependency_overrides.clear()
```

**Step 2: Run all tests**

Run: `pytest -v`
Expected: All tests pass

**Step 3: Run linting**

Run: `ruff check src tests`
Expected: All checks pass

**Step 4: Commit**

```bash
git add tests/integration/test_polish.py
git commit -m "test: add integration tests for polish features"
```

---

## Summary

Phase 5 Polish is complete when:

- [x] Structured logging with loguru configured
- [x] Core components have logging
- [x] Custom exception hierarchy defined
- [x] API error handlers in place
- [x] Main bot runner with graceful shutdown
- [x] Health checks for all components
- [x] All tests pass

**PolyMind is now production-ready for paper trading!**
