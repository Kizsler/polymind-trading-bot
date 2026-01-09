"""Database connection and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload

from polymind.config.settings import Settings
from polymind.storage.models import Base, Trade, Wallet


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

    async def get_all_wallets(self) -> list[Wallet]:
        """Get all tracked wallets with their metrics."""
        async with self.session() as session:
            result = await session.execute(
                select(Wallet).options(selectinload(Wallet.metrics))
            )
            return list(result.scalars().all())

    async def add_wallet(self, address: str, alias: str | None = None) -> Wallet:
        """Add a new wallet to track."""
        async with self.session() as session:
            wallet = Wallet(address=address, alias=alias)
            session.add(wallet)
            await session.flush()
            await session.refresh(wallet)
            return wallet

    async def remove_wallet(self, address: str) -> bool:
        """Remove a wallet by address."""
        async with self.session() as session:
            result = await session.execute(
                select(Wallet).where(Wallet.address == address)
            )
            wallet = result.scalar_one_or_none()
            if wallet:
                await session.delete(wallet)
                return True
            return False

    async def update_wallet(self, address: str, **kwargs) -> bool:
        """Update wallet fields."""
        async with self.session() as session:
            result = await session.execute(
                select(Wallet).where(Wallet.address == address)
            )
            wallet = result.scalar_one_or_none()
            if wallet:
                for key, value in kwargs.items():
                    setattr(wallet, key, value)
                return True
            return False

    async def get_recent_trades(self, limit: int = 10) -> list[Trade]:
        """Get recent trades with wallet info."""
        async with self.session() as session:
            result = await session.execute(
                select(Trade)
                .options(selectinload(Trade.wallet))
                .order_by(Trade.detected_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
