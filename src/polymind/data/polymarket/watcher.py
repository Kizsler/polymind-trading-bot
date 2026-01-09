"""Polymarket wallet watcher service."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from polymind.data.models import SignalSource, TradeSignal
from polymind.data.polymarket.client import PolymarketClient


class WalletWatcher:
    """Service for watching wallets and processing trade events.

    Monitors specified wallets and converts raw trade events into
    TradeSignal objects for further processing.
    """

    def __init__(
        self,
        client: PolymarketClient | None = None,
        on_signal: Callable[[TradeSignal], None] | None = None,
    ) -> None:
        """Initialize the wallet watcher.

        Args:
            client: Optional Polymarket client instance.
            on_signal: Optional callback for when a signal is detected.
        """
        self._client = client
        self._on_signal = on_signal
        self._wallets: set[str] = set()
        self._running = False

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

        Maps BUY side to YES and SELL side to NO.
        Uses maker address if available, otherwise uses taker.

        Args:
            event: Raw trade event dictionary from the API.

        Returns:
            TradeSignal instance with parsed data.
        """
        # Get wallet address (prefer maker, fallback to taker)
        wallet = event.get("maker") or event.get("taker", "")
        wallet = wallet.lower()

        # Map BUY -> YES, SELL -> NO
        raw_side = event.get("side", "")
        side = "YES" if raw_side == "BUY" else "NO"

        # Parse timestamp (can be string or int)
        timestamp_raw = event.get("timestamp", 0)
        if isinstance(timestamp_raw, str):
            timestamp_raw = int(timestamp_raw)
        timestamp = datetime.fromtimestamp(timestamp_raw, tz=UTC)

        return TradeSignal(
            wallet=wallet,
            market_id=event.get("market", ""),
            token_id=event.get("asset_id", ""),
            side=side,
            size=float(event.get("size", 0)),
            price=float(event.get("price", 0)),
            source=SignalSource.CLOB,
            timestamp=timestamp,
            tx_hash=event.get("transaction_hash", ""),
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

    async def start(self) -> None:
        """Start the wallet watcher.

        Placeholder implementation that loops until stopped.
        """
        self._running = True
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the wallet watcher."""
        self._running = False
