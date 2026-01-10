"""Tests for wallet metrics model."""

import pytest
from datetime import datetime, timezone

from polymind.core.intelligence.wallet_metrics import WalletMetrics


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
        # confidence = 0.6*0.3 + (0.1/0.5)*0.3 + 0.7*0.2 + 0.8*0.2
        # = 0.18 + 0.06 + 0.14 + 0.16 = 0.54
        assert metrics.confidence_score == pytest.approx(0.54, rel=0.01)

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
        # 0.6*0.5 + (0.1/0.5)*0.2 + 0.7*0.2 + 0.8*0.1
        # = 0.3 + 0.04 + 0.14 + 0.08 = 0.56
        assert score == pytest.approx(0.56, rel=0.01)

    def test_roi_capped_at_max(self) -> None:
        """Test ROI is capped for normalization."""
        metrics = WalletMetrics(
            wallet_address="0x1234",
            win_rate=0.5,
            roi=1.0,  # 100% ROI - way above cap
            timing_score=0.5,
            consistency=0.5,
        )
        # ROI should be capped at 0.5 (50%) for normalization
        # so normalized ROI = 1.0, contributing max weight
        score = metrics.confidence_score
        assert score > 0.5  # Should be higher due to maxed ROI

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        metrics = WalletMetrics(
            wallet_address="0x1234",
            win_rate=0.6,
            roi=0.1,
            timing_score=0.7,
            consistency=0.8,
            total_trades=100,
        )
        data = metrics.to_dict()
        assert data["wallet_address"] == "0x1234"
        assert data["win_rate"] == 0.6
        assert data["total_trades"] == 100
        assert "confidence_score" in data
        assert "updated_at" in data
