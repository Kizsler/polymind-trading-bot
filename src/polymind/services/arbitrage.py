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
        polymarket_client: Polymarket CLOB client (sync).
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

    def __post_init__(self) -> None:
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

        # Fetch Polymarket price (sync client wrapped in thread)
        poly_price = await self._get_polymarket_price(mapping.polymarket_id)
        if poly_price is None:
            return None

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

    async def _get_polymarket_price(self, market_id: str) -> float | None:
        """Get Polymarket price for a market.

        Args:
            market_id: Polymarket market/token ID.

        Returns:
            Price (0-1) or None if not found.
        """
        try:
            # Use sync client wrapped in thread
            price = await asyncio.to_thread(
                self.polymarket_client.get_midpoint,
                market_id,
            )
            return price if price > 0 else None
        except Exception as e:
            logger.warning("Failed to get Polymarket price for {}: {}", market_id, str(e))
            return None

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
            token_id=opp["polymarket_id"],  # Token ID may differ in practice
            side=side,
            size=size,
            price=price,
            source=SignalSource.ARBITRAGE,
            timestamp=datetime.now(),
            tx_hash="",
        )
