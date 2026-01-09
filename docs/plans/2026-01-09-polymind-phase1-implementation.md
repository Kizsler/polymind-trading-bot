# PolyMind Phase 1: Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up the foundational project structure with Python async architecture, PostgreSQL + Redis via Docker, configuration system, and CLI skeleton.

**Architecture:** Async-first Python application using asyncio. Database connections pooled via asyncpg. Configuration loaded from YAML with environment variable overrides. CLI built with Typer for rich terminal output.

**Tech Stack:** Python 3.11+, asyncio, asyncpg, redis-py, SQLAlchemy 2.0, Alembic, Typer, Rich, Docker Compose, pytest

---

## Task 1: Project Setup & Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `src/polymind/__init__.py`
- Create: `src/polymind/py.typed`
- Create: `tests/__init__.py`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Create pyproject.toml with dependencies**

```toml
[project]
name = "polymind"
version = "0.1.0"
description = "AI-powered prediction market trading bot"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27.0",
    "websockets>=12.0",
    "web3>=6.15.0",
    "anthropic>=0.40.0",
    "asyncpg>=0.29.0",
    "redis>=5.0.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.13.0",
    "typer>=0.12.0",
    "rich>=13.7.0",
    "pyyaml>=6.0.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.3.0",
    "black>=24.2.0",
    "mypy>=1.8.0",
]

[project.scripts]
polymind = "polymind.interfaces.cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/polymind"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
target-version = "py311"
line-length = 88
select = ["E", "F", "I", "N", "W", "UP"]

[tool.black]
target-version = ["py311"]
line-length = 88

[tool.mypy]
python_version = "3.11"
strict = true
```

**Step 2: Create .python-version**

```
3.11
```

**Step 3: Create src/polymind/__init__.py**

```python
"""PolyMind - AI-powered prediction market trading bot."""

__version__ = "0.1.0"
```

**Step 4: Create src/polymind/py.typed**

Empty file (marker for PEP 561 typed package).

**Step 5: Create tests/__init__.py**

```python
"""PolyMind test suite."""
```

**Step 6: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.coverage
.pytest_cache/
htmlcov/
.mypy_cache/

# Environment
.env
.env.local
*.local.yaml

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
```

**Step 7: Create README.md**

```markdown
# PolyMind

AI-powered prediction market trading bot for Polymarket.

## Features

- Wallet copy trading
- AI decision brain (Claude API)
- Risk management
- CLI, Web Dashboard, and Discord bot interfaces

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Start infrastructure
docker-compose up -d

# Run the bot
polymind start
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check src tests
black src tests --check

# Type check
mypy src
```
```

**Step 8: Install dependencies and verify**

Run: `pip install -e ".[dev]"`
Expected: Successfully installed polymind and all dependencies

**Step 9: Commit**

```bash
git add pyproject.toml .python-version src/ tests/ .gitignore README.md
git commit -m "chore: initialize project structure with dependencies"
```

---

## Task 2: Configuration System

**Files:**
- Create: `src/polymind/config/__init__.py`
- Create: `src/polymind/config/settings.py`
- Create: `config/default.yaml`
- Create: `config/example.env`
- Create: `tests/config/__init__.py`
- Create: `tests/config/test_settings.py`

**Step 1: Write the failing test for config loading**

Create `tests/config/__init__.py`:
```python
"""Config tests."""
```

Create `tests/config/test_settings.py`:
```python
"""Tests for configuration settings."""

import pytest
from polymind.config.settings import Settings, RiskConfig, DatabaseConfig


def test_settings_loads_defaults():
    """Settings should load with sensible defaults."""
    settings = Settings()

    assert settings.app_name == "polymind"
    assert settings.mode == "paper"
    assert settings.risk.max_daily_loss == 500.0


def test_risk_config_validates_positive_values():
    """Risk config should require positive values."""
    with pytest.raises(ValueError):
        RiskConfig(max_daily_loss=-100)


def test_database_config_builds_url():
    """Database config should build connection URL."""
    db = DatabaseConfig(
        host="localhost",
        port=5432,
        name="polymind",
        user="postgres",
        password="secret"
    )

    assert "postgresql+asyncpg://postgres:secret@localhost:5432/polymind" in db.url
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_settings.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'polymind.config'"

**Step 3: Create config module**

Create `src/polymind/config/__init__.py`:
```python
"""Configuration module."""

from polymind.config.settings import Settings, RiskConfig, DatabaseConfig

__all__ = ["Settings", "RiskConfig", "DatabaseConfig"]
```

Create `src/polymind/config/settings.py`:
```python
"""Application settings with Pydantic validation."""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RiskConfig(BaseSettings):
    """Risk management configuration."""

    model_config = SettingsConfigDict(env_prefix="POLYMIND_RISK_")

    max_daily_loss: float = Field(default=500.0, description="Maximum daily loss in USD")
    max_exposure_per_market: float = Field(default=200.0, description="Max exposure per market")
    max_exposure_per_wallet: float = Field(default=500.0, description="Max exposure per wallet")
    max_total_exposure: float = Field(default=2000.0, description="Max total exposure")
    max_single_trade: float = Field(default=100.0, description="Max single trade size")
    max_slippage: float = Field(default=0.03, description="Max slippage (3%)")

    @field_validator("max_daily_loss", "max_exposure_per_market", "max_exposure_per_wallet",
                     "max_total_exposure", "max_single_trade", mode="before")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Value must be positive")
        return v


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="POLYMIND_DB_")

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="polymind")
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")

    @computed_field
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="POLYMIND_REDIS_")

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)

    @computed_field
    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class ClaudeConfig(BaseSettings):
    """Claude API configuration."""

    model_config = SettingsConfigDict(env_prefix="POLYMIND_CLAUDE_")

    api_key: str = Field(default="")
    model: str = Field(default="claude-sonnet-4-20250514")
    max_tokens: int = Field(default=1024)


class DiscordConfig(BaseSettings):
    """Discord bot configuration."""

    model_config = SettingsConfigDict(env_prefix="POLYMIND_DISCORD_")

    bot_token: str = Field(default="")
    channel_id: str = Field(default="")
    enabled: bool = Field(default=False)


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="POLYMIND_",
        env_nested_delimiter="__",
    )

    app_name: str = Field(default="polymind")
    mode: Literal["paper", "live", "paused"] = Field(default="paper")
    log_level: str = Field(default="INFO")

    risk: RiskConfig = Field(default_factory=RiskConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)


def load_settings() -> Settings:
    """Load settings from environment."""
    return Settings()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_settings.py -v`
Expected: 3 passed

**Step 5: Create config files**

Create `config/default.yaml`:
```yaml
# PolyMind Default Configuration
# Copy to config/local.yaml and customize

app_name: polymind
mode: paper  # paper | live | paused
log_level: INFO

risk:
  max_daily_loss: 500.0
  max_exposure_per_market: 200.0
  max_exposure_per_wallet: 500.0
  max_total_exposure: 2000.0
  max_single_trade: 100.0
  max_slippage: 0.03

database:
  host: localhost
  port: 5432
  name: polymind
  user: postgres
  password: postgres

redis:
  host: localhost
  port: 6379
  db: 0

claude:
  api_key: ""  # Set via POLYMIND_CLAUDE_API_KEY
  model: claude-sonnet-4-20250514
  max_tokens: 1024

discord:
  bot_token: ""  # Set via POLYMIND_DISCORD_BOT_TOKEN
  channel_id: ""
  enabled: false
```

Create `config/example.env`:
```env
# PolyMind Environment Variables
# Copy to .env and fill in your values

# Trading mode
POLYMIND_MODE=paper

# Claude API
POLYMIND_CLAUDE_API_KEY=your-api-key-here

# Database
POLYMIND_DB_HOST=localhost
POLYMIND_DB_PORT=5432
POLYMIND_DB_NAME=polymind
POLYMIND_DB_USER=postgres
POLYMIND_DB_PASSWORD=postgres

# Redis
POLYMIND_REDIS_HOST=localhost
POLYMIND_REDIS_PORT=6379

# Discord (optional)
POLYMIND_DISCORD_ENABLED=false
POLYMIND_DISCORD_BOT_TOKEN=
POLYMIND_DISCORD_CHANNEL_ID=
```

**Step 6: Commit**

```bash
git add src/polymind/config/ tests/config/ config/
git commit -m "feat: add configuration system with Pydantic settings"
```

---

## Task 3: Docker Compose for PostgreSQL & Redis

**Files:**
- Create: `docker-compose.yaml`
- Create: `scripts/wait-for-db.sh`

**Step 1: Create docker-compose.yaml**

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: polymind-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: polymind
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: polymind-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

**Step 2: Create wait-for-db script**

Create `scripts/wait-for-db.sh`:
```bash
#!/bin/bash
# Wait for PostgreSQL and Redis to be ready

set -e

echo "Waiting for PostgreSQL..."
until docker exec polymind-postgres pg_isready -U postgres > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready!"

echo "Waiting for Redis..."
until docker exec polymind-redis redis-cli ping > /dev/null 2>&1; do
    sleep 1
done
echo "Redis is ready!"

echo "All services are ready!"
```

**Step 3: Start services and verify**

Run: `docker-compose up -d`
Expected: Both containers start successfully

Run: `docker-compose ps`
Expected: Both services show as "running" with healthy status

**Step 4: Commit**

```bash
git add docker-compose.yaml scripts/
git commit -m "infra: add Docker Compose for PostgreSQL and Redis"
```

---

## Task 4: Database Models & Migrations

**Files:**
- Create: `src/polymind/storage/__init__.py`
- Create: `src/polymind/storage/models.py`
- Create: `src/polymind/storage/database.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `migrations/versions/.gitkeep`
- Create: `tests/storage/__init__.py`
- Create: `tests/storage/test_models.py`

**Step 1: Write failing test for models**

Create `tests/storage/__init__.py`:
```python
"""Storage tests."""
```

Create `tests/storage/test_models.py`:
```python
"""Tests for database models."""

import pytest
from datetime import datetime, timezone
from polymind.storage.models import Wallet, Trade, WalletMetrics


def test_wallet_model_has_required_fields():
    """Wallet model should have address and alias."""
    wallet = Wallet(
        address="0x1234567890abcdef",
        alias="whale.eth",
        enabled=True
    )

    assert wallet.address == "0x1234567890abcdef"
    assert wallet.alias == "whale.eth"
    assert wallet.enabled is True


def test_trade_model_has_required_fields():
    """Trade model should capture all trade details."""
    trade = Trade(
        wallet_id=1,
        market_id="btc-50k-friday",
        side="YES",
        size=250.0,
        price=0.65,
        source="clob"
    )

    assert trade.market_id == "btc-50k-friday"
    assert trade.side == "YES"
    assert trade.size == 250.0


def test_wallet_metrics_defaults():
    """WalletMetrics should have sensible defaults."""
    metrics = WalletMetrics(wallet_id=1)

    assert metrics.win_rate == 0.0
    assert metrics.total_trades == 0
    assert metrics.total_pnl == 0.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create storage module**

Create `src/polymind/storage/__init__.py`:
```python
"""Storage module for database operations."""

from polymind.storage.models import Base, Wallet, Trade, WalletMetrics, MarketSnapshot, RiskEvent
from polymind.storage.database import Database

__all__ = [
    "Base",
    "Wallet",
    "Trade",
    "WalletMetrics",
    "MarketSnapshot",
    "RiskEvent",
    "Database",
]
```

Create `src/polymind/storage/models.py`:
```python
"""SQLAlchemy database models."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Float, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Wallet(Base):
    """Tracked wallet for copy trading."""

    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(42), unique=True, index=True)
    alias: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    metrics: Mapped[Optional["WalletMetrics"]] = relationship(back_populates="wallet")
    trades: Mapped[list["Trade"]] = relationship(back_populates="wallet")


class WalletMetrics(Base):
    """Performance metrics for a wallet."""

    __tablename__ = "wallet_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), unique=True)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_roi: Mapped[float] = mapped_column(Float, default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    last_trade_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    wallet: Mapped["Wallet"] = relationship(back_populates="metrics")


class Trade(Base):
    """Detected trade and our response."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), index=True)
    market_id: Mapped[str] = mapped_column(String(200), index=True)
    side: Mapped[str] = mapped_column(String(10))  # YES or NO
    size: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    source: Mapped[str] = mapped_column(String(20))  # clob or chain

    # AI decision
    ai_decision: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    executed_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    executed_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paper_mode: Mapped[bool] = mapped_column(Boolean, default=True)

    # Outcome
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    wallet: Mapped["Wallet"] = relationship(back_populates="trades")
    market_snapshot: Mapped[Optional["MarketSnapshot"]] = relationship(back_populates="trade")


class MarketSnapshot(Base):
    """Market state at decision time."""

    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"), unique=True)
    market_id: Mapped[str] = mapped_column(String(200))
    liquidity: Mapped[float] = mapped_column(Float)
    spread: Mapped[float] = mapped_column(Float)
    time_to_resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    trade: Mapped["Trade"] = relationship(back_populates="market_snapshot")


class RiskEvent(Base):
    """Risk management events."""

    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50))
    details: Mapped[str] = mapped_column(Text)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
```

Create `src/polymind/storage/database.py`:
```python
"""Database connection and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from polymind.config.settings import Settings
from polymind.storage.models import Base


class Database:
    """Async database connection manager."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_async_engine(
            settings.database.url,
            echo=settings.log_level == "DEBUG",
            pool_size=5,
            max_overflow=10,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Close the database connection."""
        await self.engine.dispose()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/storage/test_models.py -v`
Expected: 3 passed

**Step 5: Initialize Alembic**

Run: `alembic init migrations`

**Step 6: Update alembic.ini**

Edit the sqlalchemy.url line in `alembic.ini`:
```ini
# Change this line:
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/polymind
```

**Step 7: Update migrations/env.py**

Replace `migrations/env.py`:
```python
"""Alembic migration environment."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from polymind.storage.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 8: Create initial migration**

Run: `alembic revision --autogenerate -m "initial schema"`
Expected: Creates migration file in migrations/versions/

**Step 9: Apply migration**

Run: `alembic upgrade head`
Expected: Tables created in PostgreSQL

**Step 10: Commit**

```bash
git add src/polymind/storage/ tests/storage/ alembic.ini migrations/
git commit -m "feat: add database models and migrations"
```

---

## Task 5: Redis Cache Layer

**Files:**
- Create: `src/polymind/storage/cache.py`
- Create: `tests/storage/test_cache.py`

**Step 1: Write failing test for cache**

Create `tests/storage/test_cache.py`:
```python
"""Tests for Redis cache layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.storage.cache import Cache


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.mark.asyncio
async def test_cache_get_returns_none_when_missing(mock_redis):
    """Cache get should return None for missing keys."""
    cache = Cache(mock_redis)
    result = await cache.get("missing_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_stores_value(mock_redis):
    """Cache set should store JSON-serialized value."""
    cache = Cache(mock_redis)
    await cache.set("key", {"value": 123})
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_cache_get_daily_pnl_returns_float(mock_redis):
    """Daily PnL should return float."""
    mock_redis.get = AsyncMock(return_value=b"-150.50")
    cache = Cache(mock_redis)
    result = await cache.get_daily_pnl()
    assert result == -150.50


@pytest.mark.asyncio
async def test_cache_update_daily_pnl(mock_redis):
    """Should update daily PnL atomically."""
    mock_redis.incrbyfloat = AsyncMock(return_value=-50.0)
    cache = Cache(mock_redis)
    result = await cache.update_daily_pnl(-50.0)
    assert result == -50.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_cache.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement cache**

Create `src/polymind/storage/cache.py`:
```python
"""Redis cache layer for real-time state."""

import json
from typing import Any, Optional

from redis.asyncio import Redis


class Cache:
    """Redis cache for real-time trading state."""

    # Key prefixes
    PREFIX_WALLET = "wallet"
    PREFIX_MARKET = "market"
    PREFIX_RISK = "risk"
    PREFIX_SYSTEM = "system"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    # Generic operations

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value.decode() if isinstance(value, bytes) else value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set a value in cache."""
        serialized = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        if ttl:
            return await self.redis.setex(key, ttl, serialized)
        return await self.redis.set(key, serialized)

    async def delete(self, key: str) -> int:
        """Delete a key from cache."""
        return await self.redis.delete(key)

    # Risk state

    async def get_daily_pnl(self) -> float:
        """Get current daily P&L."""
        value = await self.redis.get(f"{self.PREFIX_RISK}:daily_pnl")
        return float(value) if value else 0.0

    async def update_daily_pnl(self, delta: float) -> float:
        """Update daily P&L atomically."""
        return await self.redis.incrbyfloat(f"{self.PREFIX_RISK}:daily_pnl", delta)

    async def reset_daily_pnl(self) -> None:
        """Reset daily P&L to zero."""
        await self.redis.set(f"{self.PREFIX_RISK}:daily_pnl", "0.0")

    async def get_open_exposure(self) -> float:
        """Get current open exposure."""
        value = await self.redis.get(f"{self.PREFIX_RISK}:open_exposure")
        return float(value) if value else 0.0

    async def update_open_exposure(self, delta: float) -> float:
        """Update open exposure atomically."""
        return await self.redis.incrbyfloat(f"{self.PREFIX_RISK}:open_exposure", delta)

    # System state

    async def get_mode(self) -> str:
        """Get current trading mode."""
        value = await self.redis.get(f"{self.PREFIX_SYSTEM}:mode")
        return value.decode() if value else "paper"

    async def set_mode(self, mode: str) -> None:
        """Set trading mode."""
        await self.redis.set(f"{self.PREFIX_SYSTEM}:mode", mode)

    # Wallet state

    async def set_wallet_last_trade(self, address: str, trade_id: int) -> None:
        """Record last trade for a wallet."""
        await self.redis.set(
            f"{self.PREFIX_WALLET}:{address}:last_trade",
            str(trade_id)
        )

    async def get_wallet_last_trade(self, address: str) -> Optional[int]:
        """Get last trade ID for a wallet."""
        value = await self.redis.get(f"{self.PREFIX_WALLET}:{address}:last_trade")
        return int(value) if value else None

    # Market state

    async def set_market_price(self, market_id: str, price: float) -> None:
        """Cache current market price."""
        await self.redis.setex(
            f"{self.PREFIX_MARKET}:{market_id}:price",
            60,  # 1 minute TTL
            str(price)
        )

    async def get_market_price(self, market_id: str) -> Optional[float]:
        """Get cached market price."""
        value = await self.redis.get(f"{self.PREFIX_MARKET}:{market_id}:price")
        return float(value) if value else None


async def create_cache(redis_url: str) -> Cache:
    """Create a cache instance."""
    redis = Redis.from_url(redis_url)
    return Cache(redis)
```

Update `src/polymind/storage/__init__.py`:
```python
"""Storage module for database operations."""

from polymind.storage.models import Base, Wallet, Trade, WalletMetrics, MarketSnapshot, RiskEvent
from polymind.storage.database import Database
from polymind.storage.cache import Cache, create_cache

__all__ = [
    "Base",
    "Wallet",
    "Trade",
    "WalletMetrics",
    "MarketSnapshot",
    "RiskEvent",
    "Database",
    "Cache",
    "create_cache",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/storage/test_cache.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/polymind/storage/ tests/storage/
git commit -m "feat: add Redis cache layer for real-time state"
```

---

## Task 6: CLI Skeleton

**Files:**
- Create: `src/polymind/interfaces/__init__.py`
- Create: `src/polymind/interfaces/cli/__init__.py`
- Create: `src/polymind/interfaces/cli/main.py`
- Create: `tests/interfaces/__init__.py`
- Create: `tests/interfaces/cli/__init__.py`
- Create: `tests/interfaces/cli/test_main.py`

**Step 1: Write failing test for CLI**

Create `tests/interfaces/__init__.py`:
```python
"""Interface tests."""
```

Create `tests/interfaces/cli/__init__.py`:
```python
"""CLI tests."""
```

Create `tests/interfaces/cli/test_main.py`:
```python
"""Tests for CLI commands."""

import pytest
from typer.testing import CliRunner

from polymind.interfaces.cli.main import app


runner = CliRunner()


def test_cli_version():
    """CLI should show version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_cli_status_command():
    """CLI should have status command."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "PolyMind" in result.stdout


def test_cli_wallets_list():
    """CLI should have wallets list command."""
    result = runner.invoke(app, ["wallets", "list"])
    assert result.exit_code == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/interfaces/cli/test_main.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement CLI**

Create `src/polymind/interfaces/__init__.py`:
```python
"""User interfaces module."""
```

Create `src/polymind/interfaces/cli/__init__.py`:
```python
"""CLI interface."""

from polymind.interfaces.cli.main import app

__all__ = ["app"]
```

Create `src/polymind/interfaces/cli/main.py`:
```python
"""PolyMind CLI application."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from polymind import __version__

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
    version: Optional[bool] = typer.Option(
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
    console.print(Panel.fit(
        "[bold green]Starting PolyMind...[/bold green]\n"
        "Mode: [yellow]paper[/yellow]\n"
        "Press Ctrl+C to stop",
        title="PolyMind",
    ))
    # TODO: Actually start the bot
    console.print("[dim]Bot start not yet implemented[/dim]")


@app.command()
def stop() -> None:
    """Stop the trading bot gracefully."""
    console.print("[yellow]Stopping PolyMind...[/yellow]")
    # TODO: Actually stop the bot
    console.print("[green]Bot stopped[/green]")


@app.command()
def status() -> None:
    """Show current bot status."""
    table = Table(title="PolyMind Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Version", __version__)
    table.add_row("Mode", "paper")
    table.add_row("Status", "stopped")
    table.add_row("Tracked Wallets", "0")
    table.add_row("Open Positions", "0")
    table.add_row("Daily P&L", "$0.00")

    console.print(table)


@app.command()
def pause() -> None:
    """Pause trading (emergency stop)."""
    console.print("[bold red]PAUSING ALL TRADING[/bold red]")
    # TODO: Set mode to paused
    console.print("[yellow]Trading paused. Use 'polymind start' to resume.[/yellow]")


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
        confirm = typer.confirm(
            "Are you sure you want to enable LIVE trading with real money?",
            abort=True,
        )

    console.print(f"[green]Mode set to: {new_mode}[/green]")


@app.command()
def trades(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of trades to show"),
) -> None:
    """Show recent trades."""
    table = Table(title=f"Recent Trades (last {limit})")
    table.add_column("Time", style="dim")
    table.add_column("Wallet")
    table.add_column("Market")
    table.add_column("Side")
    table.add_column("Size")
    table.add_column("AI Decision")
    table.add_column("P&L")

    # TODO: Fetch actual trades
    console.print(table)
    console.print("[dim]No trades yet[/dim]")


# Wallets subcommands

@wallets_app.command("list")
def wallets_list() -> None:
    """List all tracked wallets."""
    table = Table(title="Tracked Wallets")
    table.add_column("Address", style="cyan")
    table.add_column("Alias")
    table.add_column("Enabled")
    table.add_column("Win Rate")
    table.add_column("Total P&L")

    # TODO: Fetch actual wallets
    console.print(table)
    console.print("[dim]No wallets tracked. Use 'polymind wallets add <address>' to add one.[/dim]")


@wallets_app.command("add")
def wallets_add(
    address: str = typer.Argument(..., help="Wallet address to track"),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="Friendly name"),
) -> None:
    """Add a wallet to track."""
    # TODO: Validate address format
    # TODO: Add to database
    display = alias or address[:10] + "..."
    console.print(f"[green]Added wallet: {display}[/green]")


@wallets_app.command("remove")
def wallets_remove(
    address: str = typer.Argument(..., help="Wallet address to remove"),
) -> None:
    """Remove a wallet from tracking."""
    # TODO: Remove from database
    console.print(f"[yellow]Removed wallet: {address[:10]}...[/yellow]")


@wallets_app.command("enable")
def wallets_enable(
    address: str = typer.Argument(..., help="Wallet address to enable"),
) -> None:
    """Enable trading for a wallet."""
    console.print(f"[green]Enabled wallet: {address[:10]}...[/green]")


@wallets_app.command("disable")
def wallets_disable(
    address: str = typer.Argument(..., help="Wallet address to disable"),
) -> None:
    """Disable trading for a wallet."""
    console.print(f"[yellow]Disabled wallet: {address[:10]}...[/yellow]")


if __name__ == "__main__":
    app()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/interfaces/cli/test_main.py -v`
Expected: 3 passed

**Step 5: Test CLI manually**

Run: `polymind --version`
Expected: "PolyMind v0.1.0"

Run: `polymind status`
Expected: Status table displayed

Run: `polymind --help`
Expected: Help text with all commands

**Step 6: Commit**

```bash
git add src/polymind/interfaces/ tests/interfaces/
git commit -m "feat: add CLI skeleton with Typer and Rich"
```

---

## Task 7: Integration Test & Final Verification

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_foundation.py`

**Step 1: Write integration test**

Create `tests/integration/__init__.py`:
```python
"""Integration tests."""
```

Create `tests/integration/test_foundation.py`:
```python
"""Integration tests for Phase 1 foundation."""

import pytest
from polymind import __version__
from polymind.config.settings import Settings
from polymind.storage.models import Wallet, Trade
from polymind.interfaces.cli.main import app


def test_version_is_set():
    """Package version should be set."""
    assert __version__ == "0.1.0"


def test_settings_can_be_loaded():
    """Settings should load without errors."""
    settings = Settings()
    assert settings.app_name == "polymind"
    assert settings.mode == "paper"


def test_models_can_be_instantiated():
    """Database models should be instantiable."""
    wallet = Wallet(address="0x" + "a" * 40, alias="test")
    assert wallet.address.startswith("0x")

    trade = Trade(
        wallet_id=1,
        market_id="test-market",
        side="YES",
        size=100.0,
        price=0.5,
        source="clob",
    )
    assert trade.side == "YES"


def test_cli_app_exists():
    """CLI app should be importable."""
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "polymind" in result.stdout.lower()
```

**Step 2: Run all tests**

Run: `pytest -v`
Expected: All tests pass

**Step 3: Run linting**

Run: `ruff check src tests`
Expected: No errors

Run: `black src tests --check`
Expected: All files formatted correctly

**Step 4: Final commit**

```bash
git add tests/integration/
git commit -m "test: add integration tests for Phase 1 foundation"
```

---

## Summary

Phase 1 is complete when all these are working:

- [x] `polymind --version` shows version
- [x] `polymind status` shows status table
- [x] `polymind wallets list` works
- [x] `docker-compose up -d` starts PostgreSQL and Redis
- [x] `alembic upgrade head` creates database tables
- [x] `pytest` passes all tests
- [x] Settings load from environment variables

**Next Phase:** Data Layer (Polymarket CLOB API + Polygon monitoring)
