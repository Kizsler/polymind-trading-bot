# PolyMind Phase 3: AI Decision Brain Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the AI Decision Brain that evaluates trade signals using Claude API, with risk management and paper trading execution.

**Architecture:** Trade signals from Phase 2 flow into the Decision Brain, which queries wallet metrics and market data, calls Claude API for approval decision, validates against risk limits, and executes in paper mode. All decisions are logged for learning.

**Tech Stack:** anthropic SDK, asyncio, SQLAlchemy async, Redis

---

## Task 1: Decision Context Builder

**Files:**
- Create: `src/polymind/core/__init__.py`
- Create: `src/polymind/core/brain/__init__.py`
- Create: `src/polymind/core/brain/context.py`
- Create: `tests/core/__init__.py`
- Create: `tests/core/brain/__init__.py`
- Create: `tests/core/brain/test_context.py`

**Step 1: Write failing test for context builder**

Create `tests/core/__init__.py`:
```python
"""Core module tests."""
```

Create `tests/core/brain/__init__.py`:
```python
"""Brain module tests."""
```

Create `tests/core/brain/test_context.py`:
```python
"""Tests for decision context builder."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.core.brain.context import DecisionContext, DecisionContextBuilder
from polymind.data.models import SignalSource, TradeSignal


@pytest.fixture
def sample_signal() -> TradeSignal:
    """Create sample trade signal."""
    return TradeSignal(
        wallet="0x1234567890abcdef1234567890abcdef12345678",
        market_id="will-btc-hit-100k",
        token_id="token123",
        side="YES",
        size=500.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Create mock cache."""
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=-120.0)
    cache.get_open_exposure = AsyncMock(return_value=800.0)
    return cache


@pytest.fixture
def mock_market_service() -> MagicMock:
    """Create mock market data service."""
    service = MagicMock()
    service.get_liquidity = AsyncMock(return_value=25000.0)
    service.get_spread = AsyncMock(return_value=0.02)
    return service


def test_decision_context_to_dict() -> None:
    """DecisionContext should serialize to dict for Claude."""
    context = DecisionContext(
        signal_wallet="0x123",
        signal_market_id="market1",
        signal_side="YES",
        signal_size=100.0,
        signal_price=0.65,
        wallet_win_rate=0.72,
        wallet_avg_roi=1.34,
        wallet_total_trades=156,
        wallet_recent_performance="3W-1L",
        market_liquidity=25000.0,
        market_spread=0.02,
        risk_daily_pnl=-120.0,
        risk_open_exposure=800.0,
        risk_max_daily_loss=500.0,
    )

    result = context.to_dict()

    assert result["signal"]["wallet"] == "0x123"
    assert result["signal"]["side"] == "YES"
    assert result["wallet_metrics"]["win_rate"] == 0.72
    assert result["market_data"]["liquidity"] == 25000.0
    assert result["risk_state"]["daily_pnl"] == -120.0


@pytest.mark.asyncio
async def test_context_builder_builds_context(
    sample_signal: TradeSignal,
    mock_cache: AsyncMock,
    mock_market_service: MagicMock,
) -> None:
    """Builder should construct complete context from signal."""
    # Mock wallet metrics query
    mock_db = AsyncMock()
    mock_wallet_metrics = MagicMock()
    mock_wallet_metrics.win_rate = 0.72
    mock_wallet_metrics.avg_roi = 1.34
    mock_wallet_metrics.total_trades = 156
    mock_db.get_wallet_metrics = AsyncMock(return_value=mock_wallet_metrics)

    builder = DecisionContextBuilder(
        cache=mock_cache,
        market_service=mock_market_service,
        db=mock_db,
        max_daily_loss=500.0,
    )

    context = await builder.build(sample_signal)

    assert context.signal_wallet == sample_signal.wallet
    assert context.wallet_win_rate == 0.72
    assert context.market_liquidity == 25000.0
    assert context.risk_daily_pnl == -120.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/brain/test_context.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement context builder**

Create `src/polymind/core/__init__.py`:
```python
"""Core bot logic."""
```

Create `src/polymind/core/brain/__init__.py`:
```python
"""AI Decision Brain."""

from polymind.core.brain.context import DecisionContext, DecisionContextBuilder

__all__ = ["DecisionContext", "DecisionContextBuilder"]
```

Create `src/polymind/core/brain/context.py`:
```python
"""Decision context for AI evaluation."""

from dataclasses import dataclass
from typing import Any, Protocol

from polymind.data.models import TradeSignal


class CacheProtocol(Protocol):
    """Protocol for cache operations."""

    async def get_daily_pnl(self) -> float: ...
    async def get_open_exposure(self) -> float: ...


class MarketServiceProtocol(Protocol):
    """Protocol for market data service."""

    async def get_liquidity(self, token_id: str) -> float: ...
    async def get_spread(self, token_id: str) -> float: ...


class WalletMetricsProtocol(Protocol):
    """Protocol for wallet metrics."""

    win_rate: float
    avg_roi: float
    total_trades: int


class DatabaseProtocol(Protocol):
    """Protocol for database operations."""

    async def get_wallet_metrics(self, address: str) -> WalletMetricsProtocol | None: ...


@dataclass
class DecisionContext:
    """Complete context for AI decision making.

    Contains all information needed for Claude to evaluate
    whether to execute a trade.
    """

    # Signal info
    signal_wallet: str
    signal_market_id: str
    signal_side: str
    signal_size: float
    signal_price: float

    # Wallet metrics
    wallet_win_rate: float
    wallet_avg_roi: float
    wallet_total_trades: int
    wallet_recent_performance: str

    # Market data
    market_liquidity: float
    market_spread: float

    # Risk state
    risk_daily_pnl: float
    risk_open_exposure: float
    risk_max_daily_loss: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Claude API.

        Returns:
            Structured context dict matching design spec.
        """
        return {
            "signal": {
                "wallet": self.signal_wallet,
                "market_id": self.signal_market_id,
                "side": self.signal_side,
                "size": self.signal_size,
                "current_price": self.signal_price,
            },
            "wallet_metrics": {
                "win_rate": self.wallet_win_rate,
                "avg_roi": self.wallet_avg_roi,
                "total_trades": self.wallet_total_trades,
                "recent_performance": self.wallet_recent_performance,
            },
            "market_data": {
                "liquidity": self.market_liquidity,
                "spread": self.market_spread,
            },
            "risk_state": {
                "daily_pnl": self.risk_daily_pnl,
                "open_exposure": self.risk_open_exposure,
                "max_daily_loss": self.risk_max_daily_loss,
            },
        }


class DecisionContextBuilder:
    """Builds decision context from signal and external data."""

    def __init__(
        self,
        cache: CacheProtocol,
        market_service: MarketServiceProtocol,
        db: DatabaseProtocol,
        max_daily_loss: float = 500.0,
    ) -> None:
        """Initialize builder.

        Args:
            cache: Redis cache for risk state.
            market_service: Market data service.
            db: Database for wallet metrics.
            max_daily_loss: Maximum daily loss limit.
        """
        self._cache = cache
        self._market_service = market_service
        self._db = db
        self._max_daily_loss = max_daily_loss

    async def build(self, signal: TradeSignal) -> DecisionContext:
        """Build complete decision context.

        Args:
            signal: Trade signal to evaluate.

        Returns:
            Complete context for AI decision.
        """
        # Get wallet metrics
        metrics = await self._db.get_wallet_metrics(signal.wallet)

        # Get market data
        liquidity = await self._market_service.get_liquidity(signal.token_id)
        spread = await self._market_service.get_spread(signal.token_id)

        # Get risk state
        daily_pnl = await self._cache.get_daily_pnl()
        open_exposure = await self._cache.get_open_exposure()

        return DecisionContext(
            signal_wallet=signal.wallet,
            signal_market_id=signal.market_id,
            signal_side=signal.side,
            signal_size=signal.size,
            signal_price=signal.price,
            wallet_win_rate=metrics.win_rate if metrics else 0.0,
            wallet_avg_roi=metrics.avg_roi if metrics else 0.0,
            wallet_total_trades=metrics.total_trades if metrics else 0,
            wallet_recent_performance="Unknown",
            market_liquidity=liquidity,
            market_spread=spread,
            risk_daily_pnl=daily_pnl,
            risk_open_exposure=open_exposure,
            risk_max_daily_loss=self._max_daily_loss,
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/brain/test_context.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/polymind/core/ tests/core/
git commit -m "feat: add decision context builder for AI brain"
```

---

## Task 2: AI Decision Response Model

**Files:**
- Create: `src/polymind/core/brain/decision.py`
- Create: `tests/core/brain/test_decision.py`

**Step 1: Write failing test for decision model**

Create `tests/core/brain/test_decision.py`:
```python
"""Tests for AI decision response model."""

import pytest

from polymind.core.brain.decision import AIDecision, Urgency


def test_decision_from_dict() -> None:
    """AIDecision should parse from dictionary."""
    data = {
        "execute": True,
        "size": 250.0,
        "confidence": 0.78,
        "urgency": "normal",
        "reasoning": "Strong wallet, good liquidity",
    }

    decision = AIDecision.from_dict(data)

    assert decision.execute is True
    assert decision.size == 250.0
    assert decision.confidence == 0.78
    assert decision.urgency == Urgency.NORMAL
    assert "Strong wallet" in decision.reasoning


def test_decision_reject() -> None:
    """AIDecision.reject should create rejection decision."""
    decision = AIDecision.reject("Wallet performance too low")

    assert decision.execute is False
    assert decision.size == 0.0
    assert decision.confidence == 1.0
    assert "Wallet performance" in decision.reasoning


def test_decision_approve() -> None:
    """AIDecision.approve should create approval decision."""
    decision = AIDecision.approve(
        size=100.0,
        confidence=0.85,
        reasoning="Good opportunity",
    )

    assert decision.execute is True
    assert decision.size == 100.0
    assert decision.confidence == 0.85


def test_urgency_from_string() -> None:
    """Urgency should parse from string."""
    assert Urgency.from_string("high") == Urgency.HIGH
    assert Urgency.from_string("normal") == Urgency.NORMAL
    assert Urgency.from_string("low") == Urgency.LOW
    assert Urgency.from_string("unknown") == Urgency.NORMAL
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/brain/test_decision.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement decision model**

Create `src/polymind/core/brain/decision.py`:
```python
"""AI decision response model."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Urgency(Enum):
    """Trade urgency level."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    @classmethod
    def from_string(cls, value: str) -> "Urgency":
        """Parse urgency from string.

        Args:
            value: String urgency value.

        Returns:
            Urgency enum, defaults to NORMAL.
        """
        try:
            return cls(value.lower())
        except ValueError:
            return cls.NORMAL


@dataclass
class AIDecision:
    """AI decision response for a trade signal.

    Represents Claude's decision on whether to execute
    a trade and with what parameters.
    """

    execute: bool
    size: float
    confidence: float
    urgency: Urgency
    reasoning: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AIDecision":
        """Create decision from dictionary.

        Args:
            data: Dictionary with decision fields.

        Returns:
            AIDecision instance.
        """
        return cls(
            execute=bool(data.get("execute", False)),
            size=float(data.get("size", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            urgency=Urgency.from_string(data.get("urgency", "normal")),
            reasoning=str(data.get("reasoning", "")),
        )

    @classmethod
    def reject(cls, reasoning: str) -> "AIDecision":
        """Create a rejection decision.

        Args:
            reasoning: Why the trade was rejected.

        Returns:
            Rejection decision.
        """
        return cls(
            execute=False,
            size=0.0,
            confidence=1.0,
            urgency=Urgency.NORMAL,
            reasoning=reasoning,
        )

    @classmethod
    def approve(
        cls,
        size: float,
        confidence: float,
        reasoning: str,
        urgency: Urgency = Urgency.NORMAL,
    ) -> "AIDecision":
        """Create an approval decision.

        Args:
            size: Trade size to execute.
            confidence: Confidence level (0-1).
            reasoning: Why the trade was approved.
            urgency: Execution urgency.

        Returns:
            Approval decision.
        """
        return cls(
            execute=True,
            size=size,
            confidence=confidence,
            urgency=urgency,
            reasoning=reasoning,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "execute": self.execute,
            "size": self.size,
            "confidence": self.confidence,
            "urgency": self.urgency.value,
            "reasoning": self.reasoning,
        }
```

Update `src/polymind/core/brain/__init__.py`:
```python
"""AI Decision Brain."""

from polymind.core.brain.context import DecisionContext, DecisionContextBuilder
from polymind.core.brain.decision import AIDecision, Urgency

__all__ = [
    "DecisionContext",
    "DecisionContextBuilder",
    "AIDecision",
    "Urgency",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/brain/test_decision.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/polymind/core/brain/ tests/core/brain/
git commit -m "feat: add AI decision response model"
```

---

## Task 3: Claude API Client

**Files:**
- Create: `src/polymind/core/brain/claude.py`
- Create: `tests/core/brain/test_claude.py`

**Step 1: Write failing test for Claude client**

Create `tests/core/brain/test_claude.py`:
```python
"""Tests for Claude API client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.core.brain.claude import ClaudeClient
from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision, Urgency


@pytest.fixture
def sample_context() -> DecisionContext:
    """Create sample decision context."""
    return DecisionContext(
        signal_wallet="0x123",
        signal_market_id="market1",
        signal_side="YES",
        signal_size=100.0,
        signal_price=0.65,
        wallet_win_rate=0.72,
        wallet_avg_roi=1.34,
        wallet_total_trades=156,
        wallet_recent_performance="3W-1L",
        market_liquidity=25000.0,
        market_spread=0.02,
        risk_daily_pnl=-120.0,
        risk_open_exposure=800.0,
        risk_max_daily_loss=500.0,
    )


def test_client_creates_prompt(sample_context: DecisionContext) -> None:
    """Client should create structured prompt from context."""
    client = ClaudeClient(api_key="test-key")
    prompt = client._build_prompt(sample_context)

    assert "0x123" in prompt
    assert "YES" in prompt
    assert "0.72" in prompt
    assert "25000" in prompt


@pytest.mark.asyncio
async def test_client_evaluate_returns_decision(
    sample_context: DecisionContext,
) -> None:
    """Client should return AIDecision from Claude response."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps({
                "execute": True,
                "size": 50.0,
                "confidence": 0.85,
                "urgency": "normal",
                "reasoning": "Good opportunity",
            })
        )
    ]

    with patch("polymind.core.brain.claude.AsyncAnthropic") as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        client = ClaudeClient(api_key="test-key")
        decision = await client.evaluate(sample_context)

        assert decision.execute is True
        assert decision.size == 50.0
        assert decision.confidence == 0.85


@pytest.mark.asyncio
async def test_client_handles_api_error(sample_context: DecisionContext) -> None:
    """Client should return rejection on API error."""
    with patch("polymind.core.brain.claude.AsyncAnthropic") as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API Error")
        )
        mock_anthropic.return_value = mock_client

        client = ClaudeClient(api_key="test-key")
        decision = await client.evaluate(sample_context)

        assert decision.execute is False
        assert "Error" in decision.reasoning
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/brain/test_claude.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement Claude client**

Create `src/polymind/core/brain/claude.py`:
```python
"""Claude API client for trade decisions."""

import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI trading assistant for a prediction market copy-trading bot.

Your job is to evaluate trade signals from wallets we're copying and decide:
1. Whether to execute the trade (true/false)
2. What size to trade (may be smaller than the copied trade)
3. Your confidence level (0.0 to 1.0)
4. Urgency (high/normal/low)
5. Brief reasoning

Consider:
- Wallet performance metrics (win rate, ROI, trade history)
- Market liquidity and spread
- Current risk exposure and daily P&L
- Risk limits

Always respond with valid JSON in this exact format:
{
    "execute": true,
    "size": 50.0,
    "confidence": 0.85,
    "urgency": "normal",
    "reasoning": "Brief explanation"
}

Be conservative. Protect capital. Only approve high-confidence trades."""


class ClaudeClient:
    """Async client for Claude API trade decisions."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 512,
    ) -> None:
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key.
            model: Model to use.
            max_tokens: Max response tokens.
        """
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def _build_prompt(self, context: DecisionContext) -> str:
        """Build user prompt from decision context.

        Args:
            context: Decision context with all data.

        Returns:
            Formatted prompt string.
        """
        ctx = context.to_dict()
        return f"""Evaluate this trade signal:

**Signal:**
- Wallet: {ctx['signal']['wallet']}
- Market: {ctx['signal']['market_id']}
- Side: {ctx['signal']['side']}
- Size: ${ctx['signal']['size']}
- Price: {ctx['signal']['current_price']}

**Wallet Metrics:**
- Win Rate: {ctx['wallet_metrics']['win_rate']:.0%}
- Avg ROI: {ctx['wallet_metrics']['avg_roi']:.2f}x
- Total Trades: {ctx['wallet_metrics']['total_trades']}
- Recent: {ctx['wallet_metrics']['recent_performance']}

**Market Data:**
- Liquidity: ${ctx['market_data']['liquidity']:,.0f}
- Spread: {ctx['market_data']['spread']:.1%}

**Risk State:**
- Daily P&L: ${ctx['risk_state']['daily_pnl']:+.2f}
- Open Exposure: ${ctx['risk_state']['open_exposure']:,.0f}
- Max Daily Loss: ${ctx['risk_state']['max_daily_loss']:,.0f}

Should we copy this trade? Respond with JSON."""

    async def evaluate(self, context: DecisionContext) -> AIDecision:
        """Evaluate trade signal with Claude.

        Args:
            context: Complete decision context.

        Returns:
            AI decision on the trade.
        """
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": self._build_prompt(context)}
                ],
            )

            # Parse JSON response
            response_text = response.content[0].text
            decision_data = json.loads(response_text)

            return AIDecision.from_dict(decision_data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return AIDecision.reject(f"Failed to parse AI response: {e}")

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return AIDecision.reject(f"AI Error: {e}")
```

Update `src/polymind/core/brain/__init__.py`:
```python
"""AI Decision Brain."""

from polymind.core.brain.claude import ClaudeClient
from polymind.core.brain.context import DecisionContext, DecisionContextBuilder
from polymind.core.brain.decision import AIDecision, Urgency

__all__ = [
    "ClaudeClient",
    "DecisionContext",
    "DecisionContextBuilder",
    "AIDecision",
    "Urgency",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/brain/test_claude.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/polymind/core/brain/ tests/core/brain/
git commit -m "feat: add Claude API client for trade decisions"
```

---

## Task 4: Risk Manager

**Files:**
- Create: `src/polymind/core/risk/__init__.py`
- Create: `src/polymind/core/risk/manager.py`
- Create: `tests/core/risk/__init__.py`
- Create: `tests/core/risk/test_manager.py`

**Step 1: Write failing test for risk manager**

Create `tests/core/risk/__init__.py`:
```python
"""Risk module tests."""
```

Create `tests/core/risk/test_manager.py`:
```python
"""Tests for risk manager."""

from unittest.mock import AsyncMock

import pytest

from polymind.core.brain.decision import AIDecision, Urgency
from polymind.core.risk.manager import RiskManager, RiskViolation


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Create mock cache."""
    cache = AsyncMock()
    cache.get_daily_pnl = AsyncMock(return_value=-100.0)
    cache.get_open_exposure = AsyncMock(return_value=500.0)
    return cache


@pytest.fixture
def risk_manager(mock_cache: AsyncMock) -> RiskManager:
    """Create risk manager with mocks."""
    return RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )


@pytest.mark.asyncio
async def test_risk_manager_allows_valid_trade(
    risk_manager: RiskManager,
) -> None:
    """Manager should allow trades within limits."""
    decision = AIDecision.approve(
        size=50.0,
        confidence=0.85,
        reasoning="Good trade",
    )

    result = await risk_manager.validate(decision)

    assert result.execute is True
    assert result.size == 50.0


@pytest.mark.asyncio
async def test_risk_manager_blocks_over_daily_loss(
    mock_cache: AsyncMock,
) -> None:
    """Manager should block trades when daily loss exceeded."""
    mock_cache.get_daily_pnl = AsyncMock(return_value=-600.0)  # Over limit

    manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(size=50.0, confidence=0.85, reasoning="Good")
    result = await manager.validate(decision)

    assert result.execute is False
    assert "daily loss" in result.reasoning.lower()


@pytest.mark.asyncio
async def test_risk_manager_reduces_oversized_trade(
    risk_manager: RiskManager,
) -> None:
    """Manager should reduce trades exceeding single trade limit."""
    decision = AIDecision.approve(
        size=150.0,  # Over single trade limit
        confidence=0.85,
        reasoning="Good trade",
    )

    result = await risk_manager.validate(decision)

    assert result.execute is True
    assert result.size == 100.0  # Capped at max_single_trade


@pytest.mark.asyncio
async def test_risk_manager_blocks_over_total_exposure(
    mock_cache: AsyncMock,
) -> None:
    """Manager should block trades that would exceed total exposure."""
    mock_cache.get_open_exposure = AsyncMock(return_value=1950.0)

    manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(size=100.0, confidence=0.85, reasoning="Good")
    result = await manager.validate(decision)

    # Should reduce to fit within exposure limit
    assert result.size == 50.0  # 2000 - 1950 = 50 remaining


def test_risk_violation_enum() -> None:
    """RiskViolation should have all violation types."""
    assert RiskViolation.DAILY_LOSS_EXCEEDED.value == "daily_loss_exceeded"
    assert RiskViolation.EXPOSURE_EXCEEDED.value == "exposure_exceeded"
    assert RiskViolation.TRADE_SIZE_EXCEEDED.value == "trade_size_exceeded"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/risk/test_manager.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement risk manager**

Create `src/polymind/core/risk/__init__.py`:
```python
"""Risk management layer."""

from polymind.core.risk.manager import RiskManager, RiskViolation

__all__ = ["RiskManager", "RiskViolation"]
```

Create `src/polymind/core/risk/manager.py`:
```python
"""Risk management for trade validation."""

import logging
from enum import Enum
from typing import Protocol

from polymind.core.brain.decision import AIDecision

logger = logging.getLogger(__name__)


class RiskViolation(Enum):
    """Types of risk violations."""

    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"
    EXPOSURE_EXCEEDED = "exposure_exceeded"
    TRADE_SIZE_EXCEEDED = "trade_size_exceeded"


class CacheProtocol(Protocol):
    """Protocol for cache operations."""

    async def get_daily_pnl(self) -> float: ...
    async def get_open_exposure(self) -> float: ...


class RiskManager:
    """Validates trades against risk limits.

    Acts as a final gate before execution, ensuring
    all trades respect hard limits regardless of AI decision.
    """

    def __init__(
        self,
        cache: CacheProtocol,
        max_daily_loss: float,
        max_total_exposure: float,
        max_single_trade: float,
    ) -> None:
        """Initialize risk manager.

        Args:
            cache: Redis cache for risk state.
            max_daily_loss: Maximum allowed daily loss.
            max_total_exposure: Maximum total open exposure.
            max_single_trade: Maximum single trade size.
        """
        self._cache = cache
        self._max_daily_loss = max_daily_loss
        self._max_total_exposure = max_total_exposure
        self._max_single_trade = max_single_trade

    async def validate(self, decision: AIDecision) -> AIDecision:
        """Validate and potentially modify AI decision.

        Args:
            decision: AI decision to validate.

        Returns:
            Validated (and possibly modified) decision.
        """
        # If AI rejected, respect that
        if not decision.execute:
            return decision

        # Check daily loss limit
        daily_pnl = await self._cache.get_daily_pnl()
        if daily_pnl <= -self._max_daily_loss:
            logger.warning(
                f"Trade blocked: Daily loss limit exceeded "
                f"(P&L: ${daily_pnl:.2f}, Limit: -${self._max_daily_loss:.2f})"
            )
            return AIDecision.reject(
                f"Daily loss limit exceeded. "
                f"Current P&L: ${daily_pnl:.2f}, Limit: -${self._max_daily_loss:.2f}"
            )

        # Check and adjust trade size
        size = decision.size

        # Cap at single trade limit
        if size > self._max_single_trade:
            logger.info(
                f"Trade size capped: ${size:.2f} -> ${self._max_single_trade:.2f}"
            )
            size = self._max_single_trade

        # Check total exposure limit
        current_exposure = await self._cache.get_open_exposure()
        remaining_capacity = self._max_total_exposure - current_exposure

        if remaining_capacity <= 0:
            logger.warning(
                f"Trade blocked: Exposure limit reached "
                f"(Current: ${current_exposure:.2f}, Limit: ${self._max_total_exposure:.2f})"
            )
            return AIDecision.reject(
                f"Total exposure limit reached. "
                f"Current: ${current_exposure:.2f}, Limit: ${self._max_total_exposure:.2f}"
            )

        if size > remaining_capacity:
            logger.info(
                f"Trade size reduced for exposure: ${size:.2f} -> ${remaining_capacity:.2f}"
            )
            size = remaining_capacity

        # Return possibly modified decision
        if size != decision.size:
            return AIDecision.approve(
                size=size,
                confidence=decision.confidence,
                reasoning=f"{decision.reasoning} [Size adjusted by risk manager]",
                urgency=decision.urgency,
            )

        return decision
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/risk/test_manager.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/polymind/core/risk/ tests/core/risk/
git commit -m "feat: add risk manager for trade validation"
```

---

## Task 5: Paper Execution Engine

**Files:**
- Create: `src/polymind/core/execution/__init__.py`
- Create: `src/polymind/core/execution/paper.py`
- Create: `tests/core/execution/__init__.py`
- Create: `tests/core/execution/test_paper.py`

**Step 1: Write failing test for paper execution**

Create `tests/core/execution/__init__.py`:
```python
"""Execution module tests."""
```

Create `tests/core/execution/test_paper.py`:
```python
"""Tests for paper trading execution."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from polymind.core.brain.decision import AIDecision
from polymind.core.execution.paper import PaperExecutor, ExecutionResult
from polymind.data.models import SignalSource, TradeSignal


@pytest.fixture
def sample_signal() -> TradeSignal:
    """Create sample trade signal."""
    return TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Create mock cache."""
    cache = AsyncMock()
    cache.update_open_exposure = AsyncMock(return_value=150.0)
    return cache


@pytest.fixture
def executor(mock_cache: AsyncMock) -> PaperExecutor:
    """Create paper executor."""
    return PaperExecutor(cache=mock_cache)


@pytest.mark.asyncio
async def test_paper_executor_simulates_trade(
    executor: PaperExecutor,
    sample_signal: TradeSignal,
) -> None:
    """Executor should simulate trade execution."""
    decision = AIDecision.approve(
        size=50.0,
        confidence=0.85,
        reasoning="Good trade",
    )

    result = await executor.execute(sample_signal, decision)

    assert result.success is True
    assert result.executed_size == 50.0
    assert result.executed_price == sample_signal.price


@pytest.mark.asyncio
async def test_paper_executor_updates_exposure(
    executor: PaperExecutor,
    sample_signal: TradeSignal,
    mock_cache: AsyncMock,
) -> None:
    """Executor should update open exposure."""
    decision = AIDecision.approve(
        size=50.0,
        confidence=0.85,
        reasoning="Good trade",
    )

    await executor.execute(sample_signal, decision)

    mock_cache.update_open_exposure.assert_called_once_with(50.0)


@pytest.mark.asyncio
async def test_paper_executor_rejects_non_execute(
    executor: PaperExecutor,
    sample_signal: TradeSignal,
) -> None:
    """Executor should not execute rejected decisions."""
    decision = AIDecision.reject("Not a good trade")

    result = await executor.execute(sample_signal, decision)

    assert result.success is False
    assert result.executed_size == 0.0


def test_execution_result_to_dict() -> None:
    """ExecutionResult should serialize to dict."""
    result = ExecutionResult(
        success=True,
        executed_size=50.0,
        executed_price=0.65,
        paper_mode=True,
        message="Trade simulated",
    )

    data = result.to_dict()

    assert data["success"] is True
    assert data["executed_size"] == 50.0
    assert data["paper_mode"] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/execution/test_paper.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement paper executor**

Create `src/polymind/core/execution/__init__.py`:
```python
"""Trade execution engine."""

from polymind.core.execution.paper import ExecutionResult, PaperExecutor

__all__ = ["ExecutionResult", "PaperExecutor"]
```

Create `src/polymind/core/execution/paper.py`:
```python
"""Paper trading execution engine."""

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from polymind.core.brain.decision import AIDecision
from polymind.data.models import TradeSignal

logger = logging.getLogger(__name__)


class CacheProtocol(Protocol):
    """Protocol for cache operations."""

    async def update_open_exposure(self, delta: float) -> float: ...


@dataclass
class ExecutionResult:
    """Result of trade execution."""

    success: bool
    executed_size: float
    executed_price: float
    paper_mode: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "success": self.success,
            "executed_size": self.executed_size,
            "executed_price": self.executed_price,
            "paper_mode": self.paper_mode,
            "message": self.message,
        }


class PaperExecutor:
    """Simulates trade execution in paper mode.

    Logs trades and updates exposure tracking without
    actually executing on the exchange.
    """

    def __init__(self, cache: CacheProtocol) -> None:
        """Initialize paper executor.

        Args:
            cache: Redis cache for exposure tracking.
        """
        self._cache = cache

    async def execute(
        self,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> ExecutionResult:
        """Execute trade in paper mode.

        Args:
            signal: Original trade signal.
            decision: AI decision with execution params.

        Returns:
            Execution result.
        """
        if not decision.execute:
            return ExecutionResult(
                success=False,
                executed_size=0.0,
                executed_price=0.0,
                paper_mode=True,
                message=f"Trade rejected: {decision.reasoning}",
            )

        # Simulate execution at signal price
        executed_size = decision.size
        executed_price = signal.price

        # Update exposure tracking
        await self._cache.update_open_exposure(executed_size)

        logger.info(
            f"PAPER TRADE: {signal.side} ${executed_size:.2f} @ {executed_price:.2f} "
            f"on {signal.market_id} (wallet: {signal.wallet[:10]}...)"
        )

        return ExecutionResult(
            success=True,
            executed_size=executed_size,
            executed_price=executed_price,
            paper_mode=True,
            message=f"Paper trade executed: {signal.side} ${executed_size:.2f}",
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/execution/test_paper.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/polymind/core/execution/ tests/core/execution/
git commit -m "feat: add paper trading execution engine"
```

---

## Task 6: Decision Brain Orchestrator

**Files:**
- Create: `src/polymind/core/brain/orchestrator.py`
- Create: `tests/core/brain/test_orchestrator.py`

**Step 1: Write failing test for orchestrator**

Create `tests/core/brain/test_orchestrator.py`:
```python
"""Tests for decision brain orchestrator."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.core.brain.decision import AIDecision
from polymind.core.brain.orchestrator import DecisionBrain
from polymind.core.execution.paper import ExecutionResult
from polymind.data.models import SignalSource, TradeSignal


@pytest.fixture
def sample_signal() -> TradeSignal:
    """Create sample trade signal."""
    return TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_context_builder() -> AsyncMock:
    """Create mock context builder."""
    builder = AsyncMock()
    mock_context = MagicMock()
    builder.build = AsyncMock(return_value=mock_context)
    return builder


@pytest.fixture
def mock_claude() -> AsyncMock:
    """Create mock Claude client."""
    client = AsyncMock()
    client.evaluate = AsyncMock(
        return_value=AIDecision.approve(
            size=50.0,
            confidence=0.85,
            reasoning="Good trade",
        )
    )
    return client


@pytest.fixture
def mock_risk_manager() -> AsyncMock:
    """Create mock risk manager."""
    manager = AsyncMock()
    manager.validate = AsyncMock(
        side_effect=lambda d: d  # Pass through
    )
    return manager


@pytest.fixture
def mock_executor() -> AsyncMock:
    """Create mock executor."""
    executor = AsyncMock()
    executor.execute = AsyncMock(
        return_value=ExecutionResult(
            success=True,
            executed_size=50.0,
            executed_price=0.65,
            paper_mode=True,
            message="Trade executed",
        )
    )
    return executor


@pytest.mark.asyncio
async def test_brain_processes_signal(
    sample_signal: TradeSignal,
    mock_context_builder: AsyncMock,
    mock_claude: AsyncMock,
    mock_risk_manager: AsyncMock,
    mock_executor: AsyncMock,
) -> None:
    """Brain should process signal through full pipeline."""
    brain = DecisionBrain(
        context_builder=mock_context_builder,
        claude_client=mock_claude,
        risk_manager=mock_risk_manager,
        executor=mock_executor,
    )

    result = await brain.process(sample_signal)

    assert result.success is True
    mock_context_builder.build.assert_called_once_with(sample_signal)
    mock_claude.evaluate.assert_called_once()
    mock_risk_manager.validate.assert_called_once()
    mock_executor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_brain_stops_on_risk_rejection(
    sample_signal: TradeSignal,
    mock_context_builder: AsyncMock,
    mock_claude: AsyncMock,
    mock_risk_manager: AsyncMock,
    mock_executor: AsyncMock,
) -> None:
    """Brain should stop if risk manager rejects."""
    mock_risk_manager.validate = AsyncMock(
        return_value=AIDecision.reject("Risk limit exceeded")
    )

    brain = DecisionBrain(
        context_builder=mock_context_builder,
        claude_client=mock_claude,
        risk_manager=mock_risk_manager,
        executor=mock_executor,
    )

    result = await brain.process(sample_signal)

    assert result.success is False
    mock_executor.execute.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/brain/test_orchestrator.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement orchestrator**

Create `src/polymind/core/brain/orchestrator.py`:
```python
"""Decision brain orchestrator."""

import logging
from typing import Protocol

from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision
from polymind.core.execution.paper import ExecutionResult
from polymind.data.models import TradeSignal

logger = logging.getLogger(__name__)


class ContextBuilderProtocol(Protocol):
    """Protocol for context builder."""

    async def build(self, signal: TradeSignal) -> DecisionContext: ...


class ClaudeClientProtocol(Protocol):
    """Protocol for Claude client."""

    async def evaluate(self, context: DecisionContext) -> AIDecision: ...


class RiskManagerProtocol(Protocol):
    """Protocol for risk manager."""

    async def validate(self, decision: AIDecision) -> AIDecision: ...


class ExecutorProtocol(Protocol):
    """Protocol for trade executor."""

    async def execute(
        self,
        signal: TradeSignal,
        decision: AIDecision,
    ) -> ExecutionResult: ...


class DecisionBrain:
    """Orchestrates the full decision pipeline.

    Pipeline:
    1. Build context from signal
    2. Get AI decision from Claude
    3. Validate with risk manager
    4. Execute (paper or live)
    """

    def __init__(
        self,
        context_builder: ContextBuilderProtocol,
        claude_client: ClaudeClientProtocol,
        risk_manager: RiskManagerProtocol,
        executor: ExecutorProtocol,
    ) -> None:
        """Initialize decision brain.

        Args:
            context_builder: Builds context from signals.
            claude_client: Claude API client.
            risk_manager: Risk validation layer.
            executor: Trade executor (paper or live).
        """
        self._context_builder = context_builder
        self._claude = claude_client
        self._risk = risk_manager
        self._executor = executor

    async def process(self, signal: TradeSignal) -> ExecutionResult:
        """Process a trade signal through the full pipeline.

        Args:
            signal: Trade signal to evaluate.

        Returns:
            Execution result.
        """
        logger.info(
            f"Processing signal: {signal.wallet[:10]}... "
            f"{signal.side} ${signal.size:.2f} on {signal.market_id}"
        )

        # Step 1: Build context
        context = await self._context_builder.build(signal)
        logger.debug(f"Context built: {context}")

        # Step 2: Get AI decision
        ai_decision = await self._claude.evaluate(context)
        logger.info(
            f"AI Decision: execute={ai_decision.execute}, "
            f"size=${ai_decision.size:.2f}, confidence={ai_decision.confidence:.2f}"
        )

        # Step 3: Validate with risk manager
        validated = await self._risk.validate(ai_decision)

        if not validated.execute:
            logger.info(f"Trade rejected: {validated.reasoning}")
            return ExecutionResult(
                success=False,
                executed_size=0.0,
                executed_price=0.0,
                paper_mode=True,
                message=validated.reasoning,
            )

        # Step 4: Execute
        result = await self._executor.execute(signal, validated)
        logger.info(f"Execution result: {result.message}")

        return result
```

Update `src/polymind/core/brain/__init__.py`:
```python
"""AI Decision Brain."""

from polymind.core.brain.claude import ClaudeClient
from polymind.core.brain.context import DecisionContext, DecisionContextBuilder
from polymind.core.brain.decision import AIDecision, Urgency
from polymind.core.brain.orchestrator import DecisionBrain

__all__ = [
    "ClaudeClient",
    "DecisionBrain",
    "DecisionContext",
    "DecisionContextBuilder",
    "AIDecision",
    "Urgency",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/brain/test_orchestrator.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/polymind/core/brain/ tests/core/brain/
git commit -m "feat: add decision brain orchestrator"
```

---

## Task 7: Integration Tests

**Files:**
- Create: `tests/integration/test_brain.py`

**Step 1: Write integration tests**

Create `tests/integration/test_brain.py`:
```python
"""Integration tests for AI decision brain."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.core.brain import (
    AIDecision,
    ClaudeClient,
    DecisionBrain,
    DecisionContext,
    DecisionContextBuilder,
)
from polymind.core.execution import PaperExecutor
from polymind.core.risk import RiskManager
from polymind.data.models import SignalSource, TradeSignal


def test_decision_context_builds_correctly() -> None:
    """Context should build complete structure."""
    context = DecisionContext(
        signal_wallet="0x123",
        signal_market_id="market1",
        signal_side="YES",
        signal_size=100.0,
        signal_price=0.65,
        wallet_win_rate=0.72,
        wallet_avg_roi=1.34,
        wallet_total_trades=156,
        wallet_recent_performance="3W-1L",
        market_liquidity=25000.0,
        market_spread=0.02,
        risk_daily_pnl=-120.0,
        risk_open_exposure=800.0,
        risk_max_daily_loss=500.0,
    )

    data = context.to_dict()

    assert "signal" in data
    assert "wallet_metrics" in data
    assert "market_data" in data
    assert "risk_state" in data


def test_ai_decision_lifecycle() -> None:
    """Decision should support full lifecycle."""
    # Create decision from dict
    decision = AIDecision.from_dict({
        "execute": True,
        "size": 50.0,
        "confidence": 0.85,
        "urgency": "high",
        "reasoning": "Good opportunity",
    })

    assert decision.execute is True

    # Convert back to dict
    data = decision.to_dict()
    assert data["size"] == 50.0

    # Create rejection
    rejection = AIDecision.reject("Not a good trade")
    assert rejection.execute is False


@pytest.mark.asyncio
async def test_risk_manager_validates_decisions() -> None:
    """Risk manager should validate AI decisions."""
    mock_cache = AsyncMock()
    mock_cache.get_daily_pnl = AsyncMock(return_value=-100.0)
    mock_cache.get_open_exposure = AsyncMock(return_value=500.0)

    manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.85,
        reasoning="Good trade",
    )

    result = await manager.validate(decision)

    assert result.execute is True
    assert result.size == 50.0


@pytest.mark.asyncio
async def test_paper_executor_simulates_trades() -> None:
    """Paper executor should simulate trade execution."""
    mock_cache = AsyncMock()
    mock_cache.update_open_exposure = AsyncMock(return_value=100.0)

    executor = PaperExecutor(cache=mock_cache)

    signal = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(timezone.utc),
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.85,
        reasoning="Good trade",
    )

    result = await executor.execute(signal, decision)

    assert result.success is True
    assert result.paper_mode is True
    assert result.executed_size == 50.0


@pytest.mark.asyncio
async def test_full_brain_pipeline() -> None:
    """Full brain pipeline should work end-to-end."""
    # Mock all dependencies
    mock_context = DecisionContext(
        signal_wallet="0x123",
        signal_market_id="market1",
        signal_side="YES",
        signal_size=100.0,
        signal_price=0.65,
        wallet_win_rate=0.72,
        wallet_avg_roi=1.34,
        wallet_total_trades=156,
        wallet_recent_performance="3W-1L",
        market_liquidity=25000.0,
        market_spread=0.02,
        risk_daily_pnl=-120.0,
        risk_open_exposure=800.0,
        risk_max_daily_loss=500.0,
    )

    mock_context_builder = AsyncMock()
    mock_context_builder.build = AsyncMock(return_value=mock_context)

    mock_claude = AsyncMock()
    mock_claude.evaluate = AsyncMock(
        return_value=AIDecision.approve(
            size=50.0,
            confidence=0.85,
            reasoning="Good trade",
        )
    )

    mock_cache = AsyncMock()
    mock_cache.get_daily_pnl = AsyncMock(return_value=-100.0)
    mock_cache.get_open_exposure = AsyncMock(return_value=500.0)
    mock_cache.update_open_exposure = AsyncMock(return_value=550.0)

    risk_manager = RiskManager(
        cache=mock_cache,
        max_daily_loss=500.0,
        max_total_exposure=2000.0,
        max_single_trade=100.0,
    )

    executor = PaperExecutor(cache=mock_cache)

    brain = DecisionBrain(
        context_builder=mock_context_builder,
        claude_client=mock_claude,
        risk_manager=risk_manager,
        executor=executor,
    )

    signal = TradeSignal(
        wallet="0x123",
        market_id="market1",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(timezone.utc),
    )

    result = await brain.process(signal)

    assert result.success is True
    assert result.executed_size == 50.0
    assert result.paper_mode is True
```

**Step 2: Run all tests**

Run: `pytest -v`
Expected: All tests pass

**Step 3: Run linting**

Run: `ruff check src tests`
Expected: All checks passed

**Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test: add brain integration tests"
```

---

## Summary

Phase 3 AI Decision Brain is complete when:

- [x] `DecisionContext` builds complete context for Claude
- [x] `AIDecision` model represents Claude's response
- [x] `ClaudeClient` calls Claude API for trade decisions
- [x] `RiskManager` validates against hard limits
- [x] `PaperExecutor` simulates trade execution
- [x] `DecisionBrain` orchestrates full pipeline
- [x] All tests pass

**Next Phase:** User Interfaces (CLI, Dashboard, Discord)
