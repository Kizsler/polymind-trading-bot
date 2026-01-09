"""Signal queue with deduplication."""

import asyncio
import time
from collections import OrderedDict

from polymind.data.models import TradeSignal


class SignalQueue:
    """Async queue for trade signals with deduplication.

    Uses a time-based deduplication window to prevent the same trade
    signal from being processed multiple times, even when detected
    from different sources (CLOB vs blockchain).
    """

    def __init__(
        self,
        max_size: int = 1000,
        dedup_window_seconds: float = 300,
    ) -> None:
        """Initialize the signal queue.

        Args:
            max_size: Maximum number of signals in queue.
            dedup_window_seconds: Time window for deduplication (default 5 minutes).
        """
        self._queue: asyncio.Queue[TradeSignal] = asyncio.Queue(maxsize=max_size)
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._dedup_window = dedup_window_seconds
        self._lock = asyncio.Lock()

    @property
    def size(self) -> int:
        """Return current queue size."""
        return self._queue.qsize()

    async def put(self, signal: TradeSignal) -> bool:
        """Add a signal to the queue if not a duplicate.

        Args:
            signal: The trade signal to add.

        Returns:
            True if added, False if duplicate.
        """
        async with self._lock:
            self._clean_old_entries()

            dedup_id = signal.dedup_id
            if dedup_id in self._seen:
                return False

            self._seen[dedup_id] = time.monotonic()
            await self._queue.put(signal)
            return True

    async def get(self, timeout: float | None = None) -> TradeSignal:
        """Get the next signal from the queue.

        Args:
            timeout: Optional timeout in seconds.

        Returns:
            The next trade signal.

        Raises:
            asyncio.TimeoutError: If timeout is specified and no signal
                is available within the timeout period.
        """
        if timeout is not None:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        return await self._queue.get()

    def get_nowait(self) -> TradeSignal | None:
        """Get signal without waiting.

        Returns:
            The next signal or None if queue is empty.
        """
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def _clean_old_entries(self) -> None:
        """Remove entries older than dedup_window_seconds."""
        cutoff = time.monotonic() - self._dedup_window
        # Remove old entries from the front of the OrderedDict
        while self._seen:
            oldest_key = next(iter(self._seen))
            if self._seen[oldest_key] < cutoff:
                del self._seen[oldest_key]
            else:
                break

    async def clear(self) -> None:
        """Clear the queue and seen set."""
        async with self._lock:
            # Drain the queue
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self._seen.clear()
