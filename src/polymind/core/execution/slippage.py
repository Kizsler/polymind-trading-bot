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
