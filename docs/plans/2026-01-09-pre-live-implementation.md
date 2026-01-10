# Pre-Live Complete Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete all features needed before going live - execution infrastructure, wallet intelligence, market intelligence, and external integrations.

**Architecture:** Four-phase build starting with execution layer, adding intelligence layers, then external data sources. Each phase builds on the previous. Paper trading remains active throughout; live execution stays dormant until wallet credentials added.

**Tech Stack:** Python 3.11+, FastAPI, PostgreSQL, Redis, httpx, websockets, pytest

---

## Phase 1: Live Execution Infrastructure

### Task 1.1: Slippage Guard

**Files:**
- Create: `src/polymind/core/execution/slippage.py`
- Test: `tests/core/execution/test_slippage.py`

**Step 1: Write the failing test**

```python
"""Tests for slippage protection."""

import pytest
from polymind.core.execution.slippage import SlippageGuard, SlippageExceededError


class TestSlippageGuard:
    """Tests for SlippageGuard."""

    def test_calculate_slippage_no_slippage(self) -> None:
        """Test slippage calculation when prices match."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        slippage = guard.calculate_slippage(
            expected_price=0.50,
            actual_price=0.50,
        )
        assert slippage == 0.0

    def test_calculate_slippage_within_threshold(self) -> None:
        """Test slippage within acceptable range."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        slippage = guard.calculate_slippage(
            expected_price=0.50,
            actual_price=0.51,
        )
        assert slippage == pytest.approx(2.0, rel=0.01)

    def test_calculate_slippage_exceeds_threshold(self) -> None:
        """Test slippage exceeding threshold."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        slippage = guard.calculate_slippage(
            expected_price=0.50,
            actual_price=0.55,
        )
        assert slippage == pytest.approx(10.0, rel=0.01)

    def test_check_slippage_passes(self) -> None:
        """Test check passes when within threshold."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        # Should not raise
        guard.check_slippage(expected_price=0.50, actual_price=0.51)

    def test_check_slippage_raises(self) -> None:
        """Test check raises when exceeding threshold."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        with pytest.raises(SlippageExceededError) as exc_info:
            guard.check_slippage(expected_price=0.50, actual_price=0.55)
        assert "10.0%" in str(exc_info.value)
        assert "2.0%" in str(exc_info.value)

    def test_estimate_fill_price_buy(self) -> None:
        """Test estimating fill price from orderbook for buy."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        orderbook = {
            "asks": [
                {"price": 0.50, "size": 100},
                {"price": 0.51, "size": 100},
                {"price": 0.52, "size": 100},
            ],
            "bids": [],
        }
        fill_price = guard.estimate_fill_price(
            orderbook=orderbook,
            side="BUY",
            size=150,
        )
        # 100 @ 0.50 + 50 @ 0.51 = 75.50 / 150 = 0.5033
        assert fill_price == pytest.approx(0.5033, rel=0.01)

    def test_estimate_fill_price_sell(self) -> None:
        """Test estimating fill price from orderbook for sell."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        orderbook = {
            "asks": [],
            "bids": [
                {"price": 0.50, "size": 100},
                {"price": 0.49, "size": 100},
                {"price": 0.48, "size": 100},
            ],
        }
        fill_price = guard.estimate_fill_price(
            orderbook=orderbook,
            side="SELL",
            size=150,
        )
        # 100 @ 0.50 + 50 @ 0.49 = 74.50 / 150 = 0.4967
        assert fill_price == pytest.approx(0.4967, rel=0.01)

    def test_estimate_fill_price_insufficient_liquidity(self) -> None:
        """Test when orderbook has insufficient liquidity."""
        guard = SlippageGuard(max_slippage_percent=2.0)
        orderbook = {
            "asks": [{"price": 0.50, "size": 50}],
            "bids": [],
        }
        with pytest.raises(ValueError, match="Insufficient liquidity"):
            guard.estimate_fill_price(
                orderbook=orderbook,
                side="BUY",
                size=100,
            )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/execution/test_slippage.py -v`
Expected: FAIL with "No module named 'polymind.core.execution.slippage'"

**Step 3: Write minimal implementation**

```python
"""Slippage protection for trade execution."""

from dataclasses import dataclass
from typing import Any


class SlippageExceededError(Exception):
    """Raised when slippage exceeds configured threshold."""

    pass


@dataclass
class SlippageGuard:
    """Guards against excessive slippage in trade execution.

    Attributes:
        max_slippage_percent: Maximum allowed slippage as percentage (e.g., 2.0 for 2%).
    """

    max_slippage_percent: float = 2.0

    def calculate_slippage(self, expected_price: float, actual_price: float) -> float:
        """Calculate slippage as percentage.

        Args:
            expected_price: The expected/limit price.
            actual_price: The actual/estimated fill price.

        Returns:
            Slippage as percentage (e.g., 2.0 for 2%).
        """
        if expected_price == 0:
            return 0.0
        return abs(actual_price - expected_price) / expected_price * 100

    def check_slippage(self, expected_price: float, actual_price: float) -> None:
        """Check if slippage is within acceptable range.

        Args:
            expected_price: The expected/limit price.
            actual_price: The actual/estimated fill price.

        Raises:
            SlippageExceededError: If slippage exceeds threshold.
        """
        slippage = self.calculate_slippage(expected_price, actual_price)
        if slippage > self.max_slippage_percent:
            raise SlippageExceededError(
                f"Slippage of {slippage:.1f}% exceeds maximum of {self.max_slippage_percent:.1f}%"
            )

    def estimate_fill_price(
        self,
        orderbook: dict[str, list[dict[str, Any]]],
        side: str,
        size: float,
    ) -> float:
        """Estimate the fill price based on orderbook depth.

        Args:
            orderbook: Orderbook with 'asks' and 'bids' lists.
            side: 'BUY' or 'SELL'.
            size: Size to fill in dollars.

        Returns:
            Estimated average fill price.

        Raises:
            ValueError: If insufficient liquidity.
        """
        levels = orderbook["asks"] if side == "BUY" else orderbook["bids"]

        remaining = size
        total_cost = 0.0

        for level in levels:
            level_price = level["price"]
            level_size = level["size"]

            fill_at_level = min(remaining, level_size)
            total_cost += fill_at_level * level_price
            remaining -= fill_at_level

            if remaining <= 0:
                break

        if remaining > 0:
            raise ValueError(f"Insufficient liquidity: needed {size}, available {size - remaining}")

        return total_cost / size
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/execution/test_slippage.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add src/polymind/core/execution/slippage.py tests/core/execution/test_slippage.py
git commit -m "feat(execution): add slippage guard with orderbook estimation"
```

---

### Task 1.2: Order State Model

**Files:**
- Modify: `src/polymind/storage/models.py`
- Create: `src/polymind/core/execution/order.py`
- Test: `tests/core/execution/test_order.py`

**Step 1: Write the failing test**

```python
"""Tests for order state management."""

import pytest
from polymind.core.execution.order import Order, OrderStatus


class TestOrder:
    """Tests for Order model."""

    def test_create_pending_order(self) -> None:
        """Test creating a new pending order."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        assert order.status == OrderStatus.PENDING
        assert order.filled_size == 0.0
        assert order.filled_price is None
        assert order.attempts == 0

    def test_order_mark_submitted(self) -> None:
        """Test marking order as submitted."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_submitted(external_id="ext_456")
        assert order.status == OrderStatus.SUBMITTED
        assert order.external_id == "ext_456"
        assert order.attempts == 1

    def test_order_mark_filled(self) -> None:
        """Test marking order as filled."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_submitted(external_id="ext_456")
        order.mark_filled(filled_size=100.0, filled_price=0.54)
        assert order.status == OrderStatus.FILLED
        assert order.filled_size == 100.0
        assert order.filled_price == 0.54

    def test_order_mark_partial(self) -> None:
        """Test marking order as partially filled."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_submitted(external_id="ext_456")
        order.mark_partial(filled_size=60.0, filled_price=0.54)
        assert order.status == OrderStatus.PARTIAL
        assert order.filled_size == 60.0
        assert order.remaining_size == 40.0

    def test_order_mark_failed(self) -> None:
        """Test marking order as failed."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        order.mark_failed(reason="Insufficient funds")
        assert order.status == OrderStatus.FAILED
        assert order.failure_reason == "Insufficient funds"

    def test_order_can_retry(self) -> None:
        """Test retry eligibility."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
            max_attempts=3,
        )
        order.mark_submitted(external_id="ext_1")
        order.mark_failed(reason="Timeout")
        assert order.can_retry is True

        order.mark_submitted(external_id="ext_2")
        order.mark_failed(reason="Timeout")
        assert order.can_retry is True

        order.mark_submitted(external_id="ext_3")
        order.mark_failed(reason="Timeout")
        assert order.can_retry is False

    def test_order_to_dict(self) -> None:
        """Test serialization to dict."""
        order = Order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            requested_size=100.0,
            requested_price=0.55,
        )
        data = order.to_dict()
        assert data["signal_id"] == "sig_123"
        assert data["status"] == "pending"
        assert "created_at" in data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/execution/test_order.py -v`
Expected: FAIL with "No module named 'polymind.core.execution.order'"

**Step 3: Write minimal implementation**

```python
"""Order state management for execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OrderStatus(str, Enum):
    """Order lifecycle status."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Order:
    """Represents a trade order through its lifecycle.

    Attributes:
        signal_id: ID of the originating trade signal.
        market_id: Polymarket market ID.
        side: 'BUY' or 'SELL'.
        requested_size: Requested trade size in dollars.
        requested_price: Requested limit price.
        max_attempts: Maximum retry attempts.
    """

    signal_id: str
    market_id: str
    side: str
    requested_size: float
    requested_price: float
    max_attempts: int = 3

    # State fields
    id: str | None = None
    external_id: str | None = None
    status: OrderStatus = OrderStatus.PENDING
    filled_size: float = 0.0
    filled_price: float | None = None
    attempts: int = 0
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def remaining_size(self) -> float:
        """Calculate remaining unfilled size."""
        return self.requested_size - self.filled_size

    @property
    def can_retry(self) -> bool:
        """Check if order is eligible for retry."""
        return (
            self.status == OrderStatus.FAILED
            and self.attempts < self.max_attempts
        )

    def mark_submitted(self, external_id: str) -> None:
        """Mark order as submitted to exchange."""
        self.external_id = external_id
        self.status = OrderStatus.SUBMITTED
        self.attempts += 1
        self.updated_at = datetime.now(timezone.utc)

    def mark_filled(self, filled_size: float, filled_price: float) -> None:
        """Mark order as fully filled."""
        self.filled_size = filled_size
        self.filled_price = filled_price
        self.status = OrderStatus.FILLED
        self.updated_at = datetime.now(timezone.utc)

    def mark_partial(self, filled_size: float, filled_price: float) -> None:
        """Mark order as partially filled."""
        self.filled_size = filled_size
        self.filled_price = filled_price
        self.status = OrderStatus.PARTIAL
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: str) -> None:
        """Mark order as failed."""
        self.failure_reason = reason
        self.status = OrderStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        """Mark order as cancelled."""
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Serialize order to dictionary."""
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "market_id": self.market_id,
            "side": self.side,
            "external_id": self.external_id,
            "status": self.status.value,
            "requested_size": self.requested_size,
            "requested_price": self.requested_price,
            "filled_size": self.filled_size,
            "filled_price": self.filled_price,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/execution/test_order.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add src/polymind/core/execution/order.py tests/core/execution/test_order.py
git commit -m "feat(execution): add Order model with lifecycle management"
```

---

### Task 1.3: Order Manager

**Files:**
- Create: `src/polymind/core/execution/manager.py`
- Test: `tests/core/execution/test_manager.py`

**Step 1: Write the failing test**

```python
"""Tests for order manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.execution.manager import OrderManager
from polymind.core.execution.order import Order, OrderStatus


class TestOrderManager:
    """Tests for OrderManager."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def manager(self, mock_cache: MagicMock) -> OrderManager:
        """Create order manager with mocks."""
        return OrderManager(cache=mock_cache, retry_delay=0.01)

    @pytest.mark.asyncio
    async def test_create_order(self, manager: OrderManager) -> None:
        """Test creating a new order."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )
        assert order.status == OrderStatus.PENDING
        assert order.signal_id == "sig_123"
        assert order.id is not None

    @pytest.mark.asyncio
    async def test_save_and_load_order(self, manager: OrderManager, mock_cache: MagicMock) -> None:
        """Test saving and loading order from cache."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )

        await manager.save_order(order)
        mock_cache.set.assert_called_once()

        # Simulate cache returning the order
        mock_cache.get.return_value = order.to_dict()
        loaded = await manager.get_order(order.id)
        assert loaded is not None
        assert loaded.signal_id == "sig_123"

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, manager: OrderManager) -> None:
        """Test successful execution on first try."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )

        # Mock executor that succeeds
        executor = AsyncMock()
        executor.submit_order.return_value = {
            "order_id": "ext_456",
            "status": "filled",
            "filled_size": 100.0,
            "filled_price": 0.54,
        }

        result = await manager.execute_with_retry(order, executor)
        assert result.status == OrderStatus.FILLED
        assert executor.submit_order.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_retries_on_failure(self, manager: OrderManager) -> None:
        """Test retry on transient failure."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
            max_attempts=3,
        )

        # Mock executor that fails twice then succeeds
        executor = AsyncMock()
        executor.submit_order.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            {
                "order_id": "ext_456",
                "status": "filled",
                "filled_size": 100.0,
                "filled_price": 0.54,
            },
        ]

        result = await manager.execute_with_retry(order, executor)
        assert result.status == OrderStatus.FILLED
        assert executor.submit_order.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausts_retries(self, manager: OrderManager) -> None:
        """Test failure after exhausting retries."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
            max_attempts=2,
        )

        # Mock executor that always fails
        executor = AsyncMock()
        executor.submit_order.side_effect = Exception("Timeout")

        result = await manager.execute_with_retry(order, executor)
        assert result.status == OrderStatus.FAILED
        assert executor.submit_order.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_partial_fill(self, manager: OrderManager) -> None:
        """Test handling partial fill."""
        order = await manager.create_order(
            signal_id="sig_123",
            market_id="market_abc",
            side="BUY",
            size=100.0,
            price=0.55,
        )

        # Mock executor returns partial fill
        executor = AsyncMock()
        executor.submit_order.return_value = {
            "order_id": "ext_456",
            "status": "partial",
            "filled_size": 60.0,
            "filled_price": 0.54,
        }
        executor.get_order_status.return_value = {
            "status": "partial",
            "filled_size": 60.0,
            "filled_price": 0.54,
        }

        result = await manager.execute_with_retry(order, executor)
        assert result.status == OrderStatus.PARTIAL
        assert result.filled_size == 60.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/execution/test_manager.py -v`
Expected: FAIL with "No module named 'polymind.core.execution.manager'"

**Step 3: Write minimal implementation**

```python
"""Order execution manager with retry logic."""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from polymind.core.execution.order import Order, OrderStatus
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class ExecutorProtocol(Protocol):
    """Protocol for order executors."""

    async def submit_order(
        self,
        market_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict[str, Any]:
        """Submit order to exchange."""
        ...

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get order status from exchange."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order on exchange."""
        ...


@dataclass
class OrderManager:
    """Manages order lifecycle with retry logic.

    Attributes:
        cache: Cache for order persistence.
        retry_delay: Base delay between retries in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
    """

    cache: Any
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0

    async def create_order(
        self,
        signal_id: str,
        market_id: str,
        side: str,
        size: float,
        price: float,
        max_attempts: int = 3,
    ) -> Order:
        """Create a new order.

        Args:
            signal_id: ID of originating signal.
            market_id: Market to trade.
            side: 'BUY' or 'SELL'.
            size: Trade size in dollars.
            price: Limit price.
            max_attempts: Maximum retry attempts.

        Returns:
            New Order instance.
        """
        order = Order(
            id=str(uuid.uuid4()),
            signal_id=signal_id,
            market_id=market_id,
            side=side,
            requested_size=size,
            requested_price=price,
            max_attempts=max_attempts,
        )
        await self.save_order(order)
        return order

    async def save_order(self, order: Order) -> None:
        """Persist order to cache."""
        key = f"order:{order.id}"
        await self.cache.set(key, order.to_dict())

    async def get_order(self, order_id: str) -> Order | None:
        """Load order from cache."""
        key = f"order:{order_id}"
        data = await self.cache.get(key)
        if not data:
            return None
        return self._order_from_dict(data)

    def _order_from_dict(self, data: dict[str, Any]) -> Order:
        """Reconstruct order from dictionary."""
        order = Order(
            signal_id=data["signal_id"],
            market_id=data["market_id"],
            side=data["side"],
            requested_size=data["requested_size"],
            requested_price=data["requested_price"],
            max_attempts=data.get("max_attempts", 3),
        )
        order.id = data.get("id")
        order.external_id = data.get("external_id")
        order.status = OrderStatus(data.get("status", "pending"))
        order.filled_size = data.get("filled_size", 0.0)
        order.filled_price = data.get("filled_price")
        order.attempts = data.get("attempts", 0)
        order.failure_reason = data.get("failure_reason")
        return order

    async def execute_with_retry(
        self,
        order: Order,
        executor: ExecutorProtocol,
    ) -> Order:
        """Execute order with retry logic.

        Args:
            order: Order to execute.
            executor: Executor to use for submission.

        Returns:
            Updated order with final status.
        """
        delay = self.retry_delay

        while order.attempts < order.max_attempts:
            try:
                logger.info(
                    "Submitting order {} (attempt {}/{})",
                    order.id,
                    order.attempts + 1,
                    order.max_attempts,
                )

                result = await executor.submit_order(
                    market_id=order.market_id,
                    side=order.side,
                    size=order.remaining_size if order.filled_size > 0 else order.requested_size,
                    price=order.requested_price,
                )

                order.mark_submitted(external_id=result["order_id"])

                # Process result
                status = result.get("status", "")
                if status == "filled":
                    order.mark_filled(
                        filled_size=result["filled_size"],
                        filled_price=result["filled_price"],
                    )
                    logger.info("Order {} filled at {}", order.id, result["filled_price"])
                    break
                elif status == "partial":
                    order.mark_partial(
                        filled_size=result["filled_size"],
                        filled_price=result["filled_price"],
                    )
                    logger.info(
                        "Order {} partially filled: {}/{}",
                        order.id,
                        result["filled_size"],
                        order.requested_size,
                    )
                    break
                else:
                    order.mark_failed(reason=f"Unexpected status: {status}")

            except Exception as e:
                logger.warning("Order {} failed: {}", order.id, str(e))
                order.mark_failed(reason=str(e))

                if order.can_retry:
                    logger.info("Retrying order {} in {}s", order.id, delay)
                    await asyncio.sleep(delay)
                    delay *= self.backoff_multiplier
                    # Reset status to allow retry
                    order.status = OrderStatus.PENDING

        await self.save_order(order)
        return order
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/execution/test_manager.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add src/polymind/core/execution/manager.py tests/core/execution/test_manager.py
git commit -m "feat(execution): add OrderManager with retry logic"
```

---

### Task 1.4: Live Executor

**Files:**
- Create: `src/polymind/core/execution/live.py`
- Test: `tests/core/execution/test_live.py`

**Step 1: Write the failing test**

```python
"""Tests for live executor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from polymind.core.execution.live import LiveExecutor, LiveExecutorError


class TestLiveExecutor:
    """Tests for LiveExecutor."""

    def test_init_without_credentials_raises(self) -> None:
        """Test that init without credentials raises error."""
        with pytest.raises(LiveExecutorError, match="credentials"):
            LiveExecutor(api_key=None, api_secret=None)

    def test_init_with_credentials(self) -> None:
        """Test successful init with credentials."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )
        assert executor.is_configured

    @pytest.mark.asyncio
    async def test_submit_order_success(self) -> None:
        """Test successful order submission."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )

        # Mock the CLOB client
        mock_response = {
            "orderID": "order_123",
            "status": "MATCHED",
            "matchedAmount": "100",
            "averagePrice": "0.55",
        }

        with patch.object(executor, "_clob_client") as mock_client:
            mock_client.create_order = AsyncMock(return_value=mock_response)

            result = await executor.submit_order(
                market_id="market_abc",
                side="BUY",
                size=100.0,
                price=0.55,
            )

            assert result["order_id"] == "order_123"
            assert result["status"] == "filled"
            assert result["filled_size"] == 100.0

    @pytest.mark.asyncio
    async def test_submit_order_partial_fill(self) -> None:
        """Test partial fill handling."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )

        mock_response = {
            "orderID": "order_123",
            "status": "OPEN",
            "matchedAmount": "60",
            "averagePrice": "0.54",
        }

        with patch.object(executor, "_clob_client") as mock_client:
            mock_client.create_order = AsyncMock(return_value=mock_response)

            result = await executor.submit_order(
                market_id="market_abc",
                side="BUY",
                size=100.0,
                price=0.55,
            )

            assert result["status"] == "partial"
            assert result["filled_size"] == 60.0

    @pytest.mark.asyncio
    async def test_cancel_order(self) -> None:
        """Test order cancellation."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )

        with patch.object(executor, "_clob_client") as mock_client:
            mock_client.cancel_order = AsyncMock(return_value={"success": True})

            result = await executor.cancel_order("order_123")
            assert result is True

    @pytest.mark.asyncio
    async def test_get_order_status(self) -> None:
        """Test getting order status."""
        executor = LiveExecutor(
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_pass",
        )

        mock_response = {
            "orderID": "order_123",
            "status": "MATCHED",
            "matchedAmount": "100",
            "averagePrice": "0.55",
        }

        with patch.object(executor, "_clob_client") as mock_client:
            mock_client.get_order = AsyncMock(return_value=mock_response)

            result = await executor.get_order_status("order_123")
            assert result["status"] == "filled"
            assert result["filled_size"] == 100.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/execution/test_live.py -v`
Expected: FAIL with "No module named 'polymind.core.execution.live'"

**Step 3: Write minimal implementation**

```python
"""Live executor for Polymarket CLOB API."""

from dataclasses import dataclass, field
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class LiveExecutorError(Exception):
    """Error in live execution."""

    pass


@dataclass
class LiveExecutor:
    """Executes real trades on Polymarket via CLOB API.

    This executor is dormant until wallet credentials are configured.
    It wraps the Polymarket CLOB client for order submission.

    Attributes:
        api_key: Polymarket API key.
        api_secret: Polymarket API secret.
        api_passphrase: Polymarket API passphrase.
    """

    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    _clob_client: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate credentials and initialize client."""
        if not self.api_key or not self.api_secret:
            raise LiveExecutorError(
                "Live executor requires API credentials. "
                "Set POLYMIND_POLYMARKET_API_KEY and POLYMIND_POLYMARKET_API_SECRET."
            )
        # Client will be lazily initialized when needed
        # For now, we don't import the actual CLOB client to keep deps minimal

    @property
    def is_configured(self) -> bool:
        """Check if executor is properly configured."""
        return bool(self.api_key and self.api_secret)

    async def submit_order(
        self,
        market_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict[str, Any]:
        """Submit order to Polymarket.

        Args:
            market_id: Market/token ID to trade.
            side: 'BUY' or 'SELL'.
            size: Trade size in dollars.
            price: Limit price.

        Returns:
            Order result with order_id, status, filled_size, filled_price.
        """
        logger.info(
            "Submitting live order: market={} side={} size={} price={}",
            market_id,
            side,
            size,
            price,
        )

        # Call CLOB API
        response = await self._clob_client.create_order(
            token_id=market_id,
            side=side.upper(),
            size=size,
            price=price,
        )

        return self._parse_order_response(response)

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get order status from Polymarket.

        Args:
            order_id: External order ID.

        Returns:
            Order status with filled_size and filled_price.
        """
        response = await self._clob_client.get_order(order_id)
        return self._parse_order_response(response)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order on Polymarket.

        Args:
            order_id: External order ID.

        Returns:
            True if cancelled successfully.
        """
        response = await self._clob_client.cancel_order(order_id)
        return response.get("success", False)

    def _parse_order_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse CLOB API response to standard format.

        Args:
            response: Raw CLOB API response.

        Returns:
            Normalized order result.
        """
        clob_status = response.get("status", "").upper()
        matched_amount = float(response.get("matchedAmount", 0))
        average_price = float(response.get("averagePrice", 0))

        # Map CLOB statuses to our statuses
        if clob_status == "MATCHED":
            status = "filled"
        elif clob_status in ("OPEN", "PENDING") and matched_amount > 0:
            status = "partial"
        elif clob_status in ("CANCELLED", "EXPIRED"):
            status = "cancelled"
        elif clob_status in ("REJECTED", "FAILED"):
            status = "failed"
        else:
            status = "pending"

        return {
            "order_id": response.get("orderID", ""),
            "status": status,
            "filled_size": matched_amount,
            "filled_price": average_price if matched_amount > 0 else None,
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/execution/test_live.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/polymind/core/execution/live.py tests/core/execution/test_live.py
git commit -m "feat(execution): add LiveExecutor for Polymarket CLOB"
```

---

### Task 1.5: Safety Guards

**Files:**
- Create: `src/polymind/core/execution/safety.py`
- Test: `tests/core/execution/test_safety.py`

**Step 1: Write the failing test**

```python
"""Tests for execution safety guards."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.execution.safety import SafetyGuard, LiveModeBlockedError


class TestSafetyGuard:
    """Tests for SafetyGuard."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.get = AsyncMock()
        cache.set = AsyncMock()
        return cache

    @pytest.mark.asyncio
    async def test_check_live_mode_without_credentials(self, mock_cache: MagicMock) -> None:
        """Test live mode blocked without credentials."""
        guard = SafetyGuard(cache=mock_cache)

        with pytest.raises(LiveModeBlockedError, match="credentials"):
            await guard.check_live_mode_allowed(
                has_credentials=False,
                live_confirmed=True,
            )

    @pytest.mark.asyncio
    async def test_check_live_mode_without_confirmation(self, mock_cache: MagicMock) -> None:
        """Test live mode blocked without confirmation."""
        guard = SafetyGuard(cache=mock_cache)

        with pytest.raises(LiveModeBlockedError, match="confirmation"):
            await guard.check_live_mode_allowed(
                has_credentials=True,
                live_confirmed=False,
            )

    @pytest.mark.asyncio
    async def test_check_live_mode_allowed(self, mock_cache: MagicMock) -> None:
        """Test live mode allowed with all requirements."""
        guard = SafetyGuard(cache=mock_cache)

        # Should not raise
        await guard.check_live_mode_allowed(
            has_credentials=True,
            live_confirmed=True,
        )

    @pytest.mark.asyncio
    async def test_emergency_stop_activates(self, mock_cache: MagicMock) -> None:
        """Test emergency stop activation."""
        guard = SafetyGuard(cache=mock_cache)

        await guard.activate_emergency_stop(reason="Manual trigger")

        mock_cache.set.assert_called()
        assert guard.is_stopped

    @pytest.mark.asyncio
    async def test_emergency_stop_blocks_execution(self, mock_cache: MagicMock) -> None:
        """Test that emergency stop blocks execution."""
        guard = SafetyGuard(cache=mock_cache)
        await guard.activate_emergency_stop(reason="Test")

        with pytest.raises(LiveModeBlockedError, match="emergency"):
            await guard.check_execution_allowed()

    @pytest.mark.asyncio
    async def test_reset_emergency_stop(self, mock_cache: MagicMock) -> None:
        """Test resetting emergency stop."""
        guard = SafetyGuard(cache=mock_cache)
        await guard.activate_emergency_stop(reason="Test")

        assert guard.is_stopped

        await guard.reset_emergency_stop()

        assert not guard.is_stopped

    @pytest.mark.asyncio
    async def test_first_live_trade_warning(self, mock_cache: MagicMock) -> None:
        """Test first live trade warning check."""
        guard = SafetyGuard(cache=mock_cache)
        mock_cache.get.return_value = None  # No previous live trades

        needs_warning = await guard.check_first_live_trade()
        assert needs_warning is True

        # Simulate acknowledgment
        await guard.acknowledge_first_live_trade()
        mock_cache.get.return_value = True

        needs_warning = await guard.check_first_live_trade()
        assert needs_warning is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/execution/test_safety.py -v`
Expected: FAIL with "No module named 'polymind.core.execution.safety'"

**Step 3: Write minimal implementation**

```python
"""Safety guards for trade execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class LiveModeBlockedError(Exception):
    """Raised when live mode execution is blocked."""

    pass


@dataclass
class SafetyGuard:
    """Guards against unsafe execution conditions.

    Provides multiple layers of safety:
    - Credential verification
    - Live mode confirmation
    - Emergency stop
    - First trade warning

    Attributes:
        cache: Cache for persisting safety state.
    """

    cache: Any
    _stopped: bool = field(default=False, repr=False)
    _stop_reason: str | None = field(default=None, repr=False)
    _stop_time: datetime | None = field(default=None, repr=False)

    @property
    def is_stopped(self) -> bool:
        """Check if emergency stop is active."""
        return self._stopped

    async def check_live_mode_allowed(
        self,
        has_credentials: bool,
        live_confirmed: bool,
    ) -> None:
        """Verify all requirements for live mode.

        Args:
            has_credentials: Whether API credentials are configured.
            live_confirmed: Whether user has confirmed live mode.

        Raises:
            LiveModeBlockedError: If any requirement not met.
        """
        if not has_credentials:
            raise LiveModeBlockedError(
                "Live mode requires API credentials. "
                "Configure POLYMIND_POLYMARKET_API_KEY and POLYMIND_POLYMARKET_API_SECRET."
            )

        if not live_confirmed:
            raise LiveModeBlockedError(
                "Live mode requires explicit confirmation. "
                "Set live_mode_confirmed=true in settings."
            )

        await self.check_execution_allowed()

    async def check_execution_allowed(self) -> None:
        """Check if execution is currently allowed.

        Raises:
            LiveModeBlockedError: If emergency stop is active.
        """
        if self._stopped:
            raise LiveModeBlockedError(
                f"Execution blocked by emergency stop: {self._stop_reason}"
            )

    async def activate_emergency_stop(self, reason: str) -> None:
        """Activate emergency stop.

        Args:
            reason: Reason for the stop.
        """
        self._stopped = True
        self._stop_reason = reason
        self._stop_time = datetime.now(timezone.utc)

        logger.warning("EMERGENCY STOP ACTIVATED: {}", reason)

        await self.cache.set(
            "emergency_stop",
            {
                "active": True,
                "reason": reason,
                "time": self._stop_time.isoformat(),
            },
        )

    async def reset_emergency_stop(self) -> None:
        """Reset emergency stop."""
        self._stopped = False
        self._stop_reason = None
        self._stop_time = None

        logger.info("Emergency stop reset")

        await self.cache.set("emergency_stop", {"active": False})

    async def check_first_live_trade(self) -> bool:
        """Check if this is the first live trade.

        Returns:
            True if first trade warning should be shown.
        """
        acknowledged = await self.cache.get("first_live_trade_acknowledged")
        return not acknowledged

    async def acknowledge_first_live_trade(self) -> None:
        """Acknowledge first live trade warning."""
        await self.cache.set("first_live_trade_acknowledged", True)
        logger.info("First live trade warning acknowledged")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/execution/test_safety.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add src/polymind/core/execution/safety.py tests/core/execution/test_safety.py
git commit -m "feat(execution): add SafetyGuard with emergency stop"
```

---

### Task 1.6: Integrate Execution Layer into Orchestrator

**Files:**
- Modify: `src/polymind/core/brain/orchestrator.py`
- Modify: `tests/core/brain/test_orchestrator.py`

**Step 1: Read existing orchestrator**

Read `src/polymind/core/brain/orchestrator.py` to understand current structure.

**Step 2: Add imports and update orchestrator**

Add slippage guard and order manager integration. The orchestrator should:
- Check slippage before executing
- Use OrderManager for order lifecycle
- Respect safety guards

**Step 3: Update tests**

Add tests for slippage rejection and order manager integration.

**Step 4: Run all tests**

Run: `pytest tests/core/brain/test_orchestrator.py tests/core/execution/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/polymind/core/brain/orchestrator.py tests/core/brain/test_orchestrator.py
git commit -m "feat(brain): integrate slippage guard and order manager"
```

---

## Phase 2: Wallet Intelligence

### Task 2.1: Wallet Metrics Model

**Files:**
- Modify: `src/polymind/storage/models.py`
- Create migration for `wallet_metrics` table
- Test: `tests/storage/test_wallet_metrics.py`

**Step 1: Write the failing test**

```python
"""Tests for wallet metrics storage."""

import pytest
from datetime import datetime, timezone

from polymind.storage.models import WalletMetrics


class TestWalletMetrics:
    """Tests for WalletMetrics model."""

    def test_create_wallet_metrics(self) -> None:
        """Test creating wallet metrics."""
        metrics = WalletMetrics(
            wallet_address="0x1234567890abcdef",
            win_rate=0.65,
            roi=0.12,
            timing_score=0.8,
            consistency=0.75,
            total_trades=50,
        )
        assert metrics.wallet_address == "0x1234567890abcdef"
        assert metrics.win_rate == 0.65

    def test_confidence_score_calculation(self) -> None:
        """Test confidence score is calculated correctly."""
        metrics = WalletMetrics(
            wallet_address="0x1234567890abcdef",
            win_rate=0.60,
            roi=0.10,
            timing_score=0.70,
            consistency=0.80,
        )
        # confidence = 0.6*0.3 + 0.1*0.3 + 0.7*0.2 + 0.8*0.2 = 0.18 + 0.03 + 0.14 + 0.16 = 0.51
        assert metrics.confidence_score == pytest.approx(0.51, rel=0.01)

    def test_confidence_score_with_custom_weights(self) -> None:
        """Test confidence score with custom weights."""
        metrics = WalletMetrics(
            wallet_address="0x1234567890abcdef",
            win_rate=0.60,
            roi=0.10,
            timing_score=0.70,
            consistency=0.80,
        )
        score = metrics.calculate_confidence(
            win_rate_weight=0.5,
            roi_weight=0.2,
            timing_weight=0.2,
            consistency_weight=0.1,
        )
        # 0.6*0.5 + 0.1*0.2 + 0.7*0.2 + 0.8*0.1 = 0.3 + 0.02 + 0.14 + 0.08 = 0.54
        assert score == pytest.approx(0.54, rel=0.01)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_wallet_metrics.py -v`
Expected: FAIL

**Step 3: Add WalletMetrics to models**

Add to `src/polymind/storage/models.py`:

```python
@dataclass
class WalletMetrics:
    """Performance metrics for a tracked wallet.

    Attributes:
        wallet_address: The wallet address.
        win_rate: Percentage of profitable trades (0.0-1.0).
        roi: Average return on investment per trade.
        timing_score: How early they enter positions (0.0-1.0).
        consistency: Consistency of performance (0.0-1.0).
        total_trades: Total number of trades analyzed.
        updated_at: Last update timestamp.
    """

    wallet_address: str
    win_rate: float = 0.0
    roi: float = 0.0
    timing_score: float = 0.0
    consistency: float = 0.0
    total_trades: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Default weights for confidence calculation
    _default_weights = {
        "win_rate": 0.3,
        "roi": 0.3,
        "timing": 0.2,
        "consistency": 0.2,
    }

    @property
    def confidence_score(self) -> float:
        """Calculate confidence score with default weights."""
        return self.calculate_confidence()

    def calculate_confidence(
        self,
        win_rate_weight: float = 0.3,
        roi_weight: float = 0.3,
        timing_weight: float = 0.2,
        consistency_weight: float = 0.2,
    ) -> float:
        """Calculate confidence score with custom weights.

        Args:
            win_rate_weight: Weight for win rate.
            roi_weight: Weight for ROI.
            timing_weight: Weight for timing score.
            consistency_weight: Weight for consistency.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        # Normalize ROI to 0-1 range (cap at 50% ROI = 1.0)
        normalized_roi = min(max(self.roi, 0), 0.5) / 0.5

        return (
            self.win_rate * win_rate_weight
            + normalized_roi * roi_weight
            + self.timing_score * timing_weight
            + self.consistency * consistency_weight
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/storage/test_wallet_metrics.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/polymind/storage/models.py tests/storage/test_wallet_metrics.py
git commit -m "feat(storage): add WalletMetrics model with confidence scoring"
```

---

### Task 2.2: Wallet Performance Tracker

**Files:**
- Create: `src/polymind/core/intelligence/wallet.py`
- Test: `tests/core/intelligence/test_wallet.py`

**Step 1: Write the failing test**

```python
"""Tests for wallet intelligence."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from polymind.core.intelligence.wallet import WalletTracker
from polymind.storage.models import WalletMetrics


class TestWalletTracker:
    """Tests for WalletTracker."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create mock database."""
        db = MagicMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock()
        db.fetch_all = AsyncMock()
        return db

    @pytest.fixture
    def mock_data_api(self) -> MagicMock:
        """Create mock data API."""
        api = MagicMock()
        api.get_wallet_trades = AsyncMock()
        return api

    @pytest.fixture
    def tracker(self, mock_db: MagicMock, mock_data_api: MagicMock) -> WalletTracker:
        """Create wallet tracker with mocks."""
        return WalletTracker(db=mock_db, data_api=mock_data_api)

    @pytest.mark.asyncio
    async def test_calculate_win_rate(self, tracker: WalletTracker) -> None:
        """Test win rate calculation."""
        trades = [
            {"profit": 10.0},
            {"profit": -5.0},
            {"profit": 15.0},
            {"profit": -3.0},
            {"profit": 8.0},
        ]
        win_rate = tracker.calculate_win_rate(trades)
        assert win_rate == 0.6  # 3 wins out of 5

    @pytest.mark.asyncio
    async def test_calculate_roi(self, tracker: WalletTracker) -> None:
        """Test ROI calculation."""
        trades = [
            {"size": 100, "profit": 10.0},
            {"size": 100, "profit": -5.0},
            {"size": 200, "profit": 20.0},
        ]
        roi = tracker.calculate_roi(trades)
        # Total profit: 25, Total invested: 400, ROI = 25/400 = 0.0625
        assert roi == pytest.approx(0.0625, rel=0.01)

    @pytest.mark.asyncio
    async def test_calculate_timing_score(self, tracker: WalletTracker) -> None:
        """Test timing score calculation."""
        trades = [
            {"entry_time": 100, "price_move_start": 110},  # 10s before move
            {"entry_time": 100, "price_move_start": 105},  # 5s before move
            {"entry_time": 100, "price_move_start": 120},  # 20s before move
        ]
        timing = tracker.calculate_timing_score(trades)
        # Good timing = earlier entries relative to price moves
        assert 0 <= timing <= 1

    @pytest.mark.asyncio
    async def test_analyze_wallet(
        self,
        tracker: WalletTracker,
        mock_data_api: MagicMock,
    ) -> None:
        """Test full wallet analysis."""
        mock_data_api.get_wallet_trades.return_value = [
            {"size": 100, "profit": 10.0, "entry_time": 100, "price_move_start": 110},
            {"size": 100, "profit": -5.0, "entry_time": 100, "price_move_start": 105},
            {"size": 100, "profit": 15.0, "entry_time": 100, "price_move_start": 120},
        ]

        metrics = await tracker.analyze_wallet("0x1234")

        assert isinstance(metrics, WalletMetrics)
        assert metrics.wallet_address == "0x1234"
        assert metrics.total_trades == 3
        assert 0 <= metrics.win_rate <= 1
        assert 0 <= metrics.confidence_score <= 1

    @pytest.mark.asyncio
    async def test_get_wallet_score(
        self,
        tracker: WalletTracker,
        mock_db: MagicMock,
    ) -> None:
        """Test getting cached wallet score."""
        mock_db.fetch_one.return_value = {
            "wallet_address": "0x1234",
            "win_rate": 0.65,
            "roi": 0.12,
            "timing_score": 0.8,
            "consistency": 0.75,
            "confidence_score": 0.68,
            "total_trades": 50,
        }

        score = await tracker.get_wallet_score("0x1234")
        assert score == pytest.approx(0.68, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_wallet_score_not_found(
        self,
        tracker: WalletTracker,
        mock_db: MagicMock,
    ) -> None:
        """Test getting score for unknown wallet."""
        mock_db.fetch_one.return_value = None

        score = await tracker.get_wallet_score("0xunknown")
        assert score == 0.5  # Default neutral score
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/intelligence/test_wallet.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
"""Wallet intelligence and performance tracking."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from polymind.storage.models import WalletMetrics
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WalletTracker:
    """Tracks and analyzes wallet trading performance.

    Attributes:
        db: Database connection.
        data_api: Polymarket Data API client.
    """

    db: Any
    data_api: Any

    def calculate_win_rate(self, trades: list[dict[str, Any]]) -> float:
        """Calculate win rate from trades.

        Args:
            trades: List of trades with 'profit' field.

        Returns:
            Win rate as float between 0 and 1.
        """
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.get("profit", 0) > 0)
        return wins / len(trades)

    def calculate_roi(self, trades: list[dict[str, Any]]) -> float:
        """Calculate average ROI from trades.

        Args:
            trades: List of trades with 'size' and 'profit' fields.

        Returns:
            ROI as float (e.g., 0.1 for 10%).
        """
        if not trades:
            return 0.0
        total_profit = sum(t.get("profit", 0) for t in trades)
        total_invested = sum(t.get("size", 0) for t in trades)
        if total_invested == 0:
            return 0.0
        return total_profit / total_invested

    def calculate_timing_score(self, trades: list[dict[str, Any]]) -> float:
        """Calculate timing efficiency score.

        Measures how early the wallet enters positions before price moves.

        Args:
            trades: List of trades with 'entry_time' and 'price_move_start'.

        Returns:
            Timing score between 0 and 1.
        """
        if not trades:
            return 0.0

        timing_deltas = []
        for trade in trades:
            entry = trade.get("entry_time", 0)
            move_start = trade.get("price_move_start", 0)
            if entry and move_start and move_start > entry:
                # Earlier entry = higher score
                delta = move_start - entry
                timing_deltas.append(delta)

        if not timing_deltas:
            return 0.5  # Neutral score

        # Normalize: higher delta = better timing
        # Cap at 60 seconds = perfect timing
        avg_delta = sum(timing_deltas) / len(timing_deltas)
        return min(avg_delta / 60, 1.0)

    def calculate_consistency(self, trades: list[dict[str, Any]]) -> float:
        """Calculate consistency of returns.

        Lower variance in returns = higher consistency.

        Args:
            trades: List of trades with 'profit' field.

        Returns:
            Consistency score between 0 and 1.
        """
        if len(trades) < 2:
            return 0.5

        profits = [t.get("profit", 0) for t in trades]
        avg = sum(profits) / len(profits)
        variance = sum((p - avg) ** 2 for p in profits) / len(profits)
        std_dev = variance ** 0.5

        # Lower std_dev = higher consistency
        # Normalize: std_dev of 0 = 1.0, std_dev of 100 = 0.0
        return max(0, 1 - (std_dev / 100))

    async def analyze_wallet(self, wallet_address: str) -> WalletMetrics:
        """Perform full analysis of wallet performance.

        Args:
            wallet_address: Wallet address to analyze.

        Returns:
            WalletMetrics with calculated scores.
        """
        logger.info("Analyzing wallet: {}", wallet_address[:10])

        # Fetch historical trades
        trades = await self.data_api.get_wallet_trades(wallet_address)

        metrics = WalletMetrics(
            wallet_address=wallet_address,
            win_rate=self.calculate_win_rate(trades),
            roi=self.calculate_roi(trades),
            timing_score=self.calculate_timing_score(trades),
            consistency=self.calculate_consistency(trades),
            total_trades=len(trades),
            updated_at=datetime.now(timezone.utc),
        )

        # Save to database
        await self._save_metrics(metrics)

        logger.info(
            "Wallet {} analyzed: confidence={:.2f}, trades={}",
            wallet_address[:10],
            metrics.confidence_score,
            metrics.total_trades,
        )

        return metrics

    async def _save_metrics(self, metrics: WalletMetrics) -> None:
        """Save metrics to database."""
        await self.db.execute(
            """
            INSERT INTO wallet_metrics
                (wallet_address, win_rate, roi, timing_score, consistency,
                 confidence_score, total_trades, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (wallet_address) DO UPDATE SET
                win_rate = $2, roi = $3, timing_score = $4, consistency = $5,
                confidence_score = $6, total_trades = $7, updated_at = $8
            """,
            metrics.wallet_address,
            metrics.win_rate,
            metrics.roi,
            metrics.timing_score,
            metrics.consistency,
            metrics.confidence_score,
            metrics.total_trades,
            metrics.updated_at,
        )

    async def get_wallet_score(self, wallet_address: str) -> float:
        """Get cached confidence score for wallet.

        Args:
            wallet_address: Wallet address.

        Returns:
            Confidence score, or 0.5 if not found.
        """
        row = await self.db.fetch_one(
            "SELECT confidence_score FROM wallet_metrics WHERE wallet_address = $1",
            wallet_address,
        )
        if row:
            return row["confidence_score"]
        return 0.5  # Neutral default
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/intelligence/test_wallet.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/polymind/core/intelligence/wallet.py tests/core/intelligence/test_wallet.py
git commit -m "feat(intelligence): add WalletTracker for performance analysis"
```

---

### Task 2.3: Per-Wallet Controls

**Files:**
- Modify: `src/polymind/storage/models.py` - add fields to Wallet
- Modify: `src/polymind/interfaces/api/routes/wallets.py` - add control endpoints
- Test: `tests/interfaces/api/test_wallet_controls.py`

**Step 1: Write the failing test**

```python
"""Tests for per-wallet control API."""

import pytest
from httpx import AsyncClient


class TestWalletControlsAPI:
    """Tests for wallet control endpoints."""

    @pytest.mark.asyncio
    async def test_update_wallet_controls(self, client: AsyncClient) -> None:
        """Test updating wallet control settings."""
        # First add a wallet
        await client.post("/wallets", json={"address": "0x1234"})

        # Update controls
        response = await client.patch(
            "/wallets/0x1234/controls",
            json={
                "enabled": True,
                "scale_factor": 0.5,
                "max_trade_size": 100.0,
                "min_confidence": 0.6,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["scale_factor"] == 0.5
        assert data["max_trade_size"] == 100.0
        assert data["min_confidence"] == 0.6

    @pytest.mark.asyncio
    async def test_get_wallet_controls(self, client: AsyncClient) -> None:
        """Test getting wallet control settings."""
        await client.post("/wallets", json={"address": "0x1234"})

        response = await client.get("/wallets/0x1234/controls")

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "scale_factor" in data

    @pytest.mark.asyncio
    async def test_disable_wallet(self, client: AsyncClient) -> None:
        """Test disabling a wallet."""
        await client.post("/wallets", json={"address": "0x1234"})

        response = await client.patch(
            "/wallets/0x1234/controls",
            json={"enabled": False},
        )

        assert response.status_code == 200
        assert response.json()["enabled"] is False

    @pytest.mark.asyncio
    async def test_wallet_controls_not_found(self, client: AsyncClient) -> None:
        """Test controls for non-existent wallet."""
        response = await client.get("/wallets/0xnotfound/controls")
        assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/interfaces/api/test_wallet_controls.py -v`
Expected: FAIL

**Step 3: Implement wallet controls**

Add to `src/polymind/interfaces/api/routes/wallets.py`:

```python
from pydantic import BaseModel

class WalletControlsUpdate(BaseModel):
    """Request model for updating wallet controls."""
    enabled: bool | None = None
    scale_factor: float | None = None
    max_trade_size: float | None = None
    min_confidence: float | None = None


@router.get("/wallets/{address}/controls")
async def get_wallet_controls(
    address: str,
    db: Database = Depends(get_db),
) -> dict:
    """Get wallet control settings."""
    wallet = await db.fetch_one(
        "SELECT * FROM wallets WHERE address = $1", address
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "address": wallet["address"],
        "enabled": wallet.get("enabled", True),
        "scale_factor": wallet.get("scale_factor", 1.0),
        "max_trade_size": wallet.get("max_trade_size"),
        "min_confidence": wallet.get("min_confidence", 0.0),
    }


@router.patch("/wallets/{address}/controls")
async def update_wallet_controls(
    address: str,
    controls: WalletControlsUpdate,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
) -> dict:
    """Update wallet control settings."""
    wallet = await db.fetch_one(
        "SELECT * FROM wallets WHERE address = $1", address
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    updates = {k: v for k, v in controls.model_dump().items() if v is not None}
    if updates:
        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
        await db.execute(
            f"UPDATE wallets SET {set_clause} WHERE address = $1",
            address,
            *updates.values(),
        )

    result = await get_wallet_controls(address, db)
    background_tasks.add_task(manager.broadcast, "wallet", {"action": "updated", **result})
    return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/interfaces/api/test_wallet_controls.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/polymind/storage/models.py src/polymind/interfaces/api/routes/wallets.py tests/interfaces/api/test_wallet_controls.py
git commit -m "feat(api): add per-wallet control endpoints"
```

---

### Task 2.4: Auto-Disable Logic

**Files:**
- Create: `src/polymind/core/intelligence/auto_disable.py`
- Test: `tests/core/intelligence/test_auto_disable.py`

**Step 1: Write the failing test**

```python
"""Tests for auto-disable logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.intelligence.auto_disable import AutoDisableChecker


class TestAutoDisableChecker:
    """Tests for AutoDisableChecker."""

    @pytest.fixture
    def checker(self) -> AutoDisableChecker:
        """Create checker with default config."""
        return AutoDisableChecker(
            min_confidence=0.3,
            max_drawdown=-0.20,
            inactive_days=30,
        )

    @pytest.mark.asyncio
    async def test_should_disable_low_confidence(self, checker: AutoDisableChecker) -> None:
        """Test disable on low confidence."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.2,
            drawdown_7d=-0.10,
            last_trade_days_ago=5,
        )
        assert result.should_disable is True
        assert "confidence" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_should_disable_high_drawdown(self, checker: AutoDisableChecker) -> None:
        """Test disable on high drawdown."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.5,
            drawdown_7d=-0.25,
            last_trade_days_ago=5,
        )
        assert result.should_disable is True
        assert "drawdown" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_should_disable_inactive(self, checker: AutoDisableChecker) -> None:
        """Test disable on inactivity."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.5,
            drawdown_7d=-0.05,
            last_trade_days_ago=45,
        )
        assert result.should_disable is True
        assert "inactive" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_should_not_disable_healthy(self, checker: AutoDisableChecker) -> None:
        """Test no disable for healthy wallet."""
        result = await checker.check_wallet(
            wallet_address="0x1234",
            confidence_score=0.7,
            drawdown_7d=-0.05,
            last_trade_days_ago=5,
        )
        assert result.should_disable is False
        assert result.reason is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/intelligence/test_auto_disable.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
"""Auto-disable logic for underperforming wallets."""

from dataclasses import dataclass
from typing import Any

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DisableCheckResult:
    """Result of disable check."""

    should_disable: bool
    reason: str | None = None


@dataclass
class AutoDisableChecker:
    """Checks if wallets should be auto-disabled.

    Attributes:
        min_confidence: Minimum confidence score threshold.
        max_drawdown: Maximum allowed drawdown (negative float, e.g., -0.20).
        inactive_days: Days of inactivity before disable.
    """

    min_confidence: float = 0.3
    max_drawdown: float = -0.20
    inactive_days: int = 30

    async def check_wallet(
        self,
        wallet_address: str,
        confidence_score: float,
        drawdown_7d: float,
        last_trade_days_ago: int,
    ) -> DisableCheckResult:
        """Check if wallet should be disabled.

        Args:
            wallet_address: Wallet address.
            confidence_score: Current confidence score (0-1).
            drawdown_7d: 7-day drawdown as negative float.
            last_trade_days_ago: Days since last trade.

        Returns:
            DisableCheckResult indicating if disable is needed.
        """
        # Check confidence
        if confidence_score < self.min_confidence:
            logger.warning(
                "Wallet {} below confidence threshold: {:.2f} < {:.2f}",
                wallet_address[:10],
                confidence_score,
                self.min_confidence,
            )
            return DisableCheckResult(
                should_disable=True,
                reason=f"Confidence score {confidence_score:.2f} below threshold {self.min_confidence}",
            )

        # Check drawdown
        if drawdown_7d < self.max_drawdown:
            logger.warning(
                "Wallet {} exceeds drawdown limit: {:.1%} < {:.1%}",
                wallet_address[:10],
                drawdown_7d,
                self.max_drawdown,
            )
            return DisableCheckResult(
                should_disable=True,
                reason=f"Drawdown {drawdown_7d:.1%} exceeds limit {self.max_drawdown:.1%}",
            )

        # Check inactivity
        if last_trade_days_ago > self.inactive_days:
            logger.warning(
                "Wallet {} inactive for {} days (limit: {})",
                wallet_address[:10],
                last_trade_days_ago,
                self.inactive_days,
            )
            return DisableCheckResult(
                should_disable=True,
                reason=f"Inactive for {last_trade_days_ago} days",
            )

        return DisableCheckResult(should_disable=False)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/intelligence/test_auto_disable.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/polymind/core/intelligence/auto_disable.py tests/core/intelligence/test_auto_disable.py
git commit -m "feat(intelligence): add auto-disable checker for wallets"
```

---

## Phase 3: Market Intelligence

### Task 3.1: Market Analyzer

**Files:**
- Create: `src/polymind/core/intelligence/market.py`
- Test: `tests/core/intelligence/test_market.py`

[Similar structure: test first, implement, verify, commit]

Key methods:
- `calculate_liquidity_score(orderbook)`
- `calculate_spread_score(orderbook)`
- `calculate_volatility_score(price_history)`
- `calculate_time_decay_score(resolution_time)`
- `get_quality_score(market_id)` - combines all scores

---

### Task 3.2: Market Filters (Allow/Deny Lists)

**Files:**
- Create: `src/polymind/core/intelligence/filters.py`
- Test: `tests/core/intelligence/test_filters.py`

Key methods:
- `is_market_allowed(market_id, category, title)`
- `add_filter(filter_type, value, action)`
- `remove_filter(filter_id)`
- `get_filters()`

---

### Task 3.3: Market Filters API

**Files:**
- Create: `src/polymind/interfaces/api/routes/filters.py`
- Test: `tests/interfaces/api/test_filters.py`

Endpoints:
- `GET /filters` - list all filters
- `POST /filters` - add filter
- `DELETE /filters/{id}` - remove filter

---

## Phase 4: External Integrations

### Task 4.1: Kalshi Client

**Files:**
- Create: `src/polymind/data/kalshi/__init__.py`
- Create: `src/polymind/data/kalshi/client.py`
- Test: `tests/data/kalshi/test_client.py`

Key methods:
- `get_markets()`
- `get_market(market_id)`
- `get_orderbook(market_id)`
- `search_markets(query)`

---

### Task 4.2: Binance WebSocket Feed

**Files:**
- Create: `src/polymind/data/binance/__init__.py`
- Create: `src/polymind/data/binance/feed.py`
- Test: `tests/data/binance/test_feed.py`

Key methods:
- `connect(symbols)`
- `disconnect()`
- `get_price(symbol)`
- `subscribe(symbol, callback)`

---

### Task 4.3: Market Normalizer

**Files:**
- Create: `src/polymind/core/intelligence/normalizer.py`
- Test: `tests/core/intelligence/test_normalizer.py`

Key methods:
- `normalize_polymarket_odds(price)`
- `normalize_kalshi_odds(yes_price, no_price)`
- `find_equivalent_markets(polymarket_id)`
- `get_cross_platform_prices(market_mapping)`

---

### Task 4.4: Arbitrage Detector

**Files:**
- Create: `src/polymind/core/intelligence/arbitrage.py`
- Test: `tests/core/intelligence/test_arbitrage.py`

Key methods:
- `detect_opportunities()`
- `calculate_spread(poly_price, kalshi_price)`
- `estimate_profit(spread, size, fees)`
- `create_arbitrage_signal(opportunity)`

---

### Task 4.5: Price Lag Detector

**Files:**
- Create: `src/polymind/core/intelligence/pricelag.py`
- Test: `tests/core/intelligence/test_pricelag.py`

Key methods:
- `check_crypto_markets()`
- `detect_lag(binance_price, poly_market)`
- `create_lag_signal(opportunity)`

---

## Database Migrations

### Task DB.1: Create wallet_metrics Table

```sql
CREATE TABLE wallet_metrics (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL UNIQUE,
    win_rate FLOAT DEFAULT 0,
    roi FLOAT DEFAULT 0,
    timing_score FLOAT DEFAULT 0,
    consistency FLOAT DEFAULT 0,
    confidence_score FLOAT DEFAULT 0,
    total_trades INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_wallet_metrics_address ON wallet_metrics(wallet_address);
CREATE INDEX idx_wallet_metrics_confidence ON wallet_metrics(confidence_score);
```

### Task DB.2: Add Control Columns to Wallets

```sql
ALTER TABLE wallets ADD COLUMN enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE wallets ADD COLUMN scale_factor FLOAT DEFAULT 1.0;
ALTER TABLE wallets ADD COLUMN max_trade_size FLOAT;
ALTER TABLE wallets ADD COLUMN min_confidence FLOAT DEFAULT 0.0;
```

### Task DB.3: Create market_filters Table

```sql
CREATE TABLE market_filters (
    id SERIAL PRIMARY KEY,
    filter_type VARCHAR(20) NOT NULL,
    value VARCHAR(255) NOT NULL,
    action VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Task DB.4: Create market_mappings Table

```sql
CREATE TABLE market_mappings (
    id SERIAL PRIMARY KEY,
    polymarket_id VARCHAR(255),
    kalshi_id VARCHAR(255),
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Task DB.5: Create orders Table

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255),
    signal_id INT,
    status VARCHAR(20) DEFAULT 'pending',
    requested_size FLOAT,
    filled_size FLOAT DEFAULT 0,
    requested_price FLOAT,
    filled_price FLOAT,
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_signal ON orders(signal_id);
```

---

## Dashboard Updates

### Task UI.1: Wallet Detail Page

Add `/wallets/[address]` page showing:
- Performance charts (win rate, ROI over time)
- Confidence score history
- Per-wallet control settings
- Recent trades from this wallet

### Task UI.2: Market Filters Page

Add `/settings/filters` page with:
- List of current filters
- Add new filter form
- Delete filter button
- Filter type selector (category, keyword, market ID)

### Task UI.3: Arbitrage View

Add `/arbitrage` page showing:
- Live cross-platform opportunities
- Historical arbitrage trades
- Profit/loss summary

### Task UI.4: Order History

Add `/orders` page with:
- Full order lifecycle visibility
- Status filters (filled, partial, failed)
- Retry information

---

## Final Integration

### Task INT.1: Wire Wallet Intelligence into Decision Brain

Update `DecisionContextBuilder` to include:
- Wallet confidence score
- Per-wallet controls (scale factor, max size)
- Auto-disable check before processing

### Task INT.2: Wire Market Intelligence into Decision Brain

Update `DecisionContextBuilder` to include:
- Market quality score
- Filter check (allow/deny)
- Liquidity assessment

### Task INT.3: Wire External Data into Decision Brain

Add new signal types:
- `ARBITRAGE` - from arbitrage detector
- `PRICE_LAG` - from price lag detector

Update AI prompt to handle these signal types.

### Task INT.4: Full End-to-End Test

Create integration test that:
1. Adds a wallet with controls
2. Simulates a trade signal
3. Verifies wallet score is checked
4. Verifies market quality is checked
5. Verifies order lifecycle works
6. Verifies dashboard shows updates

---

## Success Criteria Checklist

- [ ] Can switch between paper/live mode without restart
- [ ] Wallet confidence scores visible in dashboard
- [ ] Per-wallet controls work (enable/disable, scaling)
- [ ] Market quality gates working (rejecting low-quality markets)
- [ ] Market filters work (allow/deny lists)
- [ ] Kalshi markets visible and normalized
- [ ] Binance prices streaming in real-time
- [ ] Arbitrage opportunities detected and logged
- [ ] Price lag opportunities detected
- [ ] Order lifecycle tracked with retries
- [ ] Slippage protection active
- [ ] Emergency stop works
- [ ] All existing tests still pass
- [ ] New features have >80% test coverage
