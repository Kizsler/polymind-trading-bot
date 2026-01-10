"""Decision context for AI brain."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from polymind.data.models import TradeSignal


class CacheProtocol(Protocol):
    """Protocol for cache operations needed by DecisionContextBuilder."""

    async def get_daily_pnl(self) -> float:
        """Get current daily P&L."""
        ...

    async def get_open_exposure(self) -> float:
        """Get current open exposure."""
        ...


class MarketServiceProtocol(Protocol):
    """Protocol for market service operations needed by DecisionContextBuilder."""

    async def get_liquidity(self, token_id: str) -> float:
        """Get market liquidity for a token."""
        ...

    async def get_spread(self, token_id: str) -> float:
        """Get bid-ask spread for a token."""
        ...


class DatabaseProtocol(Protocol):
    """Protocol for database operations needed by DecisionContextBuilder."""

    async def get_wallet_metrics(self, wallet_address: str) -> dict[str, Any] | None:
        """Get performance metrics for a wallet.

        Returns:
            Dictionary with keys: win_rate, avg_roi, total_trades, recent_performance
            or None if wallet not found.
        """
        ...

    async def get_wallet_by_address(self, address: str) -> Any | None:
        """Get wallet with controls by address."""
        ...


class WalletTrackerProtocol(Protocol):
    """Protocol for wallet tracker operations."""

    async def get_wallet_score(self, wallet_address: str) -> float:
        """Get confidence score for wallet."""
        ...


class MarketFilterProtocol(Protocol):
    """Protocol for market filter operations."""

    async def get_filters(self) -> list[Any]:
        """Get all filters."""
        ...

    def is_market_allowed(
        self,
        market_id: str,
        category: str,
        title: str,
        filters: list[Any],
    ) -> bool:
        """Check if market is allowed."""
        ...


class MarketAnalyzerProtocol(Protocol):
    """Protocol for market analyzer operations."""

    def get_quality_score(
        self,
        orderbook: dict[str, Any],
        price_history: list[float],
        resolution_time: Any,
    ) -> Any:
        """Get market quality score."""
        ...


@dataclass
class DecisionContext:
    """Context data assembled for AI decision making.

    Contains all relevant information the AI brain needs to make
    a trading decision, including signal data, wallet performance,
    market conditions, and current risk state.
    """

    # Signal data
    signal_wallet: str
    signal_market_id: str
    signal_side: str
    signal_size: float
    signal_price: float
    signal_type: str = "COPY_TRADE"  # COPY_TRADE, ARBITRAGE, PRICE_LAG

    # Wallet performance
    wallet_win_rate: float = 0.0
    wallet_avg_roi: float = 0.0
    wallet_total_trades: int = 0
    wallet_recent_performance: float = 0.0

    # Wallet intelligence (new)
    wallet_confidence_score: float = 0.5
    wallet_enabled: bool = True
    wallet_scale_factor: float = 1.0
    wallet_max_trade_size: float | None = None
    wallet_min_confidence: float = 0.0

    # Market conditions
    market_liquidity: float = 0.0
    market_spread: float = 0.0

    # Market intelligence (new)
    market_quality_score: float = 0.5
    market_allowed: bool = True
    market_filter_reason: str | None = None

    # Risk state
    risk_daily_pnl: float = 0.0
    risk_open_exposure: float = 0.0
    risk_max_daily_loss: float = 500.0

    # Arbitrage/Price Lag specific (new)
    arbitrage_spread: float | None = None
    arbitrage_direction: str | None = None
    price_lag_change: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert context to structured dictionary for AI consumption.

        Returns:
            Dictionary with nested structure for AI evaluation.
        """
        result = {
            "signal": {
                "type": self.signal_type,
                "wallet": self.signal_wallet,
                "market_id": self.signal_market_id,
                "side": self.signal_side,
                "size": self.signal_size,
                "price": self.signal_price,
            },
            "wallet_metrics": {
                "win_rate": self.wallet_win_rate,
                "avg_roi": self.wallet_avg_roi,
                "total_trades": self.wallet_total_trades,
                "recent_performance": self.wallet_recent_performance,
                "confidence_score": self.wallet_confidence_score,
            },
            "wallet_controls": {
                "enabled": self.wallet_enabled,
                "scale_factor": self.wallet_scale_factor,
                "max_trade_size": self.wallet_max_trade_size,
                "min_confidence": self.wallet_min_confidence,
            },
            "market_data": {
                "liquidity": self.market_liquidity,
                "spread": self.market_spread,
                "quality_score": self.market_quality_score,
                "allowed": self.market_allowed,
                "filter_reason": self.market_filter_reason,
            },
            "risk_state": {
                "daily_pnl": self.risk_daily_pnl,
                "open_exposure": self.risk_open_exposure,
                "max_daily_loss": self.risk_max_daily_loss,
            },
        }

        # Add arbitrage/price lag specific data if applicable
        if self.signal_type == "ARBITRAGE":
            result["arbitrage"] = {
                "spread": self.arbitrage_spread,
                "direction": self.arbitrage_direction,
            }
        elif self.signal_type == "PRICE_LAG":
            result["price_lag"] = {
                "binance_change": self.price_lag_change,
            }

        return result


class DecisionContextBuilder:
    """Builds DecisionContext by assembling data from multiple sources.

    Uses dependency injection via Protocol classes to allow for
    easy testing and flexibility in data sources.
    """

    def __init__(
        self,
        cache: CacheProtocol,
        market_service: MarketServiceProtocol,
        db: DatabaseProtocol,
        max_daily_loss: float = 500.0,
        wallet_tracker: WalletTrackerProtocol | None = None,
        market_filter: MarketFilterProtocol | None = None,
        market_analyzer: MarketAnalyzerProtocol | None = None,
    ) -> None:
        """Initialize the context builder.

        Args:
            cache: Cache service for risk state
            market_service: Market data service for liquidity/spread
            db: Database service for wallet metrics
            max_daily_loss: Maximum allowed daily loss (default: $500)
            wallet_tracker: Optional wallet tracker for confidence scores
            market_filter: Optional market filter for allow/deny lists
            market_analyzer: Optional market analyzer for quality scores
        """
        self._cache = cache
        self._market_service = market_service
        self._db = db
        self._max_daily_loss = max_daily_loss
        self._wallet_tracker = wallet_tracker
        self._market_filter = market_filter
        self._market_analyzer = market_analyzer

    async def build(
        self,
        signal: TradeSignal,
        signal_type: str = "COPY_TRADE",
        market_category: str = "",
        market_title: str = "",
        orderbook: dict[str, Any] | None = None,
        price_history: list[float] | None = None,
        resolution_time: Any = None,
        arbitrage_spread: float | None = None,
        arbitrage_direction: str | None = None,
        price_lag_change: float | None = None,
    ) -> DecisionContext:
        """Build a DecisionContext from a trade signal.

        Assembles all relevant data needed for AI decision making:
        - Signal data from the incoming trade
        - Wallet performance metrics and controls from database
        - Wallet confidence score from tracker
        - Market conditions and quality from market service
        - Market filter status
        - Risk state from cache

        Args:
            signal: The incoming trade signal to build context for
            signal_type: Type of signal (COPY_TRADE, ARBITRAGE, PRICE_LAG)
            market_category: Market category for filtering
            market_title: Market title for filtering
            orderbook: Optional orderbook for quality analysis
            price_history: Optional price history for volatility analysis
            resolution_time: Optional resolution time for time decay
            arbitrage_spread: Spread for arbitrage signals
            arbitrage_direction: Direction for arbitrage signals
            price_lag_change: Price change for price lag signals

        Returns:
            Complete DecisionContext ready for AI evaluation
        """
        # Get wallet metrics from database
        wallet_metrics = await self._db.get_wallet_metrics(signal.wallet)
        if wallet_metrics is None:
            wallet_metrics = {
                "win_rate": 0.0,
                "avg_roi": 0.0,
                "total_trades": 0,
                "recent_performance": 0.0,
            }

        # Get wallet controls
        wallet = await self._db.get_wallet_by_address(signal.wallet)
        wallet_enabled = True
        wallet_scale_factor = 1.0
        wallet_max_trade_size = None
        wallet_min_confidence = 0.0

        if wallet:
            wallet_enabled = getattr(wallet, "enabled", True)
            wallet_scale_factor = getattr(wallet, "scale_factor", 1.0)
            wallet_max_trade_size = getattr(wallet, "max_trade_size", None)
            wallet_min_confidence = getattr(wallet, "min_confidence", 0.0)

        # Get wallet confidence score
        wallet_confidence = 0.5
        if self._wallet_tracker:
            wallet_confidence = await self._wallet_tracker.get_wallet_score(signal.wallet)

        # Get market conditions
        liquidity = await self._market_service.get_liquidity(signal.token_id)
        spread = await self._market_service.get_spread(signal.token_id)

        # Get market quality score
        market_quality = 0.5
        if self._market_analyzer and orderbook and price_history and resolution_time:
            quality = self._market_analyzer.get_quality_score(
                orderbook, price_history, resolution_time
            )
            market_quality = getattr(quality, "overall_score", 0.5)

        # Check market filters
        market_allowed = True
        filter_reason = None
        if self._market_filter:
            filters = await self._market_filter.get_filters()
            market_allowed = self._market_filter.is_market_allowed(
                market_id=signal.market_id,
                category=market_category,
                title=market_title,
                filters=filters,
            )
            if not market_allowed:
                filter_reason = "Market blocked by filter"

        # Get risk state from cache
        daily_pnl = await self._cache.get_daily_pnl()
        open_exposure = await self._cache.get_open_exposure()

        return DecisionContext(
            # Signal data
            signal_wallet=signal.wallet,
            signal_market_id=signal.market_id,
            signal_side=signal.side,
            signal_size=signal.size,
            signal_price=signal.price,
            signal_type=signal_type,
            # Wallet performance
            wallet_win_rate=wallet_metrics.get("win_rate", 0.0),
            wallet_avg_roi=wallet_metrics.get("avg_roi", 0.0),
            wallet_total_trades=wallet_metrics.get("total_trades", 0),
            wallet_recent_performance=wallet_metrics.get("recent_performance", 0.0),
            # Wallet intelligence
            wallet_confidence_score=wallet_confidence,
            wallet_enabled=wallet_enabled,
            wallet_scale_factor=wallet_scale_factor,
            wallet_max_trade_size=wallet_max_trade_size,
            wallet_min_confidence=wallet_min_confidence,
            # Market conditions
            market_liquidity=liquidity,
            market_spread=spread,
            # Market intelligence
            market_quality_score=market_quality,
            market_allowed=market_allowed,
            market_filter_reason=filter_reason,
            # Risk state
            risk_daily_pnl=daily_pnl,
            risk_open_exposure=open_exposure,
            risk_max_daily_loss=self._max_daily_loss,
            # Arbitrage/Price Lag
            arbitrage_spread=arbitrage_spread,
            arbitrage_direction=arbitrage_direction,
            price_lag_change=price_lag_change,
        )
