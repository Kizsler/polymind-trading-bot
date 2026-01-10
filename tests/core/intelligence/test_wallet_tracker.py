"""Tests for wallet performance tracker."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.intelligence.wallet_tracker import WalletTracker
from polymind.core.intelligence.wallet_metrics import WalletMetrics


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
        api.get_wallet_positions = AsyncMock(return_value=[])
        return api

    @pytest.fixture
    def tracker(self, mock_db: MagicMock, mock_data_api: MagicMock) -> WalletTracker:
        """Create wallet tracker with mocks."""
        return WalletTracker(db=mock_db, data_api=mock_data_api)

    def test_calculate_win_rate(self, tracker: WalletTracker) -> None:
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

    def test_calculate_win_rate_empty(self, tracker: WalletTracker) -> None:
        """Test win rate with no trades."""
        win_rate = tracker.calculate_win_rate([])
        assert win_rate == 0.0

    def test_calculate_roi(self, tracker: WalletTracker) -> None:
        """Test ROI calculation."""
        trades = [
            {"size": 100, "profit": 10.0},
            {"size": 100, "profit": -5.0},
            {"size": 200, "profit": 20.0},
        ]
        roi = tracker.calculate_roi(trades)
        # Total profit: 25, Total invested: 400, ROI = 25/400 = 0.0625
        assert roi == pytest.approx(0.0625, rel=0.01)

    def test_calculate_roi_empty(self, tracker: WalletTracker) -> None:
        """Test ROI with no trades."""
        roi = tracker.calculate_roi([])
        assert roi == 0.0

    def test_calculate_timing_score(self, tracker: WalletTracker) -> None:
        """Test timing score calculation."""
        trades = [
            {"entry_time": 100, "price_move_start": 130},  # 30s before move
            {"entry_time": 100, "price_move_start": 115},  # 15s before move
            {"entry_time": 100, "price_move_start": 145},  # 45s before move
        ]
        timing = tracker.calculate_timing_score(trades)
        # Average: 30s, normalized: 30/60 = 0.5
        assert timing == pytest.approx(0.5, rel=0.1)

    def test_calculate_timing_score_empty(self, tracker: WalletTracker) -> None:
        """Test timing score with no trades."""
        timing = tracker.calculate_timing_score([])
        assert timing == 0.0

    def test_calculate_consistency(self, tracker: WalletTracker) -> None:
        """Test consistency calculation."""
        # All same profit = perfect consistency
        trades = [
            {"profit": 10.0},
            {"profit": 10.0},
            {"profit": 10.0},
        ]
        consistency = tracker.calculate_consistency(trades)
        assert consistency == 1.0  # No variance

    def test_calculate_consistency_variable(self, tracker: WalletTracker) -> None:
        """Test consistency with variable returns."""
        trades = [
            {"profit": 50.0},
            {"profit": -30.0},
            {"profit": 100.0},
            {"profit": -50.0},
        ]
        consistency = tracker.calculate_consistency(trades)
        # High variance = lower consistency
        assert 0.0 <= consistency <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_wallet(
        self,
        tracker: WalletTracker,
        mock_data_api: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        """Test full wallet analysis."""
        mock_data_api.get_wallet_positions.return_value = [
            {
                "size": 100,
                "profit": 10.0,
                "entry_time": 100,
                "price_move_start": 120,
            },
            {
                "size": 100,
                "profit": -5.0,
                "entry_time": 100,
                "price_move_start": 110,
            },
            {
                "size": 100,
                "profit": 15.0,
                "entry_time": 100,
                "price_move_start": 130,
            },
        ]

        metrics = await tracker.analyze_wallet("0x1234")

        assert isinstance(metrics, WalletMetrics)
        assert metrics.wallet_address == "0x1234"
        assert metrics.total_trades == 3
        assert 0 <= metrics.win_rate <= 1
        assert 0 <= metrics.confidence_score <= 1
        mock_db.execute.assert_called()  # Saved to DB

    @pytest.mark.asyncio
    async def test_get_wallet_score(
        self,
        tracker: WalletTracker,
        mock_db: MagicMock,
    ) -> None:
        """Test getting cached wallet score."""
        mock_db.fetch_one.return_value = {
            "wallet_address": "0x1234",
            "confidence_score": 0.68,
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
