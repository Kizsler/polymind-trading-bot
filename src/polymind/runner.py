"""Main bot runner for PolyMind."""

import asyncio
import sys

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
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._stopping: bool = False

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

            # Set initial mode
            await self._cache.set_mode(self._settings.mode)
            logger.info(f"Mode set to: {self._settings.mode}")

            # Clear shutdown event to indicate running state
            self._shutdown_event.clear()
            logger.info("PolyMind started successfully")
        except Exception as e:
            logger.error(f"Failed to start PolyMind: {e}")
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
            while not self._shutdown_event.is_set():
                # Main loop - process signals, check wallets, etc.
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
