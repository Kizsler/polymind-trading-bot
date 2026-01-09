# Phase 4: User Interfaces Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build user interfaces (CLI, API, Discord) to control and monitor the trading bot.

**Architecture:** CLI commands connect to database/cache for real data. FastAPI provides REST API for external integrations. Discord bot sends trade alerts and accepts commands.

**Tech Stack:** Typer + Rich (CLI), FastAPI + Pydantic (API), discord.py (Discord bot)

---

## Task 1: CLI Database Connection

**Files:**
- Create: `src/polymind/interfaces/cli/context.py`
- Modify: `src/polymind/interfaces/cli/main.py`
- Create: `tests/interfaces/cli/test_context.py`

**Step 1: Write failing test for CLI context**

Create `tests/interfaces/cli/test_context.py`:
```python
"""Tests for CLI context management."""

from unittest.mock import AsyncMock, patch

import pytest

from polymind.interfaces.cli.context import CLIContext, get_context


def test_cli_context_has_required_attributes() -> None:
    """CLI context should have db, cache, and settings."""
    context = CLIContext(
        db=AsyncMock(),
        cache=AsyncMock(),
        settings=AsyncMock(),
    )

    assert context.db is not None
    assert context.cache is not None
    assert context.settings is not None


@pytest.mark.asyncio
async def test_get_context_creates_connections() -> None:
    """get_context should create database and cache connections."""
    with patch("polymind.interfaces.cli.context.create_database") as mock_db:
        with patch("polymind.interfaces.cli.context.create_cache") as mock_cache:
            with patch("polymind.interfaces.cli.context.load_settings") as mock_settings:
                mock_db.return_value = AsyncMock()
                mock_cache.return_value = AsyncMock()
                mock_settings.return_value = AsyncMock()

                context = await get_context()

                assert context is not None
                mock_settings.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/interfaces/cli/test_context.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement CLI context**

Create `src/polymind/interfaces/cli/context.py`:
```python
"""CLI context management for database and cache connections."""

from dataclasses import dataclass
from typing import Any

from polymind.config.settings import Settings, load_settings
from polymind.storage.cache import Cache, create_cache
from polymind.storage.database import Database, create_database


@dataclass
class CLIContext:
    """Context holding CLI dependencies."""

    db: Database
    cache: Cache
    settings: Settings


_context: CLIContext | None = None


async def get_context() -> CLIContext:
    """Get or create CLI context with database and cache connections.

    Returns:
        CLIContext with active connections.
    """
    global _context

    if _context is None:
        settings = load_settings()
        db = await create_database(settings.database.url)
        cache = await create_cache(settings.redis.url)
        _context = CLIContext(db=db, cache=cache, settings=settings)

    return _context


async def close_context() -> None:
    """Close all connections in CLI context."""
    global _context

    if _context is not None:
        await _context.db.close()
        await _context.cache.close()
        _context = None
```

Update `src/polymind/interfaces/cli/__init__.py`:
```python
"""CLI interface for PolyMind."""

from polymind.interfaces.cli.context import CLIContext, close_context, get_context
from polymind.interfaces.cli.main import app

__all__ = [
    "app",
    "CLIContext",
    "get_context",
    "close_context",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/interfaces/cli/test_context.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/polymind/interfaces/cli/ tests/interfaces/cli/
git commit -m "feat: add CLI context for database and cache connections"
```

---

## Task 2: Functional Wallets Commands

**Files:**
- Modify: `src/polymind/interfaces/cli/main.py`
- Create: `tests/interfaces/cli/test_wallets.py`

**Step 1: Write failing test for wallets commands**

Create `tests/interfaces/cli/test_wallets.py`:
```python
"""Tests for CLI wallet commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from polymind.interfaces.cli.main import app

runner = CliRunner()


@pytest.fixture
def mock_context():
    """Create mock CLI context."""
    context = MagicMock()
    context.db = AsyncMock()
    context.cache = AsyncMock()
    context.settings = MagicMock()
    return context


def test_wallets_list_shows_wallets(mock_context) -> None:
    """wallets list should show tracked wallets from database."""
    # Mock database returning wallets
    mock_wallet = MagicMock()
    mock_wallet.address = "0x1234567890abcdef"
    mock_wallet.alias = "whale.eth"
    mock_wallet.enabled = True

    mock_metrics = MagicMock()
    mock_metrics.win_rate = 0.72
    mock_metrics.total_pnl = 1500.0

    mock_wallet.metrics = mock_metrics

    mock_context.db.get_all_wallets = AsyncMock(return_value=[mock_wallet])

    with patch("polymind.interfaces.cli.main.get_context", return_value=mock_context):
        with patch("polymind.interfaces.cli.main.asyncio.run", side_effect=lambda coro: coro):
            result = runner.invoke(app, ["wallets", "list"])

    assert result.exit_code == 0
    assert "whale.eth" in result.stdout or "0x1234" in result.stdout


def test_wallets_add_creates_wallet(mock_context) -> None:
    """wallets add should create wallet in database."""
    mock_context.db.add_wallet = AsyncMock(return_value=MagicMock(id=1))

    with patch("polymind.interfaces.cli.main.get_context", return_value=mock_context):
        with patch("polymind.interfaces.cli.main.asyncio.run", side_effect=lambda coro: coro):
            result = runner.invoke(app, ["wallets", "add", "0x1234567890abcdef", "--alias", "test"])

    assert result.exit_code == 0
    assert "Added" in result.stdout or "added" in result.stdout


def test_wallets_remove_deletes_wallet(mock_context) -> None:
    """wallets remove should delete wallet from database."""
    mock_context.db.remove_wallet = AsyncMock(return_value=True)

    with patch("polymind.interfaces.cli.main.get_context", return_value=mock_context):
        with patch("polymind.interfaces.cli.main.asyncio.run", side_effect=lambda coro: coro):
            result = runner.invoke(app, ["wallets", "remove", "0x1234567890abcdef"])

    assert result.exit_code == 0
    assert "Removed" in result.stdout or "removed" in result.stdout
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/interfaces/cli/test_wallets.py -v`
Expected: FAIL (commands don't connect to database yet)

**Step 3: Update CLI wallet commands**

Update `src/polymind/interfaces/cli/main.py` - modify wallet commands to use database:

```python
"""PolyMind CLI application."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from polymind import __version__
from polymind.interfaces.cli.context import get_context

# Create Typer app
app = typer.Typer(
    name="polymind",
    help="AI-powered prediction market trading bot",
    no_args_is_help=True,
)

# Create subcommand groups
wallets_app = typer.Typer(help="Manage tracked wallets")
app.add_typer(wallets_app, name="wallets")

# Rich console for pretty output
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"PolyMind v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """PolyMind - AI-powered prediction market trading bot."""
    pass


@app.command()
def start() -> None:
    """Start the trading bot."""
    console.print(
        Panel.fit(
            "[bold green]Starting PolyMind...[/bold green]\n"
            "Mode: [yellow]paper[/yellow]\n"
            "Press Ctrl+C to stop",
            title="PolyMind",
        )
    )
    console.print("[dim]Bot start not yet implemented[/dim]")


@app.command()
def stop() -> None:
    """Stop the trading bot gracefully."""
    console.print("[yellow]Stopping PolyMind...[/yellow]")
    console.print("[green]Bot stopped[/green]")


@app.command()
def status() -> None:
    """Show current bot status."""

    async def _status() -> None:
        ctx = await get_context()

        mode = await ctx.cache.get_mode()
        daily_pnl = await ctx.cache.get_daily_pnl()
        wallets = await ctx.db.get_all_wallets()

        table = Table(title="PolyMind Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Version", __version__)
        table.add_row("Mode", mode)
        table.add_row("Status", "running" if mode != "paused" else "paused")
        table.add_row("Tracked Wallets", str(len(wallets)))
        table.add_row("Daily P&L", f"${daily_pnl:.2f}")

        console.print(table)

    asyncio.run(_status())


@app.command()
def pause() -> None:
    """Pause trading (emergency stop)."""

    async def _pause() -> None:
        ctx = await get_context()
        await ctx.cache.set_mode("paused")
        console.print("[bold red]PAUSING ALL TRADING[/bold red]")
        console.print("[yellow]Trading paused. Use 'polymind mode paper' or 'polymind mode live' to resume.[/yellow]")

    asyncio.run(_pause())


@app.command()
def mode(
    new_mode: str = typer.Argument(
        ...,
        help="Trading mode: paper, live, or paused",
    ),
) -> None:
    """Switch trading mode."""
    valid_modes = ["paper", "live", "paused"]
    if new_mode not in valid_modes:
        console.print(f"[red]Invalid mode. Choose from: {', '.join(valid_modes)}[/red]")
        raise typer.Exit(1)

    if new_mode == "live":
        typer.confirm(
            "Are you sure you want to enable LIVE trading with real money?",
            abort=True,
        )

    async def _set_mode() -> None:
        ctx = await get_context()
        await ctx.cache.set_mode(new_mode)
        console.print(f"[green]Mode set to: {new_mode}[/green]")

    asyncio.run(_set_mode())


@app.command()
def trades(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of trades to show"),
) -> None:
    """Show recent trades."""

    async def _trades() -> None:
        ctx = await get_context()
        recent_trades = await ctx.db.get_recent_trades(limit=limit)

        table = Table(title=f"Recent Trades (last {limit})")
        table.add_column("Time", style="dim")
        table.add_column("Wallet")
        table.add_column("Market")
        table.add_column("Side")
        table.add_column("Size")
        table.add_column("AI Decision")
        table.add_column("P&L")

        for trade in recent_trades:
            table.add_row(
                trade.detected_at.strftime("%Y-%m-%d %H:%M"),
                trade.wallet.alias or trade.wallet.address[:10] + "...",
                trade.market_id[:20] + "...",
                trade.side,
                f"${trade.size:.2f}",
                "✓" if trade.ai_decision else "✗",
                f"${trade.pnl:.2f}" if trade.pnl else "-",
            )

        console.print(table)
        if not recent_trades:
            console.print("[dim]No trades yet[/dim]")

    asyncio.run(_trades())


# Wallets subcommands


@wallets_app.command("list")
def wallets_list() -> None:
    """List all tracked wallets."""

    async def _list() -> None:
        ctx = await get_context()
        wallets = await ctx.db.get_all_wallets()

        table = Table(title="Tracked Wallets")
        table.add_column("Address", style="cyan")
        table.add_column("Alias")
        table.add_column("Enabled")
        table.add_column("Win Rate")
        table.add_column("Total P&L")

        for wallet in wallets:
            metrics = wallet.metrics
            table.add_row(
                wallet.address[:10] + "...",
                wallet.alias or "-",
                "✓" if wallet.enabled else "✗",
                f"{metrics.win_rate * 100:.1f}%" if metrics else "-",
                f"${metrics.total_pnl:.2f}" if metrics else "-",
            )

        console.print(table)
        if not wallets:
            console.print(
                "[dim]No wallets tracked. "
                "Use 'polymind wallets add <address>' to add one.[/dim]"
            )

    asyncio.run(_list())


@wallets_app.command("add")
def wallets_add(
    address: str = typer.Argument(..., help="Wallet address to track"),
    alias: str | None = typer.Option(None, "--alias", "-a", help="Friendly name"),
) -> None:
    """Add a wallet to track."""

    async def _add() -> None:
        ctx = await get_context()
        wallet = await ctx.db.add_wallet(address=address, alias=alias)
        display = alias or address[:10] + "..."
        console.print(f"[green]Added wallet: {display} (id={wallet.id})[/green]")

    asyncio.run(_add())


@wallets_app.command("remove")
def wallets_remove(
    address: str = typer.Argument(..., help="Wallet address to remove"),
) -> None:
    """Remove a wallet from tracking."""

    async def _remove() -> None:
        ctx = await get_context()
        removed = await ctx.db.remove_wallet(address=address)
        if removed:
            console.print(f"[yellow]Removed wallet: {address[:10]}...[/yellow]")
        else:
            console.print(f"[red]Wallet not found: {address[:10]}...[/red]")

    asyncio.run(_remove())


@wallets_app.command("enable")
def wallets_enable(
    address: str = typer.Argument(..., help="Wallet address to enable"),
) -> None:
    """Enable trading for a wallet."""

    async def _enable() -> None:
        ctx = await get_context()
        updated = await ctx.db.update_wallet(address=address, enabled=True)
        if updated:
            console.print(f"[green]Enabled wallet: {address[:10]}...[/green]")
        else:
            console.print(f"[red]Wallet not found: {address[:10]}...[/red]")

    asyncio.run(_enable())


@wallets_app.command("disable")
def wallets_disable(
    address: str = typer.Argument(..., help="Wallet address to disable"),
) -> None:
    """Disable trading for a wallet."""

    async def _disable() -> None:
        ctx = await get_context()
        updated = await ctx.db.update_wallet(address=address, enabled=False)
        if updated:
            console.print(f"[yellow]Disabled wallet: {address[:10]}...[/yellow]")
        else:
            console.print(f"[red]Wallet not found: {address[:10]}...[/red]")

    asyncio.run(_disable())


if __name__ == "__main__":
    app()
```

**Step 4: Add database methods**

We need to add helper methods to the Database class. Update `src/polymind/storage/database.py` to add:

```python
# Add these methods to the Database class

async def get_all_wallets(self) -> list[Wallet]:
    """Get all tracked wallets with their metrics."""
    async with self._session() as session:
        result = await session.execute(
            select(Wallet).options(selectinload(Wallet.metrics))
        )
        return list(result.scalars().all())


async def add_wallet(self, address: str, alias: str | None = None) -> Wallet:
    """Add a new wallet to track."""
    async with self._session() as session:
        wallet = Wallet(address=address, alias=alias)
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)
        return wallet


async def remove_wallet(self, address: str) -> bool:
    """Remove a wallet by address."""
    async with self._session() as session:
        result = await session.execute(
            select(Wallet).where(Wallet.address == address)
        )
        wallet = result.scalar_one_or_none()
        if wallet:
            await session.delete(wallet)
            await session.commit()
            return True
        return False


async def update_wallet(self, address: str, **kwargs) -> bool:
    """Update wallet fields."""
    async with self._session() as session:
        result = await session.execute(
            select(Wallet).where(Wallet.address == address)
        )
        wallet = result.scalar_one_or_none()
        if wallet:
            for key, value in kwargs.items():
                setattr(wallet, key, value)
            await session.commit()
            return True
        return False


async def get_recent_trades(self, limit: int = 10) -> list[Trade]:
    """Get recent trades with wallet info."""
    async with self._session() as session:
        result = await session.execute(
            select(Trade)
            .options(selectinload(Trade.wallet))
            .order_by(Trade.detected_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/interfaces/cli/test_wallets.py -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/polymind/interfaces/cli/ src/polymind/storage/database.py tests/interfaces/cli/
git commit -m "feat: connect CLI wallet commands to database"
```

---

## Task 3: FastAPI Backend Setup

**Files:**
- Create: `src/polymind/interfaces/api/__init__.py`
- Create: `src/polymind/interfaces/api/main.py`
- Create: `src/polymind/interfaces/api/routes/__init__.py`
- Create: `src/polymind/interfaces/api/routes/health.py`
- Create: `tests/interfaces/api/test_health.py`

**Step 1: Write failing test for health endpoint**

Create `tests/interfaces/api/__init__.py`:
```python
"""API tests."""
```

Create `tests/interfaces/api/test_health.py`:
```python
"""Tests for API health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok() -> None:
    """Health endpoint should return status ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_endpoint_includes_version() -> None:
    """Health endpoint should include version."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    data = response.json()
    assert "version" in data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/interfaces/api/test_health.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement FastAPI app and health endpoint**

Create `src/polymind/interfaces/api/__init__.py`:
```python
"""FastAPI REST API for PolyMind."""

from polymind.interfaces.api.main import app

__all__ = ["app"]
```

Create `src/polymind/interfaces/api/routes/__init__.py`:
```python
"""API routes."""
```

Create `src/polymind/interfaces/api/routes/health.py`:
```python
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
```

Create `src/polymind/interfaces/api/main.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/interfaces/api/test_health.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/polymind/interfaces/api/ tests/interfaces/api/
git commit -m "feat: add FastAPI app with health endpoint"
```

---

## Task 4: API Status and Wallets Endpoints

**Files:**
- Create: `src/polymind/interfaces/api/routes/status.py`
- Create: `src/polymind/interfaces/api/routes/wallets.py`
- Create: `src/polymind/interfaces/api/deps.py`
- Modify: `src/polymind/interfaces/api/main.py`
- Create: `tests/interfaces/api/test_status.py`
- Create: `tests/interfaces/api/test_wallets.py`

**Step 1: Write failing tests**

Create `tests/interfaces/api/test_status.py`:
```python
"""Tests for API status endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.main import app


@pytest.fixture
def mock_deps():
    """Mock API dependencies."""
    mock_cache = AsyncMock()
    mock_cache.get_mode = AsyncMock(return_value="paper")
    mock_cache.get_daily_pnl = AsyncMock(return_value=-50.0)
    mock_cache.get_open_exposure = AsyncMock(return_value=500.0)

    mock_db = AsyncMock()
    mock_db.get_all_wallets = AsyncMock(return_value=[])

    return {"cache": mock_cache, "db": mock_db}


@pytest.mark.asyncio
async def test_status_endpoint_returns_mode(mock_deps) -> None:
    """Status endpoint should return current mode."""
    with patch("polymind.interfaces.api.deps.get_cache", return_value=mock_deps["cache"]):
        with patch("polymind.interfaces.api.deps.get_db", return_value=mock_deps["db"]):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/status")

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "paper"
    assert "daily_pnl" in data
```

Create `tests/interfaces/api/test_wallets.py`:
```python
"""Tests for API wallets endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from polymind.interfaces.api.main import app


@pytest.fixture
def mock_wallet():
    """Create mock wallet."""
    wallet = MagicMock()
    wallet.id = 1
    wallet.address = "0x1234567890abcdef"
    wallet.alias = "whale.eth"
    wallet.enabled = True

    metrics = MagicMock()
    metrics.win_rate = 0.72
    metrics.total_pnl = 1500.0
    wallet.metrics = metrics

    return wallet


@pytest.fixture
def mock_db(mock_wallet):
    """Mock database."""
    db = AsyncMock()
    db.get_all_wallets = AsyncMock(return_value=[mock_wallet])
    db.add_wallet = AsyncMock(return_value=mock_wallet)
    db.remove_wallet = AsyncMock(return_value=True)
    return db


@pytest.mark.asyncio
async def test_wallets_list_returns_wallets(mock_db, mock_wallet) -> None:
    """Wallets list should return all tracked wallets."""
    with patch("polymind.interfaces.api.deps.get_db", return_value=mock_db):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/wallets")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["address"] == "0x1234567890abcdef"


@pytest.mark.asyncio
async def test_wallets_add_creates_wallet(mock_db) -> None:
    """Add wallet should create and return wallet."""
    with patch("polymind.interfaces.api.deps.get_db", return_value=mock_db):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/wallets",
                json={"address": "0x1234567890abcdef", "alias": "test"},
            )

    assert response.status_code == 201
    data = response.json()
    assert data["address"] == "0x1234567890abcdef"


@pytest.mark.asyncio
async def test_wallets_delete_removes_wallet(mock_db) -> None:
    """Delete wallet should remove wallet."""
    with patch("polymind.interfaces.api.deps.get_db", return_value=mock_db):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/wallets/0x1234567890abcdef")

    assert response.status_code == 204
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/interfaces/api/test_status.py tests/interfaces/api/test_wallets.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement API dependencies and routes**

Create `src/polymind/interfaces/api/deps.py`:
```python
"""FastAPI dependency injection."""

from polymind.config.settings import Settings, load_settings
from polymind.storage.cache import Cache, create_cache
from polymind.storage.database import Database, create_database

_db: Database | None = None
_cache: Cache | None = None
_settings: Settings | None = None


async def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


async def get_db() -> Database:
    """Get database connection."""
    global _db
    if _db is None:
        settings = await get_settings()
        _db = await create_database(settings.database.url)
    return _db


async def get_cache() -> Cache:
    """Get cache connection."""
    global _cache
    if _cache is None:
        settings = await get_settings()
        _cache = await create_cache(settings.redis.url)
    return _cache
```

Create `src/polymind/interfaces/api/routes/status.py`:
```python
"""Status endpoint."""

from fastapi import APIRouter, Depends

from polymind import __version__
from polymind.interfaces.api.deps import get_cache, get_db
from polymind.storage.cache import Cache
from polymind.storage.database import Database

router = APIRouter()


@router.get("/status")
async def status(
    cache: Cache = Depends(get_cache),
    db: Database = Depends(get_db),
) -> dict:
    """Get bot status.

    Returns:
        Current bot status including mode, P&L, and wallet count.
    """
    mode = await cache.get_mode()
    daily_pnl = await cache.get_daily_pnl()
    exposure = await cache.get_open_exposure()
    wallets = await db.get_all_wallets()

    return {
        "version": __version__,
        "mode": mode,
        "daily_pnl": daily_pnl,
        "open_exposure": exposure,
        "wallet_count": len(wallets),
    }
```

Create `src/polymind/interfaces/api/routes/wallets.py`:
```python
"""Wallets endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from polymind.interfaces.api.deps import get_db
from polymind.storage.database import Database

router = APIRouter(prefix="/wallets", tags=["wallets"])


class WalletCreate(BaseModel):
    """Request to create a wallet."""

    address: str
    alias: str | None = None


class WalletResponse(BaseModel):
    """Wallet response."""

    id: int
    address: str
    alias: str | None
    enabled: bool
    win_rate: float | None = None
    total_pnl: float | None = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[WalletResponse])
async def list_wallets(db: Database = Depends(get_db)) -> list[dict]:
    """List all tracked wallets."""
    wallets = await db.get_all_wallets()
    return [
        {
            "id": w.id,
            "address": w.address,
            "alias": w.alias,
            "enabled": w.enabled,
            "win_rate": w.metrics.win_rate if w.metrics else None,
            "total_pnl": w.metrics.total_pnl if w.metrics else None,
        }
        for w in wallets
    ]


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def add_wallet(
    wallet: WalletCreate,
    db: Database = Depends(get_db),
) -> dict:
    """Add a wallet to track."""
    created = await db.add_wallet(address=wallet.address, alias=wallet.alias)
    return {
        "id": created.id,
        "address": created.address,
        "alias": created.alias,
        "enabled": created.enabled,
        "win_rate": None,
        "total_pnl": None,
    }


@router.delete("/{address}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_wallet(
    address: str,
    db: Database = Depends(get_db),
) -> None:
    """Remove a wallet from tracking."""
    removed = await db.remove_wallet(address=address)
    if not removed:
        raise HTTPException(status_code=404, detail="Wallet not found")
```

Update `src/polymind/interfaces/api/main.py`:
```python
"""FastAPI application setup."""

from fastapi import FastAPI

from polymind import __version__
from polymind.interfaces.api.routes import health, status, wallets

app = FastAPI(
    title="PolyMind API",
    description="AI-powered prediction market trading bot API",
    version=__version__,
)

# Include routers
app.include_router(health.router)
app.include_router(status.router)
app.include_router(wallets.router)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/interfaces/api/ -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/polymind/interfaces/api/ tests/interfaces/api/
git commit -m "feat: add API status and wallets endpoints"
```

---

## Task 5: Discord Bot Setup

**Files:**
- Create: `src/polymind/interfaces/discord/__init__.py`
- Create: `src/polymind/interfaces/discord/bot.py`
- Create: `src/polymind/interfaces/discord/cogs/__init__.py`
- Create: `src/polymind/interfaces/discord/cogs/status.py`
- Create: `tests/interfaces/discord/__init__.py`
- Create: `tests/interfaces/discord/test_bot.py`

**Step 1: Write failing test for Discord bot**

Create `tests/interfaces/discord/__init__.py`:
```python
"""Discord bot tests."""
```

Create `tests/interfaces/discord/test_bot.py`:
```python
"""Tests for Discord bot."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.interfaces.discord.bot import PolymindBot


def test_bot_has_required_attributes() -> None:
    """Bot should have required attributes."""
    bot = PolymindBot(command_prefix="!")

    assert bot.command_prefix == "!"
    assert hasattr(bot, "cache")
    assert hasattr(bot, "db")


def test_bot_creates_with_intents() -> None:
    """Bot should be created with proper intents."""
    bot = PolymindBot(command_prefix="!")

    # Bot should have message content intent for commands
    assert bot.intents.message_content is True


@pytest.mark.asyncio
async def test_bot_setup_hook_loads_cogs() -> None:
    """Bot setup should load cogs."""
    bot = PolymindBot(command_prefix="!")

    with patch.object(bot, "load_extension", new_callable=AsyncMock) as mock_load:
        await bot.setup_hook()

        # Should load status cog
        mock_load.assert_called()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/interfaces/discord/test_bot.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement Discord bot**

Create `src/polymind/interfaces/discord/__init__.py`:
```python
"""Discord bot interface for PolyMind."""

from polymind.interfaces.discord.bot import PolymindBot

__all__ = ["PolymindBot"]
```

Create `src/polymind/interfaces/discord/bot.py`:
```python
"""Discord bot implementation."""

import discord
from discord.ext import commands

from polymind.config.settings import Settings, load_settings
from polymind.storage.cache import Cache, create_cache
from polymind.storage.database import Database, create_database


class PolymindBot(commands.Bot):
    """PolyMind Discord bot."""

    def __init__(self, command_prefix: str = "!", **kwargs) -> None:
        """Initialize the bot.

        Args:
            command_prefix: Command prefix for bot commands.
            **kwargs: Additional arguments for commands.Bot.
        """
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            **kwargs,
        )

        self.cache: Cache | None = None
        self.db: Database | None = None
        self.settings: Settings | None = None

    async def setup_hook(self) -> None:
        """Setup hook called when bot is ready."""
        # Load settings
        self.settings = load_settings()

        # Connect to database and cache
        self.db = await create_database(self.settings.database.url)
        self.cache = await create_cache(self.settings.redis.url)

        # Load cogs
        await self.load_extension("polymind.interfaces.discord.cogs.status")

    async def close(self) -> None:
        """Clean up connections on close."""
        if self.db:
            await self.db.close()
        if self.cache:
            await self.cache.close()
        await super().close()


async def create_bot() -> PolymindBot:
    """Create and configure the Discord bot.

    Returns:
        Configured PolymindBot instance.
    """
    return PolymindBot()
```

Create `src/polymind/interfaces/discord/cogs/__init__.py`:
```python
"""Discord bot cogs."""
```

Create `src/polymind/interfaces/discord/cogs/status.py`:
```python
"""Status cog for Discord bot."""

import discord
from discord import app_commands
from discord.ext import commands

from polymind import __version__


class StatusCog(commands.Cog):
    """Cog for status commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the cog."""
        self.bot = bot

    @app_commands.command(name="status", description="Show bot status")
    async def status(self, interaction: discord.Interaction) -> None:
        """Show current bot status."""
        cache = getattr(self.bot, "cache", None)
        db = getattr(self.bot, "db", None)

        mode = await cache.get_mode() if cache else "unknown"
        daily_pnl = await cache.get_daily_pnl() if cache else 0.0
        wallets = await db.get_all_wallets() if db else []

        embed = discord.Embed(
            title="PolyMind Status",
            color=discord.Color.green() if mode != "paused" else discord.Color.red(),
        )
        embed.add_field(name="Version", value=__version__, inline=True)
        embed.add_field(name="Mode", value=mode.upper(), inline=True)
        embed.add_field(name="Wallets", value=str(len(wallets)), inline=True)
        embed.add_field(name="Daily P&L", value=f"${daily_pnl:.2f}", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause", description="Pause all trading")
    async def pause(self, interaction: discord.Interaction) -> None:
        """Pause all trading."""
        cache = getattr(self.bot, "cache", None)
        if cache:
            await cache.set_mode("paused")

        await interaction.response.send_message(
            "🛑 **Trading Paused**\nAll trading has been stopped.",
            ephemeral=True,
        )

    @app_commands.command(name="resume", description="Resume trading in paper mode")
    async def resume(self, interaction: discord.Interaction) -> None:
        """Resume trading in paper mode."""
        cache = getattr(self.bot, "cache", None)
        if cache:
            await cache.set_mode("paper")

        await interaction.response.send_message(
            "✅ **Trading Resumed**\nTrading has resumed in paper mode.",
            ephemeral=True,
        )

    @app_commands.command(name="pnl", description="Show daily P&L")
    async def pnl(self, interaction: discord.Interaction) -> None:
        """Show daily P&L."""
        cache = getattr(self.bot, "cache", None)
        daily_pnl = await cache.get_daily_pnl() if cache else 0.0

        color = discord.Color.green() if daily_pnl >= 0 else discord.Color.red()
        sign = "+" if daily_pnl >= 0 else ""

        embed = discord.Embed(
            title="Daily P&L",
            description=f"**{sign}${daily_pnl:.2f}**",
            color=color,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Setup function for loading the cog."""
    await bot.add_cog(StatusCog(bot))
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/interfaces/discord/test_bot.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/polymind/interfaces/discord/ tests/interfaces/discord/
git commit -m "feat: add Discord bot with status commands"
```

---

## Task 6: Trade Alert Notifications

**Files:**
- Create: `src/polymind/interfaces/discord/alerts.py`
- Modify: `src/polymind/interfaces/discord/bot.py`
- Create: `tests/interfaces/discord/test_alerts.py`

**Step 1: Write failing test for trade alerts**

Create `tests/interfaces/discord/test_alerts.py`:
```python
"""Tests for Discord trade alerts."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.core.brain.decision import AIDecision, Urgency
from polymind.data.models import SignalSource, TradeSignal
from polymind.interfaces.discord.alerts import TradeAlertService, format_trade_alert


def test_format_trade_alert_creates_embed() -> None:
    """format_trade_alert should create Discord embed."""
    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="will-btc-hit-50k",
        token_id="token1",
        side="YES",
        size=500.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=250.0,
        confidence=0.78,
        reasoning="Strong wallet, good liquidity",
    )

    embed = format_trade_alert(
        signal=signal,
        decision=decision,
        wallet_alias="whale.eth",
        paper_mode=True,
    )

    assert embed.title == "🔔 Trade Alert"
    assert "whale.eth" in embed.description or "YES" in embed.description


def test_format_trade_alert_shows_paper_mode() -> None:
    """Alert should indicate paper mode."""
    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="will-btc-hit-50k",
        token_id="token1",
        side="YES",
        size=500.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=250.0,
        confidence=0.78,
        reasoning="Strong wallet",
    )

    embed = format_trade_alert(signal, decision, "whale", paper_mode=True)

    # Should mention paper mode somewhere
    embed_text = str(embed.to_dict())
    assert "paper" in embed_text.lower()


@pytest.mark.asyncio
async def test_trade_alert_service_sends_to_channel() -> None:
    """TradeAlertService should send embeds to channel."""
    mock_channel = AsyncMock()

    service = TradeAlertService(channel=mock_channel)

    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="will-btc-hit-50k",
        token_id="token1",
        side="YES",
        size=500.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=250.0,
        confidence=0.78,
        reasoning="Strong wallet",
    )

    await service.send_trade_alert(
        signal=signal,
        decision=decision,
        wallet_alias="whale.eth",
        paper_mode=True,
    )

    mock_channel.send.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/interfaces/discord/test_alerts.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement trade alerts**

Create `src/polymind/interfaces/discord/alerts.py`:
```python
"""Trade alert notifications for Discord."""

import discord

from polymind.core.brain.decision import AIDecision
from polymind.data.models import TradeSignal


def format_trade_alert(
    signal: TradeSignal,
    decision: AIDecision,
    wallet_alias: str | None = None,
    paper_mode: bool = True,
) -> discord.Embed:
    """Format a trade alert as Discord embed.

    Args:
        signal: The trade signal that was detected.
        decision: AI decision for this trade.
        wallet_alias: Friendly name for the wallet.
        paper_mode: Whether this is paper trading.

    Returns:
        Discord embed with trade details.
    """
    wallet_display = wallet_alias or f"{signal.wallet[:10]}..."
    mode_text = "📝 Paper" if paper_mode else "💰 Live"

    # Determine color based on decision
    if decision.execute:
        color = discord.Color.green()
    else:
        color = discord.Color.red()

    embed = discord.Embed(
        title="🔔 Trade Alert",
        color=color,
    )

    # Main info
    embed.add_field(
        name="Wallet",
        value=f"**{wallet_display}** copied",
        inline=False,
    )
    embed.add_field(
        name="Market",
        value=f'"{signal.market_id}"',
        inline=False,
    )
    embed.add_field(
        name="Side",
        value=f"**{signal.side}** @ ${signal.price:.2f}",
        inline=True,
    )
    embed.add_field(
        name="Size",
        value=f"${decision.size:.2f} ({mode_text})",
        inline=True,
    )

    # AI info
    embed.add_field(
        name="AI Confidence",
        value=f"{decision.confidence * 100:.0f}%",
        inline=True,
    )
    embed.add_field(
        name="Reasoning",
        value=f'"{decision.reasoning}"',
        inline=False,
    )

    # Footer
    embed.set_footer(text=f"Urgency: {decision.urgency.value.upper()}")

    return embed


class TradeAlertService:
    """Service for sending trade alerts to Discord."""

    def __init__(self, channel: discord.TextChannel) -> None:
        """Initialize the alert service.

        Args:
            channel: Discord channel to send alerts to.
        """
        self.channel = channel

    async def send_trade_alert(
        self,
        signal: TradeSignal,
        decision: AIDecision,
        wallet_alias: str | None = None,
        paper_mode: bool = True,
    ) -> None:
        """Send a trade alert to the channel.

        Args:
            signal: The trade signal that was detected.
            decision: AI decision for this trade.
            wallet_alias: Friendly name for the wallet.
            paper_mode: Whether this is paper trading.
        """
        embed = format_trade_alert(
            signal=signal,
            decision=decision,
            wallet_alias=wallet_alias,
            paper_mode=paper_mode,
        )
        await self.channel.send(embed=embed)

    async def send_error(self, message: str) -> None:
        """Send an error notification.

        Args:
            message: Error message to send.
        """
        embed = discord.Embed(
            title="⚠️ Error",
            description=message,
            color=discord.Color.orange(),
        )
        await self.channel.send(embed=embed)

    async def send_risk_alert(self, violation: str, details: str) -> None:
        """Send a risk violation alert.

        Args:
            violation: Type of risk violation.
            details: Details about the violation.
        """
        embed = discord.Embed(
            title="🛑 Risk Alert",
            color=discord.Color.red(),
        )
        embed.add_field(name="Violation", value=violation, inline=False)
        embed.add_field(name="Details", value=details, inline=False)

        await self.channel.send(embed=embed)
```

Update `src/polymind/interfaces/discord/__init__.py`:
```python
"""Discord bot interface for PolyMind."""

from polymind.interfaces.discord.alerts import TradeAlertService, format_trade_alert
from polymind.interfaces.discord.bot import PolymindBot

__all__ = [
    "PolymindBot",
    "TradeAlertService",
    "format_trade_alert",
]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/interfaces/discord/test_alerts.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/polymind/interfaces/discord/ tests/interfaces/discord/
git commit -m "feat: add Discord trade alert notifications"
```

---

## Task 7: Integration Tests

**Files:**
- Create: `tests/integration/test_interfaces.py`

**Step 1: Write integration tests**

Create `tests/integration/test_interfaces.py`:
```python
"""Integration tests for user interfaces."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from typer.testing import CliRunner

from polymind.core.brain.decision import AIDecision
from polymind.data.models import SignalSource, TradeSignal
from polymind.interfaces.api.main import app as api_app
from polymind.interfaces.cli.main import app as cli_app
from polymind.interfaces.discord.alerts import TradeAlertService, format_trade_alert


runner = CliRunner()


# CLI Integration Tests


def test_cli_version_command() -> None:
    """CLI version should show version."""
    result = runner.invoke(cli_app, ["--version"])
    assert result.exit_code == 0
    assert "PolyMind" in result.stdout


def test_cli_status_command_with_mock_context() -> None:
    """CLI status should show status from cache."""
    mock_context = MagicMock()
    mock_context.cache = AsyncMock()
    mock_context.cache.get_mode = AsyncMock(return_value="paper")
    mock_context.cache.get_daily_pnl = AsyncMock(return_value=-50.0)
    mock_context.db = AsyncMock()
    mock_context.db.get_all_wallets = AsyncMock(return_value=[])

    with patch("polymind.interfaces.cli.main.get_context", return_value=mock_context):
        result = runner.invoke(cli_app, ["status"])

    assert result.exit_code == 0
    assert "paper" in result.stdout or "Paper" in result.stdout


def test_cli_mode_command_sets_mode() -> None:
    """CLI mode should set mode in cache."""
    mock_context = MagicMock()
    mock_context.cache = AsyncMock()
    mock_context.cache.set_mode = AsyncMock()

    with patch("polymind.interfaces.cli.main.get_context", return_value=mock_context):
        result = runner.invoke(cli_app, ["mode", "paper"])

    assert result.exit_code == 0
    assert "paper" in result.stdout


# API Integration Tests


@pytest.mark.asyncio
async def test_api_health_returns_ok() -> None:
    """API health should return OK."""
    async with AsyncClient(
        transport=ASGITransport(app=api_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_api_wallets_crud_flow() -> None:
    """API wallets should support full CRUD."""
    mock_wallet = MagicMock()
    mock_wallet.id = 1
    mock_wallet.address = "0xtest"
    mock_wallet.alias = "test"
    mock_wallet.enabled = True
    mock_wallet.metrics = None

    mock_db = AsyncMock()
    mock_db.get_all_wallets = AsyncMock(return_value=[mock_wallet])
    mock_db.add_wallet = AsyncMock(return_value=mock_wallet)
    mock_db.remove_wallet = AsyncMock(return_value=True)

    with patch("polymind.interfaces.api.deps.get_db", return_value=mock_db):
        async with AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
        ) as client:
            # Create
            response = await client.post(
                "/wallets",
                json={"address": "0xtest", "alias": "test"},
            )
            assert response.status_code == 201

            # List
            response = await client.get("/wallets")
            assert response.status_code == 200
            assert len(response.json()) == 1

            # Delete
            response = await client.delete("/wallets/0xtest")
            assert response.status_code == 204


# Discord Integration Tests


def test_discord_trade_alert_format() -> None:
    """Discord trade alert should format correctly."""
    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="will-btc-hit-50k",
        token_id="token1",
        side="YES",
        size=500.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=250.0,
        confidence=0.78,
        reasoning="Strong wallet, good liquidity",
    )

    embed = format_trade_alert(
        signal=signal,
        decision=decision,
        wallet_alias="whale.eth",
        paper_mode=True,
    )

    # Verify embed has required fields
    assert embed.title == "🔔 Trade Alert"
    assert len(embed.fields) >= 5


@pytest.mark.asyncio
async def test_discord_alert_service_sends_embed() -> None:
    """Discord alert service should send embeds."""
    mock_channel = AsyncMock()

    service = TradeAlertService(channel=mock_channel)

    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="test-market",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.50,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.80,
        reasoning="Test trade",
    )

    await service.send_trade_alert(signal, decision, "test", True)

    mock_channel.send.assert_called_once()
    # Verify an embed was sent
    call_kwargs = mock_channel.send.call_args.kwargs
    assert "embed" in call_kwargs
```

**Step 2: Run all tests**

Run: `pytest -v`
Expected: All tests pass

**Step 3: Run linting**

Run: `ruff check src tests`
Expected: All checks passed

**Step 4: Commit**

```bash
git add tests/integration/test_interfaces.py
git commit -m "test: add interfaces integration tests"
```

---

## Summary

Phase 4 User Interfaces is complete when:

- [x] CLI connects to database and cache for real data
- [x] CLI wallet commands create/update/delete wallets
- [x] FastAPI provides health, status, and wallets endpoints
- [x] Discord bot has status, pause, resume, pnl commands
- [x] Discord trade alerts format and send properly
- [x] All tests pass

**Next Phase:** Polish (Testing suite, Error handling, Logging, Documentation)
