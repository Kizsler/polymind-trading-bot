"""Integration tests for data layer components."""

from datetime import UTC, datetime

import pytest

from polymind.data import SignalQueue, SignalSource, TradeSignal
from polymind.data.polymarket import MarketDataService, PolymarketClient, WalletWatcher


def test_polymarket_client_initializes() -> None:
    """PolymarketClient() creates without error."""
    client = PolymarketClient()
    assert client is not None
    assert client._client is not None


def test_wallet_watcher_initializes() -> None:
    """WalletWatcher(client=client) creates without error."""
    client = PolymarketClient()
    watcher = WalletWatcher(client=client)
    assert watcher is not None
    assert watcher._client is client


def test_market_data_service_initializes() -> None:
    """MarketDataService(client=client) creates without error."""
    client = PolymarketClient()
    service = MarketDataService(client=client)
    assert service is not None
    assert service._client is client


@pytest.mark.asyncio
async def test_signal_queue_full_flow() -> None:
    """Tests put/get flow with SignalQueue."""
    queue = SignalQueue(max_size=10, dedup_window_seconds=60)

    # Create a test signal
    signal = TradeSignal(
        wallet="0x1234567890abcdef1234567890abcdef12345678",
        market_id="test-market",
        token_id="test-token",
        side="YES",
        size=100.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc123",
    )

    # Put should succeed
    result = await queue.put(signal)
    assert result is True
    assert queue.size == 1

    # Duplicate put should fail (deduplication)
    result = await queue.put(signal)
    assert result is False
    assert queue.size == 1

    # Get should return the signal
    retrieved = await queue.get(timeout=1.0)
    assert retrieved.wallet == signal.wallet
    assert retrieved.market_id == signal.market_id
    assert retrieved.side == signal.side
    assert retrieved.size == signal.size


def test_watcher_processes_signals() -> None:
    """WalletWatcher processes events for watched wallets."""
    signals_received: list[TradeSignal] = []

    def signal_callback(signal: TradeSignal) -> None:
        signals_received.append(signal)

    client = PolymarketClient()
    watcher = WalletWatcher(client=client, on_signal=signal_callback)

    # Add a wallet to watch
    test_wallet = "0x1234567890ABCDEF1234567890abcdef12345678"
    watcher.add_wallet(test_wallet)

    # Create a mock trade event for watched wallet
    event = {
        "maker": test_wallet,
        "market": "test-market-id",
        "asset_id": "test-token-id",
        "side": "BUY",
        "size": "50.0",
        "price": "0.75",
        "timestamp": "1704067200",
        "transaction_hash": "0xdef456",
    }

    # Process event - should produce a signal
    signal = watcher.process_event(event)
    assert signal is not None
    assert signal.wallet == test_wallet.lower()
    assert signal.side == "YES"  # BUY maps to YES
    assert signal.size == 50.0
    assert signal.price == 0.75

    # Callback should have been called
    assert len(signals_received) == 1
    assert signals_received[0] == signal

    # Process event for non-watched wallet - should return None
    other_event = {
        "maker": "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
        "market": "test-market-id",
        "asset_id": "test-token-id",
        "side": "SELL",
        "size": "25.0",
        "price": "0.30",
        "timestamp": "1704067300",
        "transaction_hash": "0xghi789",
    }

    signal = watcher.process_event(other_event)
    assert signal is None
    # Callback should NOT have been called again
    assert len(signals_received) == 1
