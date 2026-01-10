"""Wallet intelligence and performance tracking."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from polymind.core.intelligence.wallet_metrics import WalletMetrics
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

        # Fetch historical positions/trades from Data API
        trades = await self.data_api.get_wallet_positions(wallet_address)

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
