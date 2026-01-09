"""Decision context for AI brain."""

from dataclasses import dataclass
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

    # Wallet performance
    wallet_win_rate: float
    wallet_avg_roi: float
    wallet_total_trades: int
    wallet_recent_performance: float

    # Market conditions
    market_liquidity: float
    market_spread: float

    # Risk state
    risk_daily_pnl: float
    risk_open_exposure: float
    risk_max_daily_loss: float

    def to_dict(self) -> dict[str, Any]:
        """Convert context to structured dictionary for AI consumption.

        Returns:
            Dictionary with nested structure matching design spec format:
            {
                "signal": {...},
                "wallet_metrics": {...},
                "market_data": {...},
                "risk_state": {...}
            }
        """
        return {
            "signal": {
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
            },
            "market_data": {
                "liquidity": self.market_liquidity,
                "spread": self.market_spread,
            },
            "risk_state": {
                "daily_pnl": self.risk_daily_pnl,
                "open_exposure": self.risk_open_exposure,
                "max_daily_loss": self.risk_max_daily_loss,
            },
        }


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
    ) -> None:
        """Initialize the context builder.

        Args:
            cache: Cache service for risk state
            market_service: Market data service for liquidity/spread
            db: Database service for wallet metrics
            max_daily_loss: Maximum allowed daily loss (default: $500)
        """
        self._cache = cache
        self._market_service = market_service
        self._db = db
        self._max_daily_loss = max_daily_loss

    async def build(self, signal: TradeSignal) -> DecisionContext:
        """Build a DecisionContext from a trade signal.

        Assembles all relevant data needed for AI decision making:
        - Signal data from the incoming trade
        - Wallet performance metrics from database
        - Market conditions from market service
        - Risk state from cache

        Args:
            signal: The incoming trade signal to build context for

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

        # Get market conditions
        liquidity = await self._market_service.get_liquidity(signal.token_id)
        spread = await self._market_service.get_spread(signal.token_id)

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
            # Wallet performance
            wallet_win_rate=wallet_metrics.get("win_rate", 0.0),
            wallet_avg_roi=wallet_metrics.get("avg_roi", 0.0),
            wallet_total_trades=wallet_metrics.get("total_trades", 0),
            wallet_recent_performance=wallet_metrics.get("recent_performance", 0.0),
            # Market conditions
            market_liquidity=liquidity,
            market_spread=spread,
            # Risk state
            risk_daily_pnl=daily_pnl,
            risk_open_exposure=open_exposure,
            risk_max_daily_loss=self._max_daily_loss,
        )
