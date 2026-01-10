# Kalshi Arbitrage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Use Kalshi prices as a signal source to find and trade mispriced markets on Polymarket.

**Architecture:** ArbitrageMonitorService polls Kalshi prices for mapped markets, compares to Polymarket, and generates TradeSignals when spread exceeds threshold. Signals flow through existing AI Decision → Risk Manager → Executor pipeline.

**Tech Stack:** Python 3.14, asyncio, httpx, FastAPI, SQLAlchemy

---

### Task 1: Add ArbitrageSettings to Config

**Files:**
- Modify: `src/polymind/config/settings.py`
- Test: `tests/config/test_settings.py`

**Step 1: Add ArbitrageSettings dataclass**

Add to `src/polymind/config/settings.py` after other settings classes:

```python
@dataclass
class ArbitrageSettings:
    """Arbitrage monitoring settings."""
    enabled: bool = False
    min_spread: float = 0.03  # 3% minimum spread to trigger
    poll_interval: float = 30.0  # seconds between scans
    max_signal_size: float = 100.0  # max USD per arbitrage signal
```

**Step 2: Add to Settings class**

Add field to the main `Settings` class:

```python
arbitrage: ArbitrageSettings = field(default_factory=ArbitrageSettings)
```

**Step 3: Add env var loading in load_settings()**

Add to `load_settings()` function:

```python
arbitrage=ArbitrageSettings(
    enabled=os.getenv("POLYMIND_ARBITRAGE_ENABLED", "false").lower() == "true",
    min_spread=float(os.getenv("POLYMIND_ARBITRAGE_MIN_SPREAD", "0.03")),
    poll_interval=float(os.getenv("POLYMIND_ARBITRAGE_POLL_INTERVAL", "30.0")),
    max_signal_size=float(os.getenv("POLYMIND_ARBITRAGE_MAX_SIGNAL_SIZE", "100.0")),
),
```

**Step 4: Run existing tests**

Run: `pytest tests/config/test_settings.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/polymind/config/settings.py
git commit -m "feat: add ArbitrageSettings to config"
```

---

### Task 2: Create ArbitrageMonitorService

**Files:**
- Create: `src/polymind/services/arbitrage.py`
- Create: `tests/services/test_arbitrage.py`

**Step 1: Write the test file**

Create `tests/services/test_arbitrage.py`:

```python
"""Tests for ArbitrageMonitorService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.data.models import SignalSource, TradeSignal
from polymind.services.arbitrage import ArbitrageMonitorService


class MockKalshiMarket:
    """Mock Kalshi market."""
    def __init__(self, ticker: str, yes_price: float, no_price: float):
        self.ticker = ticker
        self.title = f"Test Market {ticker}"
        self.yes_price = yes_price
        self.no_price = no_price
        self.volume = 10000
        self.category = "test"


class MockMapping:
    """Mock market mapping."""
    def __init__(self, poly_id: str, kalshi_id: str):
        self.id = 1
        self.polymarket_id = poly_id
        self.kalshi_id = kalshi_id
        self.description = "Test mapping"
        self.active = True


@pytest.fixture
def mock_kalshi_client():
    """Create mock Kalshi client."""
    client = AsyncMock()
    client.get_market = AsyncMock(return_value=MockKalshiMarket(
        ticker="TEST-TICKER",
        yes_price=0.65,
        no_price=0.35,
    ))
    return client


@pytest.fixture
def mock_polymarket_client():
    """Create mock Polymarket client."""
    client = AsyncMock()
    client.get_market = AsyncMock(return_value={
        "price": 0.58,
        "volume": 50000,
    })
    return client


@pytest.fixture
def mock_db():
    """Create mock database."""
    db = AsyncMock()
    db.get_all_market_mappings = AsyncMock(return_value=[
        MockMapping("poly-123", "KALSHI-123"),
    ])
    return db


@pytest.fixture
def service(mock_kalshi_client, mock_polymarket_client, mock_db):
    """Create ArbitrageMonitorService."""
    return ArbitrageMonitorService(
        kalshi_client=mock_kalshi_client,
        polymarket_client=mock_polymarket_client,
        db=mock_db,
        min_spread=0.03,
        on_signal=AsyncMock(),
    )


class TestArbitrageMonitorService:
    """Tests for ArbitrageMonitorService."""

    @pytest.mark.asyncio
    async def test_scan_finds_opportunity(self, service, mock_db):
        """Scan detects opportunity when spread exceeds threshold."""
        opportunities = await service.scan()

        assert len(opportunities) == 1
        opp = opportunities[0]
        assert opp["polymarket_id"] == "poly-123"
        assert opp["kalshi_id"] == "KALSHI-123"
        assert opp["spread"] == pytest.approx(0.07, abs=0.01)
        assert opp["direction"] == "BUY_YES"

    @pytest.mark.asyncio
    async def test_scan_ignores_small_spread(self, service, mock_kalshi_client):
        """Scan ignores opportunities below threshold."""
        mock_kalshi_client.get_market = AsyncMock(return_value=MockKalshiMarket(
            ticker="TEST",
            yes_price=0.59,  # Only 1% spread
            no_price=0.41,
        ))

        opportunities = await service.scan()

        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_scan_triggers_callback(self, service):
        """Scan calls on_signal callback for valid opportunities."""
        await service.scan()

        service._on_signal.assert_called_once()
        signal = service._on_signal.call_args[0][0]
        assert isinstance(signal, TradeSignal)
        assert signal.source == SignalSource.ARBITRAGE

    @pytest.mark.asyncio
    async def test_calculate_direction_buy_yes(self, service):
        """Direction is BUY_YES when Kalshi > Polymarket."""
        direction = service._calculate_direction(
            kalshi_price=0.70,
            poly_price=0.60,
        )
        assert direction == "BUY_YES"

    @pytest.mark.asyncio
    async def test_calculate_direction_buy_no(self, service):
        """Direction is BUY_NO when Kalshi < Polymarket."""
        direction = service._calculate_direction(
            kalshi_price=0.40,
            poly_price=0.50,
        )
        assert direction == "BUY_NO"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_arbitrage.py -v`
Expected: FAIL with "No module named 'polymind.services.arbitrage'"

**Step 3: Create the service implementation**

Create `src/polymind/services/arbitrage.py`:

```python
"""Arbitrage monitoring service."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine

from polymind.data.models import SignalSource, TradeSignal
from polymind.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ArbitrageMonitorService:
    """Monitors Kalshi prices to find arbitrage opportunities on Polymarket.

    Compares prices between Kalshi and Polymarket for mapped markets.
    When spread exceeds threshold, generates TradeSignal for Polymarket.

    Attributes:
        kalshi_client: Kalshi API client.
        polymarket_client: Polymarket Data API client.
        db: Database for market mappings.
        min_spread: Minimum spread to trigger (default 3%).
        max_signal_size: Maximum signal size in USD.
        poll_interval: Seconds between scans.
        on_signal: Callback for generated signals.
    """

    kalshi_client: Any
    polymarket_client: Any
    db: Any
    min_spread: float = 0.03
    max_signal_size: float = 100.0
    poll_interval: float = 30.0
    on_signal: Callable[[TradeSignal], Coroutine[Any, Any, None]] | None = None
    _running: bool = field(default=False, repr=False)
    _on_signal: Any = field(default=None, repr=False, init=False)

    def __post_init__(self):
        self._on_signal = self.on_signal

    async def start(self) -> None:
        """Start continuous monitoring."""
        self._running = True
        logger.info(
            "Starting arbitrage monitor (interval={}s, min_spread={:.1%})",
            self.poll_interval,
            self.min_spread,
        )

        while self._running:
            try:
                await self.scan()
            except Exception as e:
                logger.error("Arbitrage scan error: {}", str(e))

            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        logger.info("Arbitrage monitor stopped")

    async def scan(self) -> list[dict[str, Any]]:
        """Scan for arbitrage opportunities.

        Returns:
            List of opportunity dicts with spread, direction, prices.
        """
        opportunities = []

        # Get all active market mappings
        mappings = await self.db.get_all_market_mappings()
        active_mappings = [m for m in mappings if m.active]

        if not active_mappings:
            logger.debug("No active market mappings to scan")
            return opportunities

        for mapping in active_mappings:
            try:
                opp = await self._check_mapping(mapping)
                if opp:
                    opportunities.append(opp)

                    # Generate signal if callback provided
                    if self._on_signal:
                        signal = self._create_signal(opp, mapping)
                        await self._on_signal(signal)

            except Exception as e:
                logger.warning(
                    "Error checking mapping {}: {}",
                    mapping.polymarket_id,
                    str(e),
                )

        if opportunities:
            logger.info("Found {} arbitrage opportunities", len(opportunities))

        return opportunities

    async def _check_mapping(self, mapping: Any) -> dict[str, Any] | None:
        """Check a single mapping for arbitrage opportunity.

        Args:
            mapping: MarketMapping object.

        Returns:
            Opportunity dict or None if no opportunity.
        """
        # Fetch Kalshi price
        kalshi_market = await self.kalshi_client.get_market(mapping.kalshi_id)
        if not kalshi_market:
            return None

        # Normalize Kalshi price (yes_price is already 0-1)
        kalshi_price = kalshi_market.yes_price

        # Fetch Polymarket price
        poly_data = await self.polymarket_client.get_market(mapping.polymarket_id)
        if not poly_data:
            return None

        poly_price = poly_data.get("price", 0.5)

        # Calculate spread
        spread = kalshi_price - poly_price

        # Check if spread exceeds threshold
        if abs(spread) < self.min_spread:
            return None

        direction = self._calculate_direction(kalshi_price, poly_price)

        return {
            "polymarket_id": mapping.polymarket_id,
            "kalshi_id": mapping.kalshi_id,
            "description": mapping.description,
            "kalshi_price": kalshi_price,
            "poly_price": poly_price,
            "spread": spread,
            "direction": direction,
        }

    def _calculate_direction(self, kalshi_price: float, poly_price: float) -> str:
        """Calculate trade direction.

        Args:
            kalshi_price: Kalshi probability.
            poly_price: Polymarket probability.

        Returns:
            "BUY_YES" if Polymarket is underpriced, "BUY_NO" if overpriced.
        """
        if kalshi_price > poly_price:
            return "BUY_YES"
        else:
            return "BUY_NO"

    def _create_signal(self, opp: dict[str, Any], mapping: Any) -> TradeSignal:
        """Create TradeSignal from opportunity.

        Args:
            opp: Opportunity dict.
            mapping: MarketMapping object.

        Returns:
            TradeSignal for the opportunity.
        """
        # Size scales with spread magnitude
        spread_factor = min(abs(opp["spread"]) / 0.10, 1.0)  # Cap at 10% spread
        size = self.max_signal_size * spread_factor

        side = "YES" if opp["direction"] == "BUY_YES" else "NO"
        price = opp["poly_price"] if side == "YES" else (1 - opp["poly_price"])

        return TradeSignal(
            wallet="arbitrage_detector",
            market_id=opp["polymarket_id"],
            token_id=opp["polymarket_id"],  # Will need actual token_id
            side=side,
            size=size,
            price=price,
            source=SignalSource.ARBITRAGE,
            timestamp=datetime.now(),
        )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/services/test_arbitrage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/polymind/services/arbitrage.py tests/services/test_arbitrage.py
git commit -m "feat: add ArbitrageMonitorService"
```

---

### Task 3: Add ARBITRAGE to SignalSource Enum

**Files:**
- Modify: `src/polymind/data/models.py`

**Step 1: Check if ARBITRAGE exists in SignalSource**

Read `src/polymind/data/models.py` and check SignalSource enum.

**Step 2: Add ARBITRAGE if missing**

Add to SignalSource enum:

```python
class SignalSource(str, Enum):
    CLOB = "clob"
    CHAIN = "chain"
    ARBITRAGE = "arbitrage"
```

**Step 3: Run tests**

Run: `pytest tests/data/test_models.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/polymind/data/models.py
git commit -m "feat: add ARBITRAGE to SignalSource enum"
```

---

### Task 4: Wire ArbitrageMonitorService into BotRunner

**Files:**
- Modify: `src/polymind/runner.py`

**Step 1: Add import**

Add to imports in `runner.py`:

```python
from polymind.services.arbitrage import ArbitrageMonitorService
from polymind.data.kalshi.client import KalshiClient
```

**Step 2: Add instance variable in __init__**

Add to `BotRunner.__init__()`:

```python
self._arbitrage_monitor: ArbitrageMonitorService | None = None
self._kalshi_client: KalshiClient | None = None
```

**Step 3: Add setup method**

Add method to BotRunner:

```python
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

    return ArbitrageMonitorService(
        kalshi_client=self._kalshi_client,
        polymarket_client=self._data_api,
        db=self._db,
        min_spread=self._settings.arbitrage.min_spread,
        max_signal_size=self._settings.arbitrage.max_signal_size,
        poll_interval=self._settings.arbitrage.poll_interval,
        on_signal=self._on_trade_signal,
    )
```

**Step 4: Initialize in start()**

Add after wallet monitor initialization in `start()`:

```python
# Initialize arbitrage monitor (may be None if disabled)
self._arbitrage_monitor = self._setup_arbitrage_monitor()
if self._arbitrage_monitor:
    logger.info("Arbitrage monitor initialized")
```

**Step 5: Start monitor task in run()**

Add after wallet monitor task creation:

```python
if self._arbitrage_monitor:
    arbitrage_task = asyncio.create_task(self._arbitrage_monitor.start())
    logger.info("Arbitrage monitoring started")
```

**Step 6: Stop in stop()**

Add to `stop()` method:

```python
if self._arbitrage_monitor:
    await self._arbitrage_monitor.stop()
    logger.info("Arbitrage monitor stopped")

if self._kalshi_client:
    await self._kalshi_client.close()
    logger.info("Kalshi client closed")
```

**Step 7: Run existing tests**

Run: `pytest tests/test_runner.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add src/polymind/runner.py
git commit -m "feat: wire ArbitrageMonitorService into BotRunner"
```

---

### Task 5: Add Manual Scan API Endpoint

**Files:**
- Modify: `src/polymind/interfaces/api/routes/arbitrage.py`
- Modify: `src/polymind/interfaces/api/deps.py`

**Step 1: Add get_arbitrage_service dependency**

Add to `deps.py`:

```python
from polymind.services.arbitrage import ArbitrageMonitorService
from polymind.data.kalshi.client import KalshiClient
from polymind.data.polymarket.data_api import DataAPIClient

_arbitrage_service: ArbitrageMonitorService | None = None
_kalshi_client: KalshiClient | None = None
_data_api_client: DataAPIClient | None = None

async def get_arbitrage_service() -> ArbitrageMonitorService:
    """Get arbitrage service for manual scans."""
    global _arbitrage_service, _kalshi_client, _data_api_client

    if _arbitrage_service is None:
        if _kalshi_client is None:
            _kalshi_client = KalshiClient()
        if _data_api_client is None:
            _data_api_client = DataAPIClient()

        db = await get_db()
        settings = await get_settings()

        _arbitrage_service = ArbitrageMonitorService(
            kalshi_client=_kalshi_client,
            polymarket_client=_data_api_client,
            db=db,
            min_spread=settings.arbitrage.min_spread,
            max_signal_size=settings.arbitrage.max_signal_size,
        )

    return _arbitrage_service
```

**Step 2: Add scan endpoint to arbitrage.py**

Add to `src/polymind/interfaces/api/routes/arbitrage.py`:

```python
from polymind.interfaces.api.deps import get_arbitrage_service
from polymind.services.arbitrage import ArbitrageMonitorService


class ScanResponse(BaseModel):
    """Manual scan response."""
    opportunities: list[OpportunityResponse]
    scanned_at: str


@router.post("/scan", response_model=ScanResponse)
async def scan_opportunities(
    service: ArbitrageMonitorService = Depends(get_arbitrage_service),
) -> dict:
    """Trigger manual scan for arbitrage opportunities."""
    from datetime import datetime

    opportunities = await service.scan()

    return {
        "opportunities": [
            {
                "polymarket_id": opp["polymarket_id"],
                "kalshi_id": opp["kalshi_id"],
                "spread": opp["spread"],
                "direction": opp["direction"],
                "poly_price": opp["poly_price"],
                "kalshi_price": opp["kalshi_price"],
                "confidence": min(abs(opp["spread"]) / 0.10, 1.0),
            }
            for opp in opportunities
        ],
        "scanned_at": datetime.now().isoformat(),
    }
```

**Step 3: Update /opportunities endpoint**

Replace the placeholder in `list_opportunities`:

```python
@router.get("/opportunities", response_model=list[OpportunityResponse])
async def list_opportunities(
    service: ArbitrageMonitorService = Depends(get_arbitrage_service),
) -> list[dict]:
    """List current arbitrage opportunities."""
    opportunities = await service.scan()

    return [
        {
            "polymarket_id": opp["polymarket_id"],
            "kalshi_id": opp["kalshi_id"],
            "spread": opp["spread"],
            "direction": opp["direction"],
            "poly_price": opp["poly_price"],
            "kalshi_price": opp["kalshi_price"],
            "confidence": min(abs(opp["spread"]) / 0.10, 1.0),
        }
        for opp in opportunities
    ]
```

**Step 4: Run API tests**

Run: `pytest tests/interfaces/api/test_arbitrage.py -v` (create if needed)
Expected: PASS

**Step 5: Commit**

```bash
git add src/polymind/interfaces/api/routes/arbitrage.py src/polymind/interfaces/api/deps.py
git commit -m "feat: add manual scan API endpoint"
```

---

### Task 6: Update Dashboard Arbitrage Page

**Files:**
- Modify: `dashboard/src/app/arbitrage/page.tsx`
- Modify: `dashboard/src/lib/api.ts`

**Step 1: Add scan API method**

Add to `dashboard/src/lib/api.ts`:

```typescript
// Arbitrage
scanArbitrage: () => fetchAPI<{ opportunities: ArbitrageOpportunity[]; scanned_at: string }>('/arbitrage/scan', { method: 'POST' }),
```

**Step 2: Update arbitrage page with scan button and real data**

Update `dashboard/src/app/arbitrage/page.tsx` to:
- Fetch real opportunities from API
- Add "Scan Now" button
- Display opportunities table with Kalshi %, Poly %, Spread, Direction

**Step 3: Test manually**

Run dashboard: `cd dashboard && npm run dev`
Navigate to /arbitrage, verify page loads

**Step 4: Commit**

```bash
git add dashboard/src/app/arbitrage/page.tsx dashboard/src/lib/api.ts
git commit -m "feat: wire up dashboard arbitrage page"
```

---

### Task 7: Integration Test

**Files:**
- Create: `tests/integration/test_arbitrage_flow.py`

**Step 1: Write integration test**

```python
"""Integration test for arbitrage flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.services.arbitrage import ArbitrageMonitorService
from polymind.data.models import SignalSource


class TestArbitrageIntegration:
    """Integration tests for arbitrage pipeline."""

    @pytest.mark.asyncio
    async def test_full_arbitrage_flow(self):
        """Test signal generation flows to callback."""
        signals_received = []

        async def capture_signal(signal):
            signals_received.append(signal)

        # Setup mocks
        kalshi = AsyncMock()
        kalshi.get_market = AsyncMock(return_value=MagicMock(
            ticker="TEST",
            yes_price=0.70,
            no_price=0.30,
            title="Test",
            volume=10000,
            category="test",
        ))

        poly = AsyncMock()
        poly.get_market = AsyncMock(return_value={"price": 0.60, "volume": 50000})

        db = AsyncMock()
        db.get_all_market_mappings = AsyncMock(return_value=[
            MagicMock(
                id=1,
                polymarket_id="poly-123",
                kalshi_id="KALSHI-123",
                description="Test",
                active=True,
            )
        ])

        service = ArbitrageMonitorService(
            kalshi_client=kalshi,
            polymarket_client=poly,
            db=db,
            min_spread=0.05,
            on_signal=capture_signal,
        )

        await service.scan()

        assert len(signals_received) == 1
        signal = signals_received[0]
        assert signal.source == SignalSource.ARBITRAGE
        assert signal.side == "YES"
```

**Step 2: Run integration test**

Run: `pytest tests/integration/test_arbitrage_flow.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_arbitrage_flow.py
git commit -m "test: add arbitrage integration test"
```

---

## Summary

After completing all tasks:
1. ArbitrageSettings in config with env vars
2. ArbitrageMonitorService with scan() and continuous monitoring
3. Wired into BotRunner (starts if enabled)
4. API endpoints: GET /arbitrage/opportunities, POST /arbitrage/scan
5. Dashboard shows real opportunities with scan button

**To enable:** Set `POLYMIND_ARBITRAGE_ENABLED=true` in .env
