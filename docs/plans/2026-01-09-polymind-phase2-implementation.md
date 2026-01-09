# PolyMind Phase 2: Data Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the data ingestion layer to monitor Polymarket trades via CLOB API and Polygon on-chain, with deduplication and market data fetching.

**Architecture:** Async data collectors running in parallel - one for CLOB API WebSocket subscriptions, one for Polygon RPC polling. Both feed into a unified signal queue that deduplicates and forwards to the AI Decision Brain (Phase 3). Market data is cached in Redis.

**Tech Stack:** py-clob-client, web3.py, httpx, websockets, asyncio

---

## Task 1: Polymarket Client Wrapper

**Files:**
- Create: `src/polymind/data/__init__.py`
- Create: `src/polymind/data/polymarket/__init__.py`
- Create: `src/polymind/data/polymarket/client.py`
- Create: `tests/data/__init__.py`
- Create: `tests/data/polymarket/__init__.py`
- Create: `tests/data/polymarket/test_client.py`

**Step 1: Write failing test for client**

Create `tests/data/__init__.py`:
```python
"""Data layer tests."""
```

Create `tests/data/polymarket/__init__.py`:
```python
"""Polymarket tests."""
```

Create `tests/data/polymarket/test_client.py`:
```python
"""Tests for Polymarket client wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.data.polymarket.client import PolymarketClient


@pytest.fixture
def mock_clob_client() -> MagicMock:
    """Create mock CLOB client."""
    client = MagicMock()
    client.get_simplified_markets = MagicMock(return_value=[
        {"condition_id": "0x123", "question": "Will BTC hit 100k?"}
    ])
    client.get_order_book = MagicMock(return_value={
        "bids": [{"price": "0.65", "size": "100"}],
        "asks": [{"price": "0.67", "size": "150"}]
    })
    return client


def test_client_can_be_created() -> None:
    """Client should initialize without API key for read-only."""
    client = PolymarketClient()
    assert client is not None


def test_client_get_markets(mock_clob_client: MagicMock) -> None:
    """Client should fetch markets."""
    with patch(
        "polymind.data.polymarket.client.ClobClient",
        return_value=mock_clob_client
    ):
        client = PolymarketClient()
        markets = client.get_markets()
        assert len(markets) > 0
        assert "condition_id" in markets[0]


def test_client_get_orderbook(mock_clob_client: MagicMock) -> None:
    """Client should fetch orderbook for a market."""
    with patch(
        "polymind.data.polymarket.client.ClobClient",
        return_value=mock_clob_client
    ):
        client = PolymarketClient()
        book = client.get_orderbook("0x123")
        assert "bids" in book
        assert "asks" in book
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/polymarket/test_client.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Add py-clob-client dependency**

Update `pyproject.toml` dependencies:
```toml
dependencies = [
    # ... existing deps ...
    "py-clob-client>=0.34.0",
]
```

Run: `pip install -e ".[dev]"`

**Step 4: Implement client wrapper**

Create `src/polymind/data/__init__.py`:
```python
"""Data ingestion layer."""
```

Create `src/polymind/data/polymarket/__init__.py`:
```python
"""Polymarket data module."""

from polymind.data.polymarket.client import PolymarketClient

__all__ = ["PolymarketClient"]
```

Create `src/polymind/data/polymarket/client.py`:
```python
"""Polymarket CLOB API client wrapper."""

from typing import Any

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

from polymind.config.settings import Settings


class PolymarketClient:
    """Wrapper around Polymarket CLOB client."""

    CLOB_HOST = "https://clob.polymarket.com"
    CHAIN_ID = 137  # Polygon mainnet

    def __init__(
        self,
        private_key: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize client.

        Args:
            private_key: Wallet private key for authenticated requests.
            settings: Application settings.
        """
        self.settings = settings or Settings()
        self._private_key = private_key

        # Initialize read-only client
        self._client = ClobClient(
            host=self.CLOB_HOST,
            chain_id=self.CHAIN_ID,
        )

        # Set up authentication if private key provided
        if private_key:
            self._setup_auth(private_key)

    def _setup_auth(self, private_key: str) -> None:
        """Set up authenticated client."""
        self._client = ClobClient(
            host=self.CLOB_HOST,
            chain_id=self.CHAIN_ID,
            key=private_key,
        )
        # Derive API credentials
        creds = self._client.create_or_derive_api_creds()
        self._client.set_api_creds(creds)

    def get_markets(self) -> list[dict[str, Any]]:
        """Get all active markets.

        Returns:
            List of market dictionaries with condition_id, question, etc.
        """
        return self._client.get_simplified_markets()

    def get_market(self, condition_id: str) -> dict[str, Any] | None:
        """Get a specific market by condition ID.

        Args:
            condition_id: The market's condition ID.

        Returns:
            Market dictionary or None if not found.
        """
        markets = self.get_markets()
        for market in markets:
            if market.get("condition_id") == condition_id:
                return market
        return None

    def get_orderbook(self, token_id: str) -> dict[str, Any]:
        """Get orderbook for a token.

        Args:
            token_id: The token ID (YES or NO outcome).

        Returns:
            Orderbook with bids and asks.
        """
        return self._client.get_order_book(token_id)

    def get_price(self, token_id: str, side: str = "BUY") -> float:
        """Get current price for a token.

        Args:
            token_id: The token ID.
            side: BUY or SELL.

        Returns:
            Current price (0.0 to 1.0).
        """
        price = self._client.get_price(token_id, side)
        return float(price) if price else 0.0

    def get_midpoint(self, token_id: str) -> float:
        """Get midpoint price for a token.

        Args:
            token_id: The token ID.

        Returns:
            Midpoint price (0.0 to 1.0).
        """
        mid = self._client.get_midpoint(token_id)
        return float(mid) if mid else 0.0

    def get_last_trade_price(self, token_id: str) -> float:
        """Get last trade price for a token.

        Args:
            token_id: The token ID.

        Returns:
            Last trade price.
        """
        price = self._client.get_last_trade_price(token_id)
        return float(price) if price else 0.0
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/data/polymarket/test_client.py -v`
Expected: 3 passed

**Step 6: Commit**

```bash
git add src/polymind/data/ tests/data/ pyproject.toml
git commit -m "feat: add Polymarket CLOB client wrapper"
```

---

## Task 2: Trade Signal Data Model

**Files:**
- Create: `src/polymind/data/models.py`
- Create: `tests/data/test_models.py`

**Step 1: Write failing test for trade signal model**

Create `tests/data/test_models.py`:
```python
"""Tests for data models."""

from datetime import datetime, timezone

import pytest

from polymind.data.models import TradeSignal, SignalSource


def test_trade_signal_from_dict() -> None:
    """TradeSignal should be created from dictionary."""
    data = {
        "wallet": "0x1234567890abcdef1234567890abcdef12345678",
        "market_id": "will-btc-hit-100k",
        "token_id": "0xabc123",
        "side": "YES",
        "size": 250.0,
        "price": 0.65,
        "source": "clob",
    }
    signal = TradeSignal.from_dict(data)

    assert signal.wallet == data["wallet"]
    assert signal.side == "YES"
    assert signal.size == 250.0
    assert signal.source == SignalSource.CLOB


def test_trade_signal_unique_id() -> None:
    """TradeSignal should generate unique ID for deduplication."""
    signal1 = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.5,
        source=SignalSource.CLOB,
        timestamp=datetime(2026, 1, 9, 12, 0, 0, tzinfo=timezone.utc),
    )
    signal2 = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.5,
        source=SignalSource.CHAIN,
        timestamp=datetime(2026, 1, 9, 12, 0, 0, tzinfo=timezone.utc),
    )

    # Same trade from different sources should have same dedup ID
    assert signal1.dedup_id == signal2.dedup_id


def test_trade_signal_different_trades_have_different_ids() -> None:
    """Different trades should have different dedup IDs."""
    signal1 = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.5,
        source=SignalSource.CLOB,
        timestamp=datetime(2026, 1, 9, 12, 0, 0, tzinfo=timezone.utc),
    )
    signal2 = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="NO",  # Different side
        size=100.0,
        price=0.5,
        source=SignalSource.CLOB,
        timestamp=datetime(2026, 1, 9, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert signal1.dedup_id != signal2.dedup_id
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement trade signal model**

Create `src/polymind/data/models.py`:
```python
"""Data models for trade signals."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any


class SignalSource(Enum):
    """Source of a trade signal."""

    CLOB = "clob"
    CHAIN = "chain"


@dataclass
class TradeSignal:
    """A detected trade from a watched wallet.

    This represents a trade signal that needs to be evaluated
    by the AI Decision Brain.
    """

    wallet: str
    market_id: str
    token_id: str
    side: str  # YES or NO
    size: float
    price: float
    source: SignalSource
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tx_hash: str | None = None

    @property
    def dedup_id(self) -> str:
        """Generate a unique ID for deduplication.

        Same trade detected from different sources should have the same ID.
        Uses wallet + market + side + size + rounded timestamp.
        """
        # Round timestamp to nearest minute for dedup tolerance
        ts_rounded = self.timestamp.replace(second=0, microsecond=0)
        key = f"{self.wallet}:{self.market_id}:{self.side}:{self.size}:{ts_rounded.isoformat()}"
        return sha256(key.encode()).hexdigest()[:16]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TradeSignal":
        """Create TradeSignal from dictionary.

        Args:
            data: Dictionary with trade data.

        Returns:
            TradeSignal instance.
        """
        source = data.get("source", "clob")
        if isinstance(source, str):
            source = SignalSource(source)

        return cls(
            wallet=data["wallet"],
            market_id=data["market_id"],
            token_id=data.get("token_id", ""),
            side=data["side"],
            size=float(data["size"]),
            price=float(data["price"]),
            source=source,
            timestamp=data.get("timestamp", datetime.now(timezone.utc)),
            tx_hash=data.get("tx_hash"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "wallet": self.wallet,
            "market_id": self.market_id,
            "token_id": self.token_id,
            "side": self.side,
            "size": self.size,
            "price": self.price,
            "source": self.source.value,
            "timestamp": self.timestamp.isoformat(),
            "tx_hash": self.tx_hash,
            "dedup_id": self.dedup_id,
        }
```

Update `src/polymind/data/__init__.py`:
```python
"""Data ingestion layer."""

from polymind.data.models import TradeSignal, SignalSource

__all__ = ["TradeSignal", "SignalSource"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/data/test_models.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/polymind/data/ tests/data/
git commit -m "feat: add TradeSignal data model with deduplication"
```

---

## Task 3: Wallet Watcher Service

**Files:**
- Create: `src/polymind/data/polymarket/watcher.py`
- Create: `tests/data/polymarket/test_watcher.py`

**Step 1: Write failing test for watcher**

Create `tests/data/polymarket/test_watcher.py`:
```python
"""Tests for wallet watcher service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.data.models import TradeSignal, SignalSource
from polymind.data.polymarket.watcher import WalletWatcher


@pytest.fixture
def mock_client() -> MagicMock:
    """Create mock Polymarket client."""
    client = MagicMock()
    return client


@pytest.fixture
def watcher(mock_client: MagicMock) -> WalletWatcher:
    """Create watcher with mock client."""
    return WalletWatcher(client=mock_client)


def test_watcher_add_wallet(watcher: WalletWatcher) -> None:
    """Watcher should track added wallets."""
    watcher.add_wallet("0x123")
    assert "0x123" in watcher.wallets


def test_watcher_remove_wallet(watcher: WalletWatcher) -> None:
    """Watcher should remove wallets."""
    watcher.add_wallet("0x123")
    watcher.remove_wallet("0x123")
    assert "0x123" not in watcher.wallets


def test_watcher_parse_trade_event() -> None:
    """Watcher should parse trade events into signals."""
    event = {
        "maker": "0x123abc",
        "market": "will-btc-hit-100k",
        "asset_id": "token123",
        "side": "BUY",
        "size": "100.5",
        "price": "0.65",
        "timestamp": "1704816000",
    }

    signal = WalletWatcher.parse_trade_event(event)

    assert signal.wallet == "0x123abc"
    assert signal.side == "YES"  # BUY on Polymarket = YES
    assert signal.size == 100.5
    assert signal.price == 0.65
    assert signal.source == SignalSource.CLOB


@pytest.mark.asyncio
async def test_watcher_filters_unwatched_wallets(
    watcher: WalletWatcher,
) -> None:
    """Watcher should ignore trades from unwatched wallets."""
    watcher.add_wallet("0xwatched")

    # Trade from watched wallet
    watched_event = {
        "maker": "0xwatched",
        "market": "market1",
        "asset_id": "token1",
        "side": "BUY",
        "size": "100",
        "price": "0.5",
        "timestamp": "1704816000",
    }

    # Trade from unwatched wallet
    unwatched_event = {
        "maker": "0xunwatched",
        "market": "market1",
        "asset_id": "token1",
        "side": "BUY",
        "size": "100",
        "price": "0.5",
        "timestamp": "1704816000",
    }

    # Should process watched
    signal = watcher.process_event(watched_event)
    assert signal is not None

    # Should ignore unwatched
    signal = watcher.process_event(unwatched_event)
    assert signal is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/polymarket/test_watcher.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement wallet watcher**

Create `src/polymind/data/polymarket/watcher.py`:
```python
"""Wallet watcher service for Polymarket."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from polymind.data.models import SignalSource, TradeSignal
from polymind.data.polymarket.client import PolymarketClient

logger = logging.getLogger(__name__)


class WalletWatcher:
    """Watches wallets for trades on Polymarket.

    Monitors trades via CLOB API and emits TradeSignals
    for wallets we're tracking.
    """

    def __init__(
        self,
        client: PolymarketClient | None = None,
        on_signal: Callable[[TradeSignal], None] | None = None,
    ) -> None:
        """Initialize watcher.

        Args:
            client: Polymarket client instance.
            on_signal: Callback for new trade signals.
        """
        self.client = client or PolymarketClient()
        self.on_signal = on_signal
        self._wallets: set[str] = set()
        self._running = False

    @property
    def wallets(self) -> set[str]:
        """Get set of watched wallet addresses."""
        return self._wallets.copy()

    def add_wallet(self, address: str) -> None:
        """Add a wallet to watch.

        Args:
            address: Wallet address (lowercase).
        """
        self._wallets.add(address.lower())
        logger.info(f"Added wallet to watch: {address[:10]}...")

    def remove_wallet(self, address: str) -> None:
        """Remove a wallet from watching.

        Args:
            address: Wallet address.
        """
        self._wallets.discard(address.lower())
        logger.info(f"Removed wallet from watch: {address[:10]}...")

    @staticmethod
    def parse_trade_event(event: dict[str, Any]) -> TradeSignal:
        """Parse a trade event into a TradeSignal.

        Args:
            event: Raw trade event from API.

        Returns:
            Parsed TradeSignal.
        """
        # Map BUY/SELL to YES/NO
        side = "YES" if event.get("side") == "BUY" else "NO"

        # Parse timestamp
        ts = event.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        elif isinstance(ts, int | float):
            ts = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        return TradeSignal(
            wallet=event.get("maker", event.get("taker", "")),
            market_id=event.get("market", ""),
            token_id=event.get("asset_id", ""),
            side=side,
            size=float(event.get("size", 0)),
            price=float(event.get("price", 0)),
            source=SignalSource.CLOB,
            timestamp=ts,
            tx_hash=event.get("transaction_hash"),
        )

    def process_event(self, event: dict[str, Any]) -> TradeSignal | None:
        """Process a trade event, filtering for watched wallets.

        Args:
            event: Raw trade event.

        Returns:
            TradeSignal if from watched wallet, None otherwise.
        """
        wallet = event.get("maker", event.get("taker", "")).lower()

        if wallet not in self._wallets:
            return None

        signal = self.parse_trade_event(event)
        logger.info(
            f"Trade signal: {signal.wallet[:10]}... "
            f"{signal.side} {signal.size} @ {signal.price}"
        )

        if self.on_signal:
            self.on_signal(signal)

        return signal

    async def start(self) -> None:
        """Start watching for trades.

        This is a placeholder for WebSocket subscription.
        Full implementation requires WebSocket connection to
        wss://ws-subscriptions-clob.polymarket.com
        """
        self._running = True
        logger.info(f"Wallet watcher started, watching {len(self._wallets)} wallets")

        # Placeholder: In production, connect to WebSocket
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop watching for trades."""
        self._running = False
        logger.info("Wallet watcher stopped")
```

Update `src/polymind/data/polymarket/__init__.py`:
```python
"""Polymarket data module."""

from polymind.data.polymarket.client import PolymarketClient
from polymind.data.polymarket.watcher import WalletWatcher

__all__ = ["PolymarketClient", "WalletWatcher"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/data/polymarket/test_watcher.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/polymind/data/polymarket/ tests/data/polymarket/
git commit -m "feat: add wallet watcher service for Polymarket"
```

---

## Task 4: Signal Queue with Deduplication

**Files:**
- Create: `src/polymind/data/queue.py`
- Create: `tests/data/test_queue.py`

**Step 1: Write failing test for signal queue**

Create `tests/data/test_queue.py`:
```python
"""Tests for signal queue."""

from datetime import datetime, timezone

import pytest

from polymind.data.models import SignalSource, TradeSignal
from polymind.data.queue import SignalQueue


@pytest.fixture
def queue() -> SignalQueue:
    """Create empty signal queue."""
    return SignalQueue(max_size=100, dedup_window_seconds=60)


@pytest.fixture
def sample_signal() -> TradeSignal:
    """Create sample trade signal."""
    return TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.5,
        source=SignalSource.CLOB,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_queue_add_and_get(
    queue: SignalQueue,
    sample_signal: TradeSignal,
) -> None:
    """Queue should add and retrieve signals."""
    await queue.put(sample_signal)
    result = await queue.get()
    assert result.wallet == sample_signal.wallet


@pytest.mark.asyncio
async def test_queue_deduplicates(
    queue: SignalQueue,
    sample_signal: TradeSignal,
) -> None:
    """Queue should reject duplicate signals."""
    await queue.put(sample_signal)

    # Same signal from different source
    duplicate = TradeSignal(
        wallet=sample_signal.wallet,
        market_id=sample_signal.market_id,
        token_id=sample_signal.token_id,
        side=sample_signal.side,
        size=sample_signal.size,
        price=sample_signal.price,
        source=SignalSource.CHAIN,  # Different source
        timestamp=sample_signal.timestamp,
    )

    added = await queue.put(duplicate)
    assert added is False  # Duplicate rejected


@pytest.mark.asyncio
async def test_queue_accepts_different_signals(
    queue: SignalQueue,
    sample_signal: TradeSignal,
) -> None:
    """Queue should accept different signals."""
    await queue.put(sample_signal)

    different = TradeSignal(
        wallet="0x456",  # Different wallet
        market_id=sample_signal.market_id,
        token_id=sample_signal.token_id,
        side=sample_signal.side,
        size=sample_signal.size,
        price=sample_signal.price,
        source=SignalSource.CLOB,
        timestamp=sample_signal.timestamp,
    )

    added = await queue.put(different)
    assert added is True


@pytest.mark.asyncio
async def test_queue_size(queue: SignalQueue, sample_signal: TradeSignal) -> None:
    """Queue should report correct size."""
    assert queue.size == 0
    await queue.put(sample_signal)
    assert queue.size == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/test_queue.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement signal queue**

Create `src/polymind/data/queue.py`:
```python
"""Signal queue with deduplication."""

import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timezone

from polymind.data.models import TradeSignal

logger = logging.getLogger(__name__)


class SignalQueue:
    """Async queue for trade signals with deduplication.

    Signals from multiple sources (CLOB API, on-chain) are
    deduplicated based on their dedup_id before being processed.
    """

    def __init__(
        self,
        max_size: int = 1000,
        dedup_window_seconds: int = 300,
    ) -> None:
        """Initialize signal queue.

        Args:
            max_size: Maximum queue size.
            dedup_window_seconds: How long to remember seen signals.
        """
        self.max_size = max_size
        self.dedup_window_seconds = dedup_window_seconds

        self._queue: asyncio.Queue[TradeSignal] = asyncio.Queue(maxsize=max_size)
        self._seen: OrderedDict[str, datetime] = OrderedDict()
        self._lock = asyncio.Lock()

    @property
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    async def put(self, signal: TradeSignal) -> bool:
        """Add a signal to the queue if not duplicate.

        Args:
            signal: Trade signal to add.

        Returns:
            True if added, False if duplicate.
        """
        async with self._lock:
            # Clean old entries
            self._clean_old_entries()

            # Check for duplicate
            if signal.dedup_id in self._seen:
                logger.debug(f"Duplicate signal rejected: {signal.dedup_id}")
                return False

            # Add to seen set
            self._seen[signal.dedup_id] = datetime.now(timezone.utc)

        # Add to queue
        try:
            self._queue.put_nowait(signal)
            logger.debug(f"Signal queued: {signal.dedup_id}")
            return True
        except asyncio.QueueFull:
            logger.warning("Signal queue full, dropping signal")
            return False

    async def get(self, timeout: float | None = None) -> TradeSignal:
        """Get next signal from queue.

        Args:
            timeout: Optional timeout in seconds.

        Returns:
            Next trade signal.

        Raises:
            asyncio.TimeoutError: If timeout expires.
        """
        if timeout:
            return await asyncio.wait_for(self._queue.get(), timeout)
        return await self._queue.get()

    def get_nowait(self) -> TradeSignal | None:
        """Get next signal without waiting.

        Returns:
            Next signal or None if queue empty.
        """
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def _clean_old_entries(self) -> None:
        """Remove entries older than dedup window."""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - self.dedup_window_seconds

        # Remove old entries (OrderedDict maintains insertion order)
        while self._seen:
            key, ts = next(iter(self._seen.items()))
            if ts.timestamp() < cutoff:
                del self._seen[key]
            else:
                break

    async def clear(self) -> None:
        """Clear the queue and seen set."""
        async with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self._seen.clear()
```

Update `src/polymind/data/__init__.py`:
```python
"""Data ingestion layer."""

from polymind.data.models import SignalSource, TradeSignal
from polymind.data.queue import SignalQueue

__all__ = ["SignalSource", "TradeSignal", "SignalQueue"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/data/test_queue.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/polymind/data/ tests/data/
git commit -m "feat: add signal queue with deduplication"
```

---

## Task 5: Market Data Service

**Files:**
- Create: `src/polymind/data/polymarket/markets.py`
- Create: `tests/data/polymarket/test_markets.py`

**Step 1: Write failing test for market data service**

Create `tests/data/polymarket/test_markets.py`:
```python
"""Tests for market data service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.data.polymarket.markets import MarketDataService


@pytest.fixture
def mock_client() -> MagicMock:
    """Create mock Polymarket client."""
    client = MagicMock()
    client.get_markets = MagicMock(return_value=[
        {
            "condition_id": "0x123",
            "question": "Will BTC hit 100k?",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }
    ])
    client.get_orderbook = MagicMock(return_value={
        "bids": [{"price": "0.65", "size": "1000"}],
        "asks": [{"price": "0.67", "size": "500"}],
    })
    client.get_midpoint = MagicMock(return_value=0.66)
    return client


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Create mock cache."""
    cache = AsyncMock()
    cache.get_market_price = AsyncMock(return_value=None)
    cache.set_market_price = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def service(mock_client: MagicMock, mock_cache: AsyncMock) -> MarketDataService:
    """Create service with mocks."""
    return MarketDataService(client=mock_client, cache=mock_cache)


def test_service_get_markets(service: MarketDataService) -> None:
    """Service should fetch and return markets."""
    markets = service.get_markets()
    assert len(markets) == 1
    assert markets[0]["condition_id"] == "0x123"


@pytest.mark.asyncio
async def test_service_get_market_liquidity(
    service: MarketDataService,
    mock_client: MagicMock,
) -> None:
    """Service should calculate market liquidity."""
    liquidity = await service.get_liquidity("yes_token")
    assert liquidity > 0


@pytest.mark.asyncio
async def test_service_get_spread(
    service: MarketDataService,
    mock_client: MagicMock,
) -> None:
    """Service should calculate bid-ask spread."""
    spread = await service.get_spread("yes_token")
    assert spread == pytest.approx(0.02, abs=0.001)  # 0.67 - 0.65


@pytest.mark.asyncio
async def test_service_caches_prices(
    service: MarketDataService,
    mock_cache: AsyncMock,
) -> None:
    """Service should cache market prices."""
    await service.get_price_cached("yes_token")
    mock_cache.set_market_price.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/polymarket/test_markets.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement market data service**

Create `src/polymind/data/polymarket/markets.py`:
```python
"""Market data service for Polymarket."""

import logging
from typing import Any

from polymind.data.polymarket.client import PolymarketClient
from polymind.storage.cache import Cache

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching and caching market data.

    Provides market information, prices, liquidity, and spread
    data with Redis caching for fast access.
    """

    def __init__(
        self,
        client: PolymarketClient | None = None,
        cache: Cache | None = None,
    ) -> None:
        """Initialize service.

        Args:
            client: Polymarket client.
            cache: Redis cache for market data.
        """
        self.client = client or PolymarketClient()
        self.cache = cache

    def get_markets(self) -> list[dict[str, Any]]:
        """Get all active markets.

        Returns:
            List of market data dictionaries.
        """
        return self.client.get_markets()

    def get_market(self, condition_id: str) -> dict[str, Any] | None:
        """Get a specific market.

        Args:
            condition_id: Market condition ID.

        Returns:
            Market data or None.
        """
        return self.client.get_market(condition_id)

    async def get_price_cached(self, token_id: str) -> float:
        """Get price with caching.

        Args:
            token_id: Token ID.

        Returns:
            Current price.
        """
        # Try cache first
        if self.cache:
            cached = await self.cache.get_market_price(token_id)
            if cached is not None:
                return cached

        # Fetch from API
        price = self.client.get_midpoint(token_id)

        # Cache the result
        if self.cache:
            await self.cache.set_market_price(token_id, price)

        return price

    async def get_liquidity(self, token_id: str) -> float:
        """Calculate total liquidity for a token.

        Sums bid and ask sizes from orderbook.

        Args:
            token_id: Token ID.

        Returns:
            Total liquidity in USD.
        """
        book = self.client.get_orderbook(token_id)

        bid_liquidity = sum(
            float(b.get("size", 0)) * float(b.get("price", 0))
            for b in book.get("bids", [])
        )
        ask_liquidity = sum(
            float(a.get("size", 0)) * float(a.get("price", 0))
            for a in book.get("asks", [])
        )

        return bid_liquidity + ask_liquidity

    async def get_spread(self, token_id: str) -> float:
        """Calculate bid-ask spread.

        Args:
            token_id: Token ID.

        Returns:
            Spread as decimal (e.g., 0.02 for 2%).
        """
        book = self.client.get_orderbook(token_id)

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        if not bids or not asks:
            return 0.0

        best_bid = float(bids[0].get("price", 0))
        best_ask = float(asks[0].get("price", 0))

        return best_ask - best_bid

    async def get_market_snapshot(self, token_id: str) -> dict[str, Any]:
        """Get complete market snapshot.

        Args:
            token_id: Token ID.

        Returns:
            Dictionary with price, liquidity, spread.
        """
        price = await self.get_price_cached(token_id)
        liquidity = await self.get_liquidity(token_id)
        spread = await self.get_spread(token_id)

        return {
            "token_id": token_id,
            "price": price,
            "liquidity": liquidity,
            "spread": spread,
        }
```

Update `src/polymind/data/polymarket/__init__.py`:
```python
"""Polymarket data module."""

from polymind.data.polymarket.client import PolymarketClient
from polymind.data.polymarket.markets import MarketDataService
from polymind.data.polymarket.watcher import WalletWatcher

__all__ = ["PolymarketClient", "MarketDataService", "WalletWatcher"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/data/polymarket/test_markets.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/polymind/data/polymarket/ tests/data/polymarket/
git commit -m "feat: add market data service with caching"
```

---

## Task 6: Data Layer Integration Tests

**Files:**
- Create: `tests/integration/test_data_layer.py`

**Step 1: Write integration tests**

Create `tests/integration/test_data_layer.py`:
```python
"""Integration tests for data layer."""

from datetime import datetime, timezone

import pytest

from polymind.data import SignalSource, TradeSignal, SignalQueue
from polymind.data.polymarket import PolymarketClient, WalletWatcher, MarketDataService


def test_polymarket_client_initializes() -> None:
    """Polymarket client should initialize for read-only access."""
    client = PolymarketClient()
    assert client is not None


def test_wallet_watcher_initializes() -> None:
    """Wallet watcher should initialize with client."""
    client = PolymarketClient()
    watcher = WalletWatcher(client=client)
    assert watcher is not None


def test_market_data_service_initializes() -> None:
    """Market data service should initialize."""
    client = PolymarketClient()
    service = MarketDataService(client=client)
    assert service is not None


@pytest.mark.asyncio
async def test_signal_queue_full_flow() -> None:
    """Signal queue should handle full add/get flow."""
    queue = SignalQueue(max_size=10, dedup_window_seconds=60)

    signal = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.5,
        source=SignalSource.CLOB,
        timestamp=datetime.now(timezone.utc),
    )

    # Add signal
    added = await queue.put(signal)
    assert added is True
    assert queue.size == 1

    # Get signal
    result = await queue.get(timeout=1.0)
    assert result.wallet == signal.wallet
    assert queue.size == 0


def test_watcher_processes_signals() -> None:
    """Watcher should process events for watched wallets."""
    watcher = WalletWatcher()
    watcher.add_wallet("0xwatched")

    event = {
        "maker": "0xwatched",
        "market": "market1",
        "asset_id": "token1",
        "side": "BUY",
        "size": "100",
        "price": "0.5",
        "timestamp": "1704816000",
    }

    signal = watcher.process_event(event)
    assert signal is not None
    assert signal.side == "YES"
```

**Step 2: Run all tests**

Run: `pytest -v`
Expected: All tests pass (including new data layer tests)

**Step 3: Run linting**

Run: `ruff check src tests`
Expected: All checks passed

**Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test: add data layer integration tests"
```

---

## Summary

Phase 2 Data Layer is complete when:

- [x] `PolymarketClient` wraps py-clob-client for API access
- [x] `TradeSignal` model with deduplication ID
- [x] `WalletWatcher` service monitors trades
- [x] `SignalQueue` deduplicates signals from multiple sources
- [x] `MarketDataService` provides cached market data
- [x] All tests pass

**Next Phase:** AI Decision Brain (Claude API integration)
