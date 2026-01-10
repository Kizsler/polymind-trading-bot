"""Tests for ArbitrageMonitorService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.data.models import SignalSource, TradeSignal
from polymind.services.arbitrage import ArbitrageMonitorService


class MockKalshiMarket:
    """Mock Kalshi market."""

    def __init__(self, ticker: str, yes_price: float, no_price: float) -> None:
        self.ticker = ticker
        self.title = f"Test Market {ticker}"
        self.yes_price = yes_price
        self.no_price = no_price
        self.volume = 10000
        self.category = "test"


class MockMapping:
    """Mock market mapping."""

    def __init__(self, poly_id: str, kalshi_id: str) -> None:
        self.id = 1
        self.polymarket_id = poly_id
        self.kalshi_id = kalshi_id
        self.description = "Test mapping"
        self.active = True


@pytest.fixture
def mock_kalshi_client() -> AsyncMock:
    """Create mock Kalshi client."""
    client = AsyncMock()
    client.get_market = AsyncMock(
        return_value=MockKalshiMarket(
            ticker="TEST-TICKER",
            yes_price=0.65,
            no_price=0.35,
        )
    )
    return client


@pytest.fixture
def mock_polymarket_client() -> MagicMock:
    """Create mock Polymarket client (sync)."""
    client = MagicMock()
    client.get_midpoint = MagicMock(return_value=0.58)
    return client


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create mock database."""
    db = AsyncMock()
    db.get_all_market_mappings = AsyncMock(
        return_value=[
            MockMapping("poly-123", "KALSHI-123"),
        ]
    )
    return db


@pytest.fixture
def service(
    mock_kalshi_client: AsyncMock,
    mock_polymarket_client: MagicMock,
    mock_db: AsyncMock,
) -> ArbitrageMonitorService:
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
    async def test_scan_finds_opportunity(
        self,
        service: ArbitrageMonitorService,
        mock_db: AsyncMock,
    ) -> None:
        """Scan detects opportunity when spread exceeds threshold."""
        opportunities = await service.scan()

        assert len(opportunities) == 1
        opp = opportunities[0]
        assert opp["polymarket_id"] == "poly-123"
        assert opp["kalshi_id"] == "KALSHI-123"
        assert opp["spread"] == pytest.approx(0.07, abs=0.01)
        assert opp["direction"] == "BUY_YES"

    @pytest.mark.asyncio
    async def test_scan_ignores_small_spread(
        self,
        service: ArbitrageMonitorService,
        mock_kalshi_client: AsyncMock,
    ) -> None:
        """Scan ignores opportunities below threshold."""
        mock_kalshi_client.get_market = AsyncMock(
            return_value=MockKalshiMarket(
                ticker="TEST",
                yes_price=0.59,  # Only 1% spread
                no_price=0.41,
            )
        )

        opportunities = await service.scan()

        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_scan_triggers_callback(
        self,
        service: ArbitrageMonitorService,
    ) -> None:
        """Scan calls on_signal callback for valid opportunities."""
        await service.scan()

        service._on_signal.assert_called_once()
        signal = service._on_signal.call_args[0][0]
        assert isinstance(signal, TradeSignal)
        assert signal.source == SignalSource.ARBITRAGE

    def test_calculate_direction_buy_yes(
        self,
        service: ArbitrageMonitorService,
    ) -> None:
        """Direction is BUY_YES when Kalshi > Polymarket."""
        direction = service._calculate_direction(
            kalshi_price=0.70,
            poly_price=0.60,
        )
        assert direction == "BUY_YES"

    def test_calculate_direction_buy_no(
        self,
        service: ArbitrageMonitorService,
    ) -> None:
        """Direction is BUY_NO when Kalshi < Polymarket."""
        direction = service._calculate_direction(
            kalshi_price=0.40,
            poly_price=0.50,
        )
        assert direction == "BUY_NO"

    @pytest.mark.asyncio
    async def test_scan_handles_inactive_mappings(
        self,
        service: ArbitrageMonitorService,
        mock_db: AsyncMock,
    ) -> None:
        """Scan skips inactive mappings."""
        inactive_mapping = MockMapping("poly-inactive", "KALSHI-inactive")
        inactive_mapping.active = False
        mock_db.get_all_market_mappings = AsyncMock(return_value=[inactive_mapping])

        opportunities = await service.scan()

        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_scan_handles_no_mappings(
        self,
        service: ArbitrageMonitorService,
        mock_db: AsyncMock,
    ) -> None:
        """Scan returns empty list when no mappings exist."""
        mock_db.get_all_market_mappings = AsyncMock(return_value=[])

        opportunities = await service.scan()

        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_scan_handles_kalshi_error(
        self,
        service: ArbitrageMonitorService,
        mock_kalshi_client: AsyncMock,
    ) -> None:
        """Scan continues if Kalshi request fails for a mapping."""
        mock_kalshi_client.get_market = AsyncMock(return_value=None)

        opportunities = await service.scan()

        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_scan_handles_polymarket_error(
        self,
        service: ArbitrageMonitorService,
        mock_polymarket_client: MagicMock,
    ) -> None:
        """Scan continues if Polymarket request fails for a mapping."""
        mock_polymarket_client.get_midpoint = MagicMock(side_effect=Exception("API error"))

        opportunities = await service.scan()

        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_create_signal_scales_size_with_spread(
        self,
        service: ArbitrageMonitorService,
    ) -> None:
        """Signal size scales with spread magnitude."""
        mapping = MockMapping("poly-123", "KALSHI-123")

        # 5% spread = 50% of max size
        opp = {
            "polymarket_id": "poly-123",
            "kalshi_id": "KALSHI-123",
            "description": "Test",
            "kalshi_price": 0.65,
            "poly_price": 0.60,
            "spread": 0.05,
            "direction": "BUY_YES",
        }

        signal = service._create_signal(opp, mapping)

        assert signal.size == pytest.approx(50.0, abs=1.0)  # 50% of 100.0 max

    @pytest.mark.asyncio
    async def test_create_signal_caps_at_10_percent(
        self,
        service: ArbitrageMonitorService,
    ) -> None:
        """Signal size is capped at max for large spreads."""
        mapping = MockMapping("poly-123", "KALSHI-123")

        # 15% spread should cap at max size
        opp = {
            "polymarket_id": "poly-123",
            "kalshi_id": "KALSHI-123",
            "description": "Test",
            "kalshi_price": 0.75,
            "poly_price": 0.60,
            "spread": 0.15,
            "direction": "BUY_YES",
        }

        signal = service._create_signal(opp, mapping)

        assert signal.size == service.max_signal_size  # Capped at 100.0
