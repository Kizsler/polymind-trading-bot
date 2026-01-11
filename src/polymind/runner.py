"""Main bot runner for PolyMind."""

import asyncio
import sys

from polymind.config.settings import Settings, load_settings
from polymind.core.brain.claude import ClaudeClient
from polymind.core.brain.context import DecisionContextBuilder
from polymind.core.brain.decision import AIDecision
from polymind.core.brain.orchestrator import DecisionBrain
from polymind.core.execution.paper import ExecutionResult, PaperExecutor
from polymind.core.intelligence.filters import MarketFilterManager
from polymind.core.risk.manager import RiskManager
from polymind.data.kalshi.client import KalshiClient
from polymind.data.models import TradeSignal
from polymind.data.polymarket.client import PolymarketClient
from polymind.data.polymarket.data_api import DataAPIClient
from polymind.data.polymarket.markets import MarketDataService
from polymind.interfaces.api.websocket import manager as ws_manager
from polymind.services.arbitrage import ArbitrageMonitorService
from polymind.services.monitor import WalletMonitorService
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
        self._data_api: DataAPIClient | None = None
        self._monitor: WalletMonitorService | None = None
        self._brain: DecisionBrain | None = None
        self._filter_manager: MarketFilterManager | None = None
        self._arbitrage_monitor: ArbitrageMonitorService | None = None
        self._kalshi_client: KalshiClient | None = None
        self._polymarket_client: PolymarketClient | None = None
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._stopping: bool = False

    async def _on_trade_signal(self, signal: TradeSignal) -> None:
        """Handle a detected trade signal.

        Routes signals to the DecisionBrain for AI evaluation,
        or logs them if the brain is not configured.

        Args:
            signal: The detected trade signal.
        """
        logger.info(
            "Trade detected: wallet={} market={} side={} size=${:.2f}",
            signal.wallet[:10],
            signal.market_id[:20] if signal.market_id else "unknown",
            signal.side,
            signal.size,
        )

        # Check emergency stop
        if self._cache and await self._cache.is_stopped():
            logger.warning("Trade blocked: Emergency stop is active")
            return

        # Check market filters before processing
        if self._filter_manager and self._db:
            try:
                filters = await self._filter_manager.get_filters()
                if filters:
                    # Use market_id as both identifier and title for now
                    # Category could be extracted from market data if available
                    is_allowed = self._filter_manager.is_market_allowed(
                        market_id=signal.market_id or "",
                        category="",  # No category in signal yet
                        title=signal.market_id or "",
                        filters=filters,
                    )
                    if not is_allowed:
                        logger.info(
                            "Market filtered out by deny list: {}",
                            signal.market_id[:20] if signal.market_id else "unknown",
                        )
                        return
            except Exception as e:
                logger.warning("Error checking market filters: {}", str(e))

        if self._brain:
            try:
                result = await self._brain.process(signal)
                if result.success:
                    logger.info(
                        "Trade executed: size=${:.2f} price={:.4f} paper={}",
                        result.executed_size,
                        result.executed_price,
                        result.paper_mode,
                    )
                else:
                    logger.info("Trade not executed: {}", result.message)

                # Save trade to database
                await self._save_trade_record(signal, result)

                # Broadcast trade event to WebSocket clients
                await self._broadcast_trade(signal, result)

                # Broadcast updated status
                await self._broadcast_status()

            except Exception as e:
                logger.error("Error processing signal: {}", str(e))
        else:
            logger.warning("DecisionBrain not configured - signal logged but not processed")

    async def _broadcast_trade(self, signal: TradeSignal, result: ExecutionResult) -> None:
        """Broadcast a trade event to WebSocket clients."""
        try:
            trade_data = {
                "wallet": signal.wallet,
                "market_id": signal.market_id,
                "side": signal.side,
                "size": signal.size,
                "decision": "COPY" if result.success else "SKIP",
                "executed": result.success,
                "executed_size": result.executed_size,
                "executed_price": result.executed_price,
                "message": result.message,
            }
            await ws_manager.broadcast("trade", trade_data)
        except Exception as e:
            logger.warning("Failed to broadcast trade: {}", str(e))

    async def _broadcast_status(self) -> None:
        """Broadcast current status to WebSocket clients."""
        if not self._cache:
            return
        try:
            status_data = {
                "mode": await self._cache.get_mode(),
                "daily_pnl": await self._cache.get_daily_pnl(),
                "open_exposure": await self._cache.get_open_exposure(),
            }
            await ws_manager.broadcast("status", status_data)
        except Exception as e:
            logger.warning("Failed to broadcast status: {}", str(e))

    async def _save_trade_record(
        self, signal: TradeSignal, result: ExecutionResult
    ) -> None:
        """Save trade to database for tracking and analytics.

        Args:
            signal: The original trade signal
            result: The execution result
        """
        if not self._db:
            return
        try:
            await self._db.save_trade(
                wallet_address=signal.wallet,
                market_id=signal.market_id,
                side=signal.side,
                size=signal.size,
                price=signal.price,
                source=signal.source.value if hasattr(signal.source, 'value') else str(signal.source),
                ai_decision=result.success,
                ai_confidence=None,  # Would need to extract from decision
                ai_reasoning=result.message,
                executed=result.success,
                executed_size=result.executed_size if result.success else None,
                executed_price=result.executed_price if result.success else None,
            )
            logger.debug("Trade saved to database")
        except Exception as e:
            logger.warning("Failed to save trade: {}", str(e))

    def _setup_brain(self) -> DecisionBrain | None:
        """Set up the DecisionBrain with all dependencies.

        Returns:
            Configured DecisionBrain or None if API key not set.
        """
        if not self._settings or not self._settings.claude.api_key:
            logger.warning(
                "Claude API key not configured - AI decisions disabled. "
                "Set POLYMIND_CLAUDE_API_KEY to enable."
            )
            return None

        # Create Claude client
        claude_client = ClaudeClient(
            api_key=self._settings.claude.api_key,
            model=self._settings.claude.model,
            max_tokens=self._settings.claude.max_tokens,
        )

        # Create market data service (for context building)
        polymarket_client = PolymarketClient(settings=self._settings)
        market_service = MarketDataService(
            client=polymarket_client,
            cache=self._cache,
        )

        # Create context builder
        context_builder = DecisionContextBuilder(
            cache=self._cache,
            market_service=market_service,
            db=self._db,
            max_daily_loss=self._settings.risk.max_daily_loss,
        )

        # Create risk manager
        risk_manager = RiskManager(
            cache=self._cache,
            max_daily_loss=self._settings.risk.max_daily_loss,
            max_total_exposure=self._settings.risk.max_total_exposure,
            max_single_trade=self._settings.risk.max_single_trade,
        )

        # Create paper executor
        executor = PaperExecutor(cache=self._cache)

        # Assemble the brain
        return DecisionBrain(
            context_builder=context_builder,
            claude_client=claude_client,
            risk_manager=risk_manager,
            executor=executor,
            cache=self._cache,
        )

    def _setup_arbitrage_monitor(self) -> ArbitrageMonitorService | None:
        """Set up arbitrage monitor if enabled.

        Returns:
            ArbitrageMonitorService or None if disabled.
        """
        if not self._settings or not self._settings.arbitrage.enabled:
            logger.info("Arbitrage monitoring disabled")
            return None

        # Create Kalshi client (read-only, no auth needed)
        self._kalshi_client = KalshiClient()

        # Create Polymarket client for price lookups
        self._polymarket_client = PolymarketClient(settings=self._settings)

        return ArbitrageMonitorService(
            kalshi_client=self._kalshi_client,
            polymarket_client=self._polymarket_client,
            db=self._db,
            min_spread=self._settings.arbitrage.min_spread,
            max_signal_size=self._settings.arbitrage.max_signal_size,
            poll_interval=self._settings.arbitrage.poll_interval,
            on_signal=self._on_trade_signal,
        )

    async def start(self) -> None:
        """Start the bot and initialize all components."""
        logger.info("Starting PolyMind...")

        try:
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

            # Initialize Data API client
            self._data_api = DataAPIClient()
            logger.info("Data API client initialized")

            # Initialize wallet monitor
            self._monitor = WalletMonitorService(
                db=self._db,
                data_api=self._data_api,
                on_signal=self._on_trade_signal,
                poll_interval=5.0,
            )
            logger.info("Wallet monitor initialized")

            # Initialize market filter manager
            self._filter_manager = MarketFilterManager(db=self._db)
            logger.info("Market filter manager initialized")

            # Initialize decision brain (may be None if API key not set)
            self._brain = self._setup_brain()
            if self._brain:
                logger.info("Decision brain initialized with Claude AI")

            # Initialize arbitrage monitor (may be None if disabled)
            self._arbitrage_monitor = self._setup_arbitrage_monitor()
            if self._arbitrage_monitor:
                logger.info("Arbitrage monitor initialized")

            # Set initial mode
            await self._cache.set_mode(self._settings.mode)
            logger.info("Mode set to: {}", self._settings.mode)

            # Clear shutdown event to indicate running state
            self._shutdown_event.clear()
            logger.info("PolyMind started successfully")
        except Exception as e:
            logger.error("Failed to start PolyMind: {}", str(e))
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the bot and close all connections."""
        # Guard against double-stop
        if self._stopping:
            return
        self._stopping = True

        logger.info("Stopping PolyMind...")
        self._shutdown_event.set()

        # Stop monitor
        if self._monitor:
            await self._monitor.stop()
            logger.info("Wallet monitor stopped")

        # Stop arbitrage monitor
        if self._arbitrage_monitor:
            await self._arbitrage_monitor.stop()
            logger.info("Arbitrage monitor stopped")

        # Close Kalshi client
        if self._kalshi_client:
            await self._kalshi_client.close()
            logger.info("Kalshi client closed")

        # Close Data API client
        if self._data_api:
            await self._data_api.close()
            logger.info("Data API client closed")

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

        # Setup signal handlers (platform-specific)
        if sys.platform != "win32":
            import signal

            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        try:
            # Start the wallet monitor as a background task
            if self._monitor:
                monitor_task = asyncio.create_task(self._monitor.start())
                logger.info("Wallet monitoring started")

            # Start the arbitrage monitor as a background task
            if self._arbitrage_monitor:
                arbitrage_task = asyncio.create_task(self._arbitrage_monitor.start())
                logger.info("Arbitrage monitoring started")

            # Main loop - keep running until shutdown
            while not self._shutdown_event.is_set():
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        finally:
            if not self._stopping:
                await self.stop()

    @property
    def is_running(self) -> bool:
        """Check if bot is running."""
        return not self._shutdown_event.is_set()


def run_bot() -> None:
    """Entry point to run the bot."""
    runner = BotRunner()
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        # On Windows, Ctrl+C raises KeyboardInterrupt
        pass
