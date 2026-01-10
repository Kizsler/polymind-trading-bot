"""Binance WebSocket feed for real-time price data."""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)

BINANCE_WS_URL = "wss://stream.binance.com:9443"


@dataclass
class PriceUpdate:
    """Real-time price update from Binance.

    Attributes:
        symbol: Trading pair symbol (e.g., "BTCUSDT").
        price: Current price.
        timestamp: Update timestamp in milliseconds.
    """

    symbol: str
    price: float
    timestamp: int


@dataclass
class BinanceFeed:
    """WebSocket feed for Binance real-time prices.

    Supports subscribing to price updates for crypto pairs.
    Price data is cached and accessible via get_price().

    Attributes:
        base_url: WebSocket base URL.
    """

    base_url: str = field(default=BINANCE_WS_URL)
    _prices: dict[str, PriceUpdate] = field(default_factory=dict, repr=False)
    _subscriptions: dict[str, list[Callable]] = field(default_factory=dict, repr=False)
    _ws: Any = field(default=None, repr=False)
    _connected: bool = field(default=False, repr=False)
    _receive_task: asyncio.Task | None = field(default=None, repr=False)

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected and self._ws is not None

    async def connect(self, symbols: list[str]) -> None:
        """Connect to Binance WebSocket.

        Args:
            symbols: List of trading pair symbols to subscribe to.
        """
        try:
            import websockets
        except ImportError:
            logger.error("websockets package not installed, cannot connect to Binance")
            return

        streams = "/".join(f"{s.lower()}@trade" for s in symbols)
        url = f"{self.base_url}/stream?streams={streams}"

        logger.info("Connecting to Binance WebSocket: {}", url[:50])

        self._ws = await websockets.connect(url)
        self._connected = True

        # Start receiving messages
        self._receive_task = asyncio.create_task(self._receive_loop())

        logger.info("Connected to Binance, subscribed to {} symbols", len(symbols))

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        self._connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

        logger.info("Disconnected from Binance")

    async def _receive_loop(self) -> None:
        """Receive and process messages from WebSocket."""
        while self._connected and self._ws:
            try:
                raw = await self._ws.recv()
                data = json.loads(raw)

                # Binance streams wrap data in {"stream": ..., "data": ...}
                if "data" in data:
                    await self._process_message(data["data"])
                else:
                    await self._process_message(data)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error receiving Binance message: {}", str(e))
                await asyncio.sleep(1)

    async def _process_message(self, message: dict[str, Any]) -> None:
        """Process a trade message.

        Args:
            message: Trade message from Binance.
        """
        if message.get("e") != "trade":
            return

        symbol = message.get("s", "")
        price_str = message.get("p", "0")
        timestamp = message.get("T", 0)

        try:
            price = float(price_str)
        except ValueError:
            return

        update = PriceUpdate(
            symbol=symbol,
            price=price,
            timestamp=timestamp,
        )

        # Cache the price
        self._prices[symbol] = update

        # Trigger callbacks
        for callback in self._subscriptions.get(symbol, []):
            try:
                await callback(update)
            except Exception as e:
                logger.error("Error in price callback: {}", str(e))

    async def get_price(self, symbol: str) -> PriceUpdate | None:
        """Get cached price for a symbol.

        Args:
            symbol: Trading pair symbol.

        Returns:
            PriceUpdate or None if no data.
        """
        return self._prices.get(symbol)

    async def get_all_prices(self) -> dict[str, PriceUpdate]:
        """Get all cached prices.

        Returns:
            Dict of symbol to PriceUpdate.
        """
        return self._prices.copy()

    async def subscribe(
        self,
        symbol: str,
        callback: Callable[[PriceUpdate], Any],
    ) -> None:
        """Subscribe to price updates for a symbol.

        Args:
            symbol: Trading pair symbol.
            callback: Async callback function receiving PriceUpdate.
        """
        if symbol not in self._subscriptions:
            self._subscriptions[symbol] = []
        self._subscriptions[symbol].append(callback)

        logger.debug("Subscribed to {} price updates", symbol)

    async def unsubscribe(
        self,
        symbol: str,
        callback: Callable[[PriceUpdate], Any],
    ) -> None:
        """Unsubscribe from price updates.

        Args:
            symbol: Trading pair symbol.
            callback: Callback to remove.
        """
        if symbol in self._subscriptions:
            try:
                self._subscriptions[symbol].remove(callback)
            except ValueError:
                pass

        logger.debug("Unsubscribed from {} price updates", symbol)
