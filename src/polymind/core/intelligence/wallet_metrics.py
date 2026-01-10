"""Wallet performance metrics model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize metrics to dictionary."""
        return {
            "wallet_address": self.wallet_address,
            "win_rate": self.win_rate,
            "roi": self.roi,
            "timing_score": self.timing_score,
            "consistency": self.consistency,
            "confidence_score": self.confidence_score,
            "total_trades": self.total_trades,
            "updated_at": self.updated_at.isoformat(),
        }
