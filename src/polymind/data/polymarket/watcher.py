"""Polymarket wallet watcher service."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from polymind.data.models import SignalSource, TradeAction, TradeSignal
from polymind.data.polymarket.client import PolymarketClient
from polymind.data.polymarket.data_api import DataAPIClient
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class WalletWatcher:
    """Service for watching wallets and processing trade events.

    Monitors specified wallets and converts raw trade events into
    TradeSignal objects for further processing.
    """

    def __init__(
        self,
        client: PolymarketClient | None = None,
        data_api: DataAPIClient | None = None,
        on_signal: Callable[[TradeSignal], None] | None = None,
        poll_interval: float = 5.0,
    ) -> None:
        """Initialize the wallet watcher.

        Args:
            client: Optional Polymarket CLOB client instance.
            data_api: Optional Data API client for fetching trades.
            on_signal: Optional callback for when a signal is detected.
            poll_interval: Seconds between polling cycles.
        """
        self._client = client
        self._data_api = data_api
        self._on_signal = on_signal
        self._poll_interval = poll_interval
        self._wallets: set[str] = set()
        self._running = False
        self._seen_trades: set[str] = set()  # Track dedup_ids
        self._last_timestamp: dict[str, int] = {}  # Per-wallet last timestamp

    @property
    def wallets(self) -> set[str]:
        """Return a copy of the watched wallet addresses (lowercase).

        Returns:
            Set of watched wallet addresses in lowercase.
        """
        return self._wallets.copy()

    def add_wallet(self, address: str) -> None:
        """Add a wallet address to the watch list.

        Args:
            address: Wallet address to watch (will be converted to lowercase).
        """
        self._wallets.add(address.lower())

    def remove_wallet(self, address: str) -> None:
        """Remove a wallet address from the watch list.

        Args:
            address: Wallet address to remove (case insensitive).
        """
        self._wallets.discard(address.lower())

    @staticmethod
    def parse_trade_event(event: dict[str, Any]) -> TradeSignal:
        """Parse a raw trade event into a TradeSignal.

        Properly tracks both:
        - side: YES or NO (the outcome being traded)
        - action: BUY or SELL (whether buying or selling that outcome)

        Args:
            event: Raw trade event dictionary from the API.

        Returns:
            TradeSignal instance with parsed data.
        """
        # Get wallet address - Data API uses proxyWallet, CLOB uses maker/taker
        wallet = event.get("proxyWallet") or event.get("maker") or event.get("taker", "")
        wallet = wallet.lower() if wallet else ""

        # Get the outcome (YES/NO) - this is which side of the market
        outcome = event.get("outcome", "")
        if outcome:
            side = "YES" if outcome.lower() in ("yes", "up") else "NO"
        else:
            # Fallback: if no outcome, default to YES
            side = "YES"

        # Get the action (BUY/SELL) - this is the trade direction
        raw_side = event.get("side", "BUY")
        action = TradeAction.BUY if raw_side == "BUY" else TradeAction.SELL

        # Parse timestamp (can be string or int)
        timestamp_raw = event.get("timestamp", 0)
        if isinstance(timestamp_raw, str):
            timestamp_raw = int(timestamp_raw)
        timestamp = datetime.fromtimestamp(timestamp_raw, tz=UTC)

        # Get market ID - Data API uses conditionId or slug
        market_id = event.get("conditionId") or event.get("market") or event.get("slug", "")

        # Get token ID - Data API uses asset, CLOB uses asset_id
        token_id = event.get("asset") or event.get("asset_id", "")

        # Get tx hash - Data API uses transactionHash
        tx_hash = event.get("transactionHash") or event.get("transaction_hash", "")

        return TradeSignal(
            wallet=wallet,
            market_id=market_id,
            token_id=token_id,
            side=side,
            action=action,
            size=float(event.get("size", 0)),
            price=float(event.get("price", 0)),
            source=SignalSource.CLOB,
            timestamp=timestamp,
            tx_hash=tx_hash,
        )

    def process_event(self, event: dict[str, Any]) -> TradeSignal | None:
        """Process a trade event and return TradeSignal if wallet is watched.

        Args:
            event: Raw trade event dictionary.

        Returns:
            TradeSignal if the wallet is watched, None otherwise.
        """
        signal = self.parse_trade_event(event)

        if signal.wallet not in self._wallets:
            return None

        if self._on_signal:
            self._on_signal(signal)

        return signal

    async def _poll_wallet(self, wallet: str) -> list[TradeSignal]:
        """Poll a single wallet for new trades.

        Args:
            wallet: Wallet address to poll.

        Returns:
            List of new TradeSignal objects.
        """
        if not self._data_api:
            return []

        try:
            since_ts = self._last_timestamp.get(wallet)
            trades = await self._data_api.get_wallet_trades(
                wallet=wallet,
                limit=50,
                since_timestamp=since_ts,
            )

            new_signals = []
            for trade in trades:
                signal = self.parse_trade_event(trade)

                # Skip if already seen
                if signal.dedup_id in self._seen_trades:
                    continue

                self._seen_trades.add(signal.dedup_id)

                # Update last timestamp
                ts = trade.get("timestamp", 0)
                if isinstance(ts, str):
                    ts = int(ts)
                if ts > self._last_timestamp.get(wallet, 0):
                    self._last_timestamp[wallet] = ts

                new_signals.append(signal)

                if self._on_signal:
                    self._on_signal(signal)

            return new_signals

        except Exception as e:
            logger.error("Error polling wallet {}: {}", wallet, str(e))
            return []

    async def start(self) -> None:
        """Start the wallet watcher polling loop."""
        self._running = True
        logger.info("WalletWatcher started, watching {} wallets", len(self._wallets))

        while self._running:
            for wallet in list(self._wallets):
                if not self._running:
                    break
                await self._poll_wallet(wallet)

            if self._running:
                await asyncio.sleep(self._poll_interval)

        logger.info("WalletWatcher stopped")

    async def stop(self) -> None:
        """Stop the wallet watcher."""
        self._running = False
