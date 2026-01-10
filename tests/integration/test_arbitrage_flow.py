"""Integration test for arbitrage flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.data.models import SignalSource
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

    def __init__(self, poly_id: str, kalshi_id: str, description: str = "Test") -> None:
        self.id = 1
        self.polymarket_id = poly_id
        self.kalshi_id = kalshi_id
        self.description = description
        self.active = True


class TestArbitrageIntegration:
    """Integration tests for arbitrage pipeline."""

    @pytest.mark.asyncio
    async def test_full_arbitrage_flow(self) -> None:
        """Test signal generation flows to callback."""
        signals_received = []

        async def capture_signal(signal):
            signals_received.append(signal)

        # Setup mocks
        kalshi = AsyncMock()
        kalshi.get_market = AsyncMock(
            return_value=MockKalshiMarket(
                ticker="TEST",
                yes_price=0.70,
                no_price=0.30,
            )
        )

        poly = MagicMock()
        poly.get_midpoint = MagicMock(return_value=0.60)

        db = AsyncMock()
        db.get_all_market_mappings = AsyncMock(
            return_value=[
                MockMapping(
                    poly_id="poly-123",
                    kalshi_id="KALSHI-123",
                    description="Test Market",
                )
            ]
        )

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
        assert signal.market_id == "poly-123"

    @pytest.mark.asyncio
    async def test_arbitrage_direction_buy_no(self) -> None:
        """Test signal generates BUY_NO when Kalshi < Polymarket."""
        signals_received = []

        async def capture_signal(signal):
            signals_received.append(signal)

        kalshi = AsyncMock()
        kalshi.get_market = AsyncMock(
            return_value=MockKalshiMarket(
                ticker="TEST",
                yes_price=0.35,  # Lower than Polymarket
                no_price=0.65,
            )
        )

        poly = MagicMock()
        poly.get_midpoint = MagicMock(return_value=0.45)

        db = AsyncMock()
        db.get_all_market_mappings = AsyncMock(
            return_value=[MockMapping("poly-456", "KALSHI-456")]
        )

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
        assert signal.side == "NO"  # Buy NO when Kalshi is lower

    @pytest.mark.asyncio
    async def test_arbitrage_respects_spread_threshold(self) -> None:
        """Test no signal when spread is below threshold."""
        signals_received = []

        async def capture_signal(signal):
            signals_received.append(signal)

        kalshi = AsyncMock()
        kalshi.get_market = AsyncMock(
            return_value=MockKalshiMarket(
                ticker="TEST",
                yes_price=0.52,  # Only 2% spread
                no_price=0.48,
            )
        )

        poly = MagicMock()
        poly.get_midpoint = MagicMock(return_value=0.50)

        db = AsyncMock()
        db.get_all_market_mappings = AsyncMock(
            return_value=[MockMapping("poly-789", "KALSHI-789")]
        )

        service = ArbitrageMonitorService(
            kalshi_client=kalshi,
            polymarket_client=poly,
            db=db,
            min_spread=0.03,  # 3% threshold
            on_signal=capture_signal,
        )

        await service.scan()

        assert len(signals_received) == 0  # No signal for small spread

    @pytest.mark.asyncio
    async def test_arbitrage_handles_multiple_mappings(self) -> None:
        """Test scanning multiple market mappings."""
        signals_received = []

        async def capture_signal(signal):
            signals_received.append(signal)

        call_count = 0

        async def varying_kalshi_response(ticker):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First market: 10% spread
                return MockKalshiMarket(ticker, 0.70, 0.30)
            elif call_count == 2:
                # Second market: 1% spread (no signal)
                return MockKalshiMarket(ticker, 0.51, 0.49)
            else:
                # Third market: 8% spread
                return MockKalshiMarket(ticker, 0.58, 0.42)

        kalshi = AsyncMock()
        kalshi.get_market = AsyncMock(side_effect=varying_kalshi_response)

        poly = MagicMock()
        poly.get_midpoint = MagicMock(return_value=0.50)

        db = AsyncMock()
        db.get_all_market_mappings = AsyncMock(
            return_value=[
                MockMapping("poly-1", "KALSHI-1"),
                MockMapping("poly-2", "KALSHI-2"),
                MockMapping("poly-3", "KALSHI-3"),
            ]
        )

        service = ArbitrageMonitorService(
            kalshi_client=kalshi,
            polymarket_client=poly,
            db=db,
            min_spread=0.05,
            on_signal=capture_signal,
        )

        opportunities = await service.scan()

        # Should find 2 opportunities (first and third)
        assert len(opportunities) == 2
        assert len(signals_received) == 2

    @pytest.mark.asyncio
    async def test_arbitrage_signal_size_scaling(self) -> None:
        """Test that signal size scales with spread magnitude."""
        signals_received = []

        async def capture_signal(signal):
            signals_received.append(signal)

        # 10% spread = max size (100%)
        kalshi = AsyncMock()
        kalshi.get_market = AsyncMock(
            return_value=MockKalshiMarket("TEST", 0.70, 0.30)
        )

        poly = MagicMock()
        poly.get_midpoint = MagicMock(return_value=0.60)

        db = AsyncMock()
        db.get_all_market_mappings = AsyncMock(
            return_value=[MockMapping("poly-123", "KALSHI-123")]
        )

        service = ArbitrageMonitorService(
            kalshi_client=kalshi,
            polymarket_client=poly,
            db=db,
            min_spread=0.05,
            max_signal_size=100.0,
            on_signal=capture_signal,
        )

        await service.scan()

        assert len(signals_received) == 1
        signal = signals_received[0]
        # 10% spread = 100% of max_signal_size = 100.0
        assert signal.size == pytest.approx(100.0, rel=0.01)
