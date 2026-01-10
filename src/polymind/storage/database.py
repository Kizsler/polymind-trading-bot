"""Database connection and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload

from polymind.config.settings import Settings
from polymind.storage.models import (
    Base,
    MarketFilter,
    MarketMapping,
    Order,
    Trade,
    Wallet,
)


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

    async def get_wallet_by_address(self, address: str) -> Wallet | None:
        """Get a wallet by address.

        Args:
            address: The wallet address.

        Returns:
            Wallet object or None if not found.
        """
        async with self.session() as session:
            result = await session.execute(
                select(Wallet)
                .options(selectinload(Wallet.metrics))
                .where(Wallet.address == address)
            )
            return result.scalar_one_or_none()

    async def update_wallet_controls(
        self, address: str, controls: dict[str, Any]
    ) -> bool:
        """Update wallet control settings.

        Args:
            address: The wallet address.
            controls: Dictionary of control settings to update.
                Valid keys: enabled, scale_factor, max_trade_size, min_confidence.

        Returns:
            True if wallet was found and updated, False otherwise.
        """
        valid_keys = {"enabled", "scale_factor", "max_trade_size", "min_confidence"}
        filtered = {k: v for k, v in controls.items() if k in valid_keys}

        if not filtered:
            return True  # Nothing to update

        async with self.session() as session:
            result = await session.execute(
                select(Wallet).where(Wallet.address == address)
            )
            wallet = result.scalar_one_or_none()
            if wallet:
                for key, value in filtered.items():
                    setattr(wallet, key, value)
                return True
            return False

    async def get_recent_trades(
        self, limit: int = 10, executed_only: bool = False
    ) -> list[Trade]:
        """Get recent trades with wallet info.

        Args:
            limit: Maximum number of trades to return
            executed_only: If True, only return executed trades

        Returns:
            List of Trade objects ordered by most recent first
        """
        async with self.session() as session:
            query = select(Trade).options(selectinload(Trade.wallet))

            if executed_only:
                query = query.where(Trade.executed == True)  # noqa: E712

            query = query.order_by(Trade.detected_at.desc()).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_wallet_metrics(self, wallet_address: str) -> dict[str, Any] | None:
        """Get performance metrics for a wallet.

        Args:
            wallet_address: The wallet address to get metrics for.

        Returns:
            Dictionary with win_rate, avg_roi, total_trades, recent_performance
            or None if wallet not found.
        """
        async with self.session() as session:
            result = await session.execute(
                select(Wallet)
                .options(selectinload(Wallet.metrics))
                .where(Wallet.address == wallet_address.lower())
            )
            wallet = result.scalar_one_or_none()

            if not wallet or not wallet.metrics:
                return None

            metrics = wallet.metrics
            return {
                "win_rate": metrics.win_rate,
                "avg_roi": metrics.avg_roi,
                "total_trades": metrics.total_trades,
                "recent_performance": metrics.total_pnl / max(metrics.total_trades, 1) if metrics.total_trades > 0 else 0.0,
            }

    # Market Mapping methods

    async def get_all_market_mappings(self) -> list[MarketMapping]:
        """Get all market mappings for cross-platform arbitrage."""
        async with self.session() as session:
            result = await session.execute(
                select(MarketMapping).order_by(MarketMapping.created_at.desc())
            )
            return list(result.scalars().all())

    async def add_market_mapping(
        self,
        polymarket_id: str | None = None,
        kalshi_id: str | None = None,
        description: str | None = None,
        active: bool = True,
    ) -> MarketMapping:
        """Add a new market mapping."""
        async with self.session() as session:
            mapping = MarketMapping(
                polymarket_id=polymarket_id,
                kalshi_id=kalshi_id,
                description=description,
                active=active,
            )
            session.add(mapping)
            await session.flush()
            await session.refresh(mapping)
            return mapping

    async def remove_market_mapping(self, mapping_id: int) -> bool:
        """Remove a market mapping by ID."""
        async with self.session() as session:
            result = await session.execute(
                select(MarketMapping).where(MarketMapping.id == mapping_id)
            )
            mapping = result.scalar_one_or_none()
            if mapping:
                await session.delete(mapping)
                return True
            return False

    # Order methods

    async def get_orders(
        self, status: str | None = None, limit: int = 50
    ) -> list[Order]:
        """Get orders with optional status filter."""
        async with self.session() as session:
            query = select(Order)
            if status:
                query = query.where(Order.status == status)
            query = query.order_by(Order.created_at.desc()).limit(limit)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_order_by_id(self, order_id: int) -> Order | None:
        """Get an order by ID."""
        async with self.session() as session:
            result = await session.execute(
                select(Order).where(Order.id == order_id)
            )
            return result.scalar_one_or_none()

    async def update_order_status(
        self, order_id: int, status: str, failure_reason: str | None = None
    ) -> Order | None:
        """Update order status."""
        async with self.session() as session:
            result = await session.execute(
                select(Order).where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
            if order:
                order.status = status
                if failure_reason:
                    order.failure_reason = failure_reason
                await session.flush()
                await session.refresh(order)
                return order
            return None

    async def create_order(
        self,
        market_id: str,
        side: str,
        requested_size: float,
        requested_price: float,
        signal_id: str | None = None,
    ) -> Order:
        """Create a new order."""
        async with self.session() as session:
            order = Order(
                market_id=market_id,
                side=side,
                requested_size=requested_size,
                requested_price=requested_price,
                signal_id=signal_id,
                status="pending",
            )
            session.add(order)
            await session.flush()
            await session.refresh(order)
            return order

    async def save_trade(
        self,
        wallet_address: str,
        market_id: str,
        side: str,
        size: float,
        price: float,
        source: str = "clob",
        ai_decision: bool | None = None,
        ai_confidence: float | None = None,
        ai_reasoning: str | None = None,
        executed: bool = False,
        executed_size: float | None = None,
        executed_price: float | None = None,
    ) -> Trade:
        """Save a trade record to the database.

        Args:
            wallet_address: The wallet address that made the trade
            market_id: The market ID
            side: YES or NO
            size: Trade size
            price: Trade price
            source: Signal source (clob or chain)
            ai_decision: Whether AI decided to copy
            ai_confidence: AI confidence level
            ai_reasoning: AI reasoning text
            executed: Whether trade was executed
            executed_size: Actual executed size
            executed_price: Actual executed price

        Returns:
            The created Trade object
        """
        async with self.session() as session:
            # Find wallet by address
            result = await session.execute(
                select(Wallet).where(Wallet.address == wallet_address.lower())
            )
            wallet = result.scalar_one_or_none()

            if not wallet:
                # Try without lowercase
                result = await session.execute(
                    select(Wallet).where(Wallet.address == wallet_address)
                )
                wallet = result.scalar_one_or_none()

            if not wallet:
                raise ValueError(f"Wallet not found: {wallet_address}")

            trade = Trade(
                wallet_id=wallet.id,
                market_id=market_id,
                side=side,
                size=size,
                price=price,
                source=source,
                ai_decision=ai_decision,
                ai_confidence=ai_confidence,
                ai_reasoning=ai_reasoning,
                executed=executed,
                executed_size=executed_size,
                executed_price=executed_price,
            )
            session.add(trade)
            await session.flush()
            await session.refresh(trade)
            return trade

    # Market Filter methods

    async def get_all_market_filters(self) -> list[MarketFilter]:
        """Get all market filters.

        Returns:
            List of MarketFilter objects.
        """
        async with self.session() as session:
            result = await session.execute(
                select(MarketFilter).order_by(MarketFilter.created_at.desc())
            )
            return list(result.scalars().all())

    async def add_market_filter(
        self,
        filter_type: str,
        value: str,
        action: str,
    ) -> MarketFilter:
        """Add a market filter.

        Args:
            filter_type: Type of filter (market_id, category, keyword).
            value: Value to match.
            action: Filter action (allow, deny).

        Returns:
            Created MarketFilter object.
        """
        async with self.session() as session:
            market_filter = MarketFilter(
                filter_type=filter_type,
                value=value,
                action=action,
            )
            session.add(market_filter)
            await session.flush()
            await session.refresh(market_filter)
            return market_filter

    async def remove_market_filter(self, filter_id: int) -> bool:
        """Remove a market filter by ID.

        Args:
            filter_id: The filter ID to remove.

        Returns:
            True if removed, False if not found.
        """
        async with self.session() as session:
            result = await session.execute(
                select(MarketFilter).where(MarketFilter.id == filter_id)
            )
            market_filter = result.scalar_one_or_none()
            if market_filter:
                await session.delete(market_filter)
                return True
            return False
