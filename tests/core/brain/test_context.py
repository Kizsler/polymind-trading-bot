"""Tests for decision context module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from polymind.core.brain.context import DecisionContext, DecisionContextBuilder
from polymind.data.models import SignalSource, TradeSignal


class TestDecisionContext:
    """Tests for DecisionContext dataclass."""

    def test_decision_context_to_dict(self):
        """Verify dict structure matches design spec format."""
        context = DecisionContext(
            # Signal data
            signal_wallet="0x1234567890abcdef1234567890abcdef12345678",
            signal_market_id="btc-50k-friday",
            signal_side="YES",
            signal_size=250.0,
            signal_price=0.65,
            # Wallet performance
            wallet_win_rate=0.72,
            wallet_avg_roi=0.15,
            wallet_total_trades=100,
            wallet_recent_performance=0.08,
            # Market conditions
            market_liquidity=50000.0,
            market_spread=0.02,
            # Risk state
            risk_daily_pnl=-50.0,
            risk_open_exposure=1000.0,
            risk_max_daily_loss=500.0,
        )

        result = context.to_dict()

        # Verify top-level structure
        assert "signal" in result
        assert "wallet" in result
        assert "market" in result
        assert "risk" in result

        # Verify signal section
        expected_wallet = "0x1234567890abcdef1234567890abcdef12345678"
        assert result["signal"]["wallet"] == expected_wallet
        assert result["signal"]["market_id"] == "btc-50k-friday"
        assert result["signal"]["side"] == "YES"
        assert result["signal"]["size"] == 250.0
        assert result["signal"]["price"] == 0.65

        # Verify wallet section
        assert result["wallet"]["win_rate"] == 0.72
        assert result["wallet"]["avg_roi"] == 0.15
        assert result["wallet"]["total_trades"] == 100
        assert result["wallet"]["recent_performance"] == 0.08

        # Verify market section
        assert result["market"]["liquidity"] == 50000.0
        assert result["market"]["spread"] == 0.02

        # Verify risk section
        assert result["risk"]["daily_pnl"] == -50.0
        assert result["risk"]["open_exposure"] == 1000.0
        assert result["risk"]["max_daily_loss"] == 500.0

    def test_decision_context_to_dict_with_zero_values(self):
        """Context with zero values should still produce valid dict."""
        context = DecisionContext(
            signal_wallet="0x0000000000000000000000000000000000000000",
            signal_market_id="test-market",
            signal_side="NO",
            signal_size=0.0,
            signal_price=0.0,
            wallet_win_rate=0.0,
            wallet_avg_roi=0.0,
            wallet_total_trades=0,
            wallet_recent_performance=0.0,
            market_liquidity=0.0,
            market_spread=0.0,
            risk_daily_pnl=0.0,
            risk_open_exposure=0.0,
            risk_max_daily_loss=500.0,
        )

        result = context.to_dict()

        # All sections should exist even with zero values
        assert result["signal"]["size"] == 0.0
        assert result["wallet"]["total_trades"] == 0
        assert result["market"]["liquidity"] == 0.0
        assert result["risk"]["daily_pnl"] == 0.0


class TestDecisionContextBuilder:
    """Tests for DecisionContextBuilder class."""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache with Protocol methods."""
        cache = AsyncMock()
        cache.get_daily_pnl = AsyncMock(return_value=-75.50)
        cache.get_open_exposure = AsyncMock(return_value=1500.0)
        return cache

    @pytest.fixture
    def mock_market_service(self):
        """Create mock market service with Protocol methods."""
        service = AsyncMock()
        service.get_liquidity = AsyncMock(return_value=25000.0)
        service.get_spread = AsyncMock(return_value=0.015)
        return service

    @pytest.fixture
    def mock_db(self):
        """Create mock database with Protocol methods."""
        db = AsyncMock()
        db.get_wallet_metrics = AsyncMock(
            return_value={
                "win_rate": 0.68,
                "avg_roi": 0.12,
                "total_trades": 50,
                "recent_performance": 0.05,
            }
        )
        return db

    @pytest.fixture
    def sample_signal(self):
        """Create sample trade signal."""
        return TradeSignal(
            wallet="0x1234567890abcdef1234567890abcdef12345678",
            market_id="eth-5k-monday",
            token_id="token456",
            side="YES",
            size=100.0,
            price=0.55,
            source=SignalSource.CLOB,
            timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
            tx_hash="0xdef456",
        )

    @pytest.mark.asyncio
    async def test_context_builder_builds_context(
        self, mock_cache, mock_market_service, mock_db, sample_signal
    ):
        """Verify builder assembles all data correctly."""
        builder = DecisionContextBuilder(
            cache=mock_cache,
            market_service=mock_market_service,
            db=mock_db,
            max_daily_loss=600.0,
        )

        context = await builder.build(sample_signal)

        # Verify signal data from input
        assert context.signal_wallet == "0x1234567890abcdef1234567890abcdef12345678"
        assert context.signal_market_id == "eth-5k-monday"
        assert context.signal_side == "YES"
        assert context.signal_size == 100.0
        assert context.signal_price == 0.55

        # Verify wallet data from mock db
        assert context.wallet_win_rate == 0.68
        assert context.wallet_avg_roi == 0.12
        assert context.wallet_total_trades == 50
        assert context.wallet_recent_performance == 0.05

        # Verify market data from mock service
        assert context.market_liquidity == 25000.0
        assert context.market_spread == 0.015

        # Verify risk data from mock cache
        assert context.risk_daily_pnl == -75.50
        assert context.risk_open_exposure == 1500.0
        assert context.risk_max_daily_loss == 600.0

    @pytest.mark.asyncio
    async def test_context_builder_calls_services_with_correct_args(
        self, mock_cache, mock_market_service, mock_db, sample_signal
    ):
        """Verify builder calls services with correct parameters."""
        builder = DecisionContextBuilder(
            cache=mock_cache,
            market_service=mock_market_service,
            db=mock_db,
        )

        await builder.build(sample_signal)

        # Verify wallet metrics called with wallet address
        mock_db.get_wallet_metrics.assert_called_once_with(
            "0x1234567890abcdef1234567890abcdef12345678"
        )

        # Verify market service called with token_id
        mock_market_service.get_liquidity.assert_called_once_with("token456")
        mock_market_service.get_spread.assert_called_once_with("token456")

        # Verify cache methods were called
        mock_cache.get_daily_pnl.assert_called_once()
        mock_cache.get_open_exposure.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_builder_handles_missing_wallet_metrics(
        self, mock_cache, mock_market_service, mock_db, sample_signal
    ):
        """Builder should use defaults when wallet metrics not found."""
        mock_db.get_wallet_metrics = AsyncMock(return_value=None)

        builder = DecisionContextBuilder(
            cache=mock_cache,
            market_service=mock_market_service,
            db=mock_db,
        )

        context = await builder.build(sample_signal)

        # Should use default values
        assert context.wallet_win_rate == 0.0
        assert context.wallet_avg_roi == 0.0
        assert context.wallet_total_trades == 0
        assert context.wallet_recent_performance == 0.0

    @pytest.mark.asyncio
    async def test_context_builder_default_max_daily_loss(
        self, mock_cache, mock_market_service, mock_db, sample_signal
    ):
        """Builder should use default max_daily_loss of 500.0."""
        builder = DecisionContextBuilder(
            cache=mock_cache,
            market_service=mock_market_service,
            db=mock_db,
        )

        context = await builder.build(sample_signal)

        assert context.risk_max_daily_loss == 500.0

    @pytest.mark.asyncio
    async def test_context_builder_result_is_serializable(
        self, mock_cache, mock_market_service, mock_db, sample_signal
    ):
        """Built context should be convertible to dict for AI consumption."""
        builder = DecisionContextBuilder(
            cache=mock_cache,
            market_service=mock_market_service,
            db=mock_db,
        )

        context = await builder.build(sample_signal)
        result = context.to_dict()

        # Verify it's a valid dict structure
        assert isinstance(result, dict)
        assert len(result) == 4
        assert all(isinstance(v, dict) for v in result.values())
