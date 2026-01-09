"""Wallet monitoring service."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from polymind.data.models import TradeSignal
from polymind.data.polymarket.data_api import DataAPIClient
from polymind.data.polymarket.watcher import WalletWatcher
from polymind.storage.database import Database
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class WalletMonitorService:
    """Service that monitors tracked wallets for trades.

    Loads wallets from the database, watches them for trades,
    and routes detected signals to a callback for processing.
    """

    def __init__(
        self,
        db: Database,
        data_api: DataAPIClient | None = None,
        on_signal: Callable[[TradeSignal], Awaitable[None]] | None = None,
        poll_interval: float = 5.0,
    ) -> None:
        """Initialize the monitor service.

        Args:
            db: Database instance for loading wallets.
            data_api: Data API client for fetching trades.
            on_signal: Async callback for detected trade signals.
            poll_interval: Seconds between polling cycles.
        """
        self._db = db
        self._data_api = data_api
        self._on_signal = on_signal
        self._poll_interval = poll_interval
        self._running = False
        self._watcher: WalletWatcher | None = None
        self._wallet_aliases: dict[str, str | None] = {}  # address -> alias

    @property
    def watched_wallets(self) -> set[str]:
        """Get set of currently watched wallet addresses."""
        if self._watcher:
            return self._watcher.wallets
        return set()

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running

    def get_wallet_alias(self, address: str) -> str | None:
        """Get the alias for a wallet address.

        Args:
            address: Wallet address (case insensitive).

        Returns:
            Alias if found, None otherwise.
        """
        return self._wallet_aliases.get(address.lower())

    async def load_wallets(self) -> int:
        """Load enabled wallets from database into watcher.

        Returns:
            Number of wallets loaded.
        """
        wallets = await self._db.get_all_wallets()

        if not self._watcher:
            self._watcher = WalletWatcher(
                data_api=self._data_api,
                on_signal=self._sync_signal_handler,
                poll_interval=self._poll_interval,
            )

        # Clear and reload
        self._watcher._wallets.clear()
        self._wallet_aliases.clear()

        loaded = 0
        for wallet in wallets:
            if wallet.enabled:
                self._watcher.add_wallet(wallet.address)
                self._wallet_aliases[wallet.address.lower()] = wallet.alias
                loaded += 1

        logger.info("Loaded {} enabled wallets", loaded)
        return loaded

    async def refresh_wallets(self) -> int:
        """Refresh the wallet list from database.

        Returns:
            Number of wallets after refresh.
        """
        return await self.load_wallets()

    def _sync_signal_handler(self, signal: TradeSignal) -> None:
        """Synchronous wrapper to handle signals from WalletWatcher."""
        if self._on_signal:
            # Schedule the async callback
            asyncio.create_task(self._handle_signal(signal))

    async def _handle_signal(self, signal: TradeSignal) -> None:
        """Handle a detected trade signal.

        Args:
            signal: The detected trade signal.
        """
        alias = self.get_wallet_alias(signal.wallet)
        logger.info(
            "Trade detected: wallet={} ({}) market={} side={} size={}",
            signal.wallet[:10],
            alias or "unknown",
            signal.market_id[:20] if signal.market_id else "N/A",
            signal.side,
            signal.size,
        )

        if self._on_signal:
            try:
                await self._on_signal(signal)
            except Exception as e:
                logger.error("Error in signal handler: {}", str(e))

    async def start(self) -> None:
        """Start the monitoring service."""
        logger.info("Starting WalletMonitorService...")

        await self.load_wallets()

        self._running = True

        if self._watcher:
            await self._watcher.start()

    async def stop(self) -> None:
        """Stop the monitoring service."""
        logger.info("Stopping WalletMonitorService...")
        self._running = False

        if self._watcher:
            await self._watcher.stop()
