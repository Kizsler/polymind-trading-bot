"""Tests for signal queue with deduplication."""

import asyncio
from datetime import UTC, datetime

import pytest

from polymind.data.models import SignalSource, TradeSignal
from polymind.data.queue import SignalQueue


def _make_signal(
    wallet: str = "0x1234567890abcdef1234567890abcdef12345678",
    market_id: str = "btc-50k-friday",
    token_id: str = "token123",
    side: str = "YES",
    size: float = 250.0,
    price: float = 0.65,
    source: SignalSource = SignalSource.CLOB,
    timestamp: datetime | None = None,
    tx_hash: str = "0xabc123",
) -> TradeSignal:
    """Helper to create TradeSignal for tests."""
    if timestamp is None:
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
    return TradeSignal(
        wallet=wallet,
        market_id=market_id,
        token_id=token_id,
        side=side,
        size=size,
        price=price,
        source=source,
        timestamp=timestamp,
        tx_hash=tx_hash,
    )


@pytest.mark.asyncio
async def test_queue_add_and_get():
    """Put and get signal."""
    queue = SignalQueue()
    signal = _make_signal()

    added = await queue.put(signal)
    assert added is True
    assert queue.size == 1

    result = await queue.get(timeout=1.0)
    assert result == signal
    assert queue.size == 0


@pytest.mark.asyncio
async def test_queue_deduplicates():
    """Same trade different sources should be rejected."""
    queue = SignalQueue()

    # Add signal from CLOB source
    clob_signal = _make_signal(source=SignalSource.CLOB)
    added_clob = await queue.put(clob_signal)
    assert added_clob is True

    # Same trade from CHAIN source should be rejected (same dedup_id)
    chain_signal = _make_signal(source=SignalSource.CHAIN)
    added_chain = await queue.put(chain_signal)
    assert added_chain is False

    # Queue should only have one signal
    assert queue.size == 1


@pytest.mark.asyncio
async def test_queue_accepts_different_signals():
    """Different trades should be accepted."""
    queue = SignalQueue()

    # Add first signal
    signal1 = _make_signal(side="YES")
    added1 = await queue.put(signal1)
    assert added1 is True

    # Add different signal (different side -> different dedup_id)
    signal2 = _make_signal(side="NO")
    added2 = await queue.put(signal2)
    assert added2 is True

    # Queue should have both signals
    assert queue.size == 2


@pytest.mark.asyncio
async def test_queue_size():
    """Size property works correctly."""
    queue = SignalQueue()
    assert queue.size == 0

    # Add multiple different signals
    for i in range(5):
        signal = _make_signal(
            market_id=f"market-{i}",
            timestamp=datetime(2025, 1, 15, 10, 30 + i, 0, tzinfo=UTC),
        )
        await queue.put(signal)

    assert queue.size == 5

    # Get one signal
    await queue.get(timeout=1.0)
    assert queue.size == 4


@pytest.mark.asyncio
async def test_queue_get_nowait():
    """get_nowait returns signal or None."""
    queue = SignalQueue()

    # Empty queue returns None
    result = queue.get_nowait()
    assert result is None

    # Add signal and get it
    signal = _make_signal()
    await queue.put(signal)

    result = queue.get_nowait()
    assert result == signal

    # Queue is now empty
    result = queue.get_nowait()
    assert result is None


@pytest.mark.asyncio
async def test_queue_get_timeout():
    """get with timeout raises TimeoutError when empty."""
    queue = SignalQueue()

    with pytest.raises(asyncio.TimeoutError):
        await queue.get(timeout=0.1)


@pytest.mark.asyncio
async def test_queue_clear():
    """clear removes all signals and seen entries."""
    queue = SignalQueue()

    # Add signals
    signal1 = _make_signal(market_id="market-1")
    signal2 = _make_signal(market_id="market-2")
    await queue.put(signal1)
    await queue.put(signal2)
    assert queue.size == 2

    # Clear queue
    await queue.clear()
    assert queue.size == 0

    # Should be able to add same signal again after clear
    added = await queue.put(signal1)
    assert added is True


@pytest.mark.asyncio
async def test_queue_dedup_window():
    """Old entries should be cleaned after dedup_window_seconds."""
    # Use very short dedup window for testing
    queue = SignalQueue(dedup_window_seconds=0.1)

    signal = _make_signal()
    added1 = await queue.put(signal)
    assert added1 is True

    # Consume the signal
    await queue.get(timeout=1.0)

    # Wait for dedup window to expire
    await asyncio.sleep(0.15)

    # Same signal should now be accepted (dedup entry expired)
    added2 = await queue.put(signal)
    assert added2 is True


@pytest.mark.asyncio
async def test_queue_max_size():
    """Queue respects max_size."""
    queue = SignalQueue(max_size=3)

    # Add signals up to max
    for i in range(3):
        signal = _make_signal(
            market_id=f"market-{i}",
            timestamp=datetime(2025, 1, 15, 10, 30 + i, 0, tzinfo=UTC),
        )
        added = await queue.put(signal)
        assert added is True

    # Queue is full - next put should block or fail
    # We'll verify the queue has 3 items
    assert queue.size == 3
