"""SQLAlchemy database models."""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Wallet(Base):
    """Tracked wallet for copy trading."""

    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(42), unique=True, index=True)
    alias: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Per-wallet trading controls
    scale_factor: Mapped[float] = mapped_column(Float, default=1.0)
    max_trade_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
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
    last_trade_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
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
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    source: Mapped[str] = mapped_column(String(20))  # clob or chain

    # AI decision
    ai_decision: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    executed_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    executed_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    paper_mode: Mapped[bool] = mapped_column(Boolean, default=True)

    # Outcome
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    wallet: Mapped["Wallet"] = relationship(back_populates="trades")
    market_snapshot: Mapped[Optional["MarketSnapshot"]] = relationship(
        back_populates="trade"
    )


class MarketSnapshot(Base):
    """Market state at decision time."""

    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"), unique=True)
    market_id: Mapped[str] = mapped_column(String(200))
    liquidity: Mapped[float] = mapped_column(Float)
    spread: Mapped[float] = mapped_column(Float)
    time_to_resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
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
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class MarketFilter(Base):
    """Market allow/deny filter rules."""

    __tablename__ = "market_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    filter_type: Mapped[str] = mapped_column(String(20))  # market_id, category, keyword
    value: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(10))  # allow, deny
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class MarketMapping(Base):
    """Cross-platform market mappings for arbitrage."""

    __tablename__ = "market_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    polymarket_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    kalshi_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Order(Base):
    """Order lifecycle tracking."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    signal_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    market_id: Mapped[str] = mapped_column(String(200), index=True)
    side: Mapped[str] = mapped_column(String(10))  # BUY or SELL
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    requested_size: Mapped[float] = mapped_column(Float)
    filled_size: Mapped[float] = mapped_column(Float, default=0.0)
    requested_price: Mapped[float] = mapped_column(Float)
    filled_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
