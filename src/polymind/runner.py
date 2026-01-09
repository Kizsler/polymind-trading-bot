"""Main bot runner for PolyMind."""

import asyncio
import sys

from polymind.config.settings import Settings, load_settings
from polymind.data.models import TradeSignal
from polymind.data.polymarket.data_api import DataAPIClient
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
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._stopping: bool = False

    async def _on_trade_signal(self, signal: TradeSignal) -> None:
        """Handle a detected trade signal.

        This is called when a tracked wallet makes a trade.
        For now, just log it. Later this will route to the DecisionBrain.

        Args:
            signal: The detected trade signal.
        """
        logger.info(
            "Trade detected! wallet={} market={} side={} size=${:.2f}",
            signal.wallet[:10],
            signal.market_id[:20] if signal.market_id else "unknown",
            signal.side,
            signal.size,
        )
        # TODO: Route to DecisionBrain for AI evaluation
        # decision = await self._brain.process(signal)

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
