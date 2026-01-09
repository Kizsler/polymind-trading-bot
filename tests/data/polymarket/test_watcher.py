"""Tests for Polymarket wallet watcher service."""

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.data.models import SignalSource, TradeSignal
from polymind.data.polymarket.watcher import WalletWatcher


@pytest.fixture
def watcher() -> WalletWatcher:
    """Create a wallet watcher instance."""
    return WalletWatcher()


@pytest.fixture
def sample_event() -> dict[str, Any]:
    """Create a sample trade event."""
    return {
        "maker": "0x1234567890ABCDEF1234567890ABCDEF12345678",
        "taker": "0xFEDCBA0987654321FEDCBA0987654321FEDCBA09",
        "market": "btc-50k-friday",
        "asset_id": "token123",
        "side": "BUY",
        "size": "250.0",
        "price": "0.65",
        "timestamp": "1705315800",  # Unix timestamp as string
        "transaction_hash": "0xabc123",
    }


def test_watcher_add_wallet(watcher: WalletWatcher) -> None:
    """Watcher should add wallet to watch list."""
    watcher.add_wallet("0x1234567890ABCDEF1234567890ABCDEF12345678")

    assert "0x1234567890abcdef1234567890abcdef12345678" in watcher.wallets
    assert len(watcher.wallets) == 1


def test_watcher_add_wallet_lowercase(watcher: WalletWatcher) -> None:
    """Watcher should store wallets in lowercase."""
    watcher.add_wallet("0xABCDEF")
    watcher.add_wallet("0xabcdef")

    # Should deduplicate since both are same after lowercase
    assert len(watcher.wallets) == 1
    assert "0xabcdef" in watcher.wallets


def test_watcher_remove_wallet(watcher: WalletWatcher) -> None:
    """Watcher should remove wallet from watch list."""
    watcher.add_wallet("0x1234")
    watcher.add_wallet("0x5678")

    watcher.remove_wallet("0x1234")

    assert "0x1234" not in watcher.wallets
    assert "0x5678" in watcher.wallets


def test_watcher_remove_wallet_case_insensitive(watcher: WalletWatcher) -> None:
    """Watcher should remove wallet regardless of case."""
    watcher.add_wallet("0xABCDEF")

    watcher.remove_wallet("0xabcdef")

    assert len(watcher.wallets) == 0


def test_watcher_remove_nonexistent_wallet(watcher: WalletWatcher) -> None:
    """Watcher should handle removing non-existent wallet gracefully."""
    watcher.remove_wallet("0xNONEXISTENT")

    assert len(watcher.wallets) == 0


def test_watcher_parse_trade_event(sample_event: dict[str, Any]) -> None:
    """Watcher should parse raw event into TradeSignal."""
    signal = WalletWatcher.parse_trade_event(sample_event)

    assert signal.wallet == "0x1234567890abcdef1234567890abcdef12345678"
    assert signal.market_id == "btc-50k-friday"
    assert signal.token_id == "token123"
    assert signal.side == "YES"  # BUY maps to YES
    assert signal.size == 250.0
    assert signal.price == 0.65
    assert signal.source == SignalSource.CLOB
    assert signal.tx_hash == "0xabc123"


def test_watcher_parse_trade_event_sell_to_no(sample_event: dict[str, Any]) -> None:
    """Watcher should map SELL side to NO."""
    sample_event["side"] = "SELL"

    signal = WalletWatcher.parse_trade_event(sample_event)

    assert signal.side == "NO"


def test_watcher_parse_trade_event_timestamp_string() -> None:
    """Watcher should parse timestamp from string."""
    event = {
        "maker": "0x1234",
        "market": "test-market",
        "asset_id": "token456",
        "side": "BUY",
        "size": "100",
        "price": "0.5",
        "timestamp": "1705315800",  # String timestamp
        "transaction_hash": "0xhash",
    }

    signal = WalletWatcher.parse_trade_event(event)

    assert isinstance(signal.timestamp, datetime)


def test_watcher_parse_trade_event_timestamp_int() -> None:
    """Watcher should parse timestamp from integer."""
    event = {
        "maker": "0x1234",
        "market": "test-market",
        "asset_id": "token456",
        "side": "BUY",
        "size": "100",
        "price": "0.5",
        "timestamp": 1705315800,  # Integer timestamp
        "transaction_hash": "0xhash",
    }

    signal = WalletWatcher.parse_trade_event(event)

    assert isinstance(signal.timestamp, datetime)


def test_watcher_parse_trade_event_uses_taker_when_no_maker() -> None:
    """Watcher should use taker address when maker is not present."""
    event = {
        "taker": "0xTAKER",
        "market": "test-market",
        "asset_id": "token456",
        "side": "BUY",
        "size": "100",
        "price": "0.5",
        "timestamp": 1705315800,
        "transaction_hash": "0xhash",
    }

    signal = WalletWatcher.parse_trade_event(event)

    assert signal.wallet == "0xtaker"


def test_watcher_filters_unwatched_wallets(
    watcher: WalletWatcher,
    sample_event: dict[str, Any],
) -> None:
    """Watcher should return None for unwatched wallets."""
    # Do not add any wallets

    result = watcher.process_event(sample_event)

    assert result is None


def test_watcher_processes_watched_wallets(
    watcher: WalletWatcher,
    sample_event: dict[str, Any],
) -> None:
    """Watcher should return TradeSignal for watched wallets."""
    watcher.add_wallet("0x1234567890ABCDEF1234567890ABCDEF12345678")

    result = watcher.process_event(sample_event)

    assert result is not None
    assert isinstance(result, TradeSignal)
    assert result.wallet == "0x1234567890abcdef1234567890abcdef12345678"


def test_watcher_calls_callback_for_watched_wallet(
    watcher: WalletWatcher,
    sample_event: dict[str, Any],
) -> None:
    """Watcher should call on_signal callback when processing watched wallet."""
    callback = MagicMock()
    watcher_with_callback = WalletWatcher(on_signal=callback)
    watcher_with_callback.add_wallet("0x1234567890ABCDEF1234567890ABCDEF12345678")

    result = watcher_with_callback.process_event(sample_event)

    callback.assert_called_once_with(result)


def test_watcher_does_not_call_callback_for_unwatched_wallet(
    watcher: WalletWatcher,
    sample_event: dict[str, Any],
) -> None:
    """Watcher should not call on_signal callback for unwatched wallets."""
    callback = MagicMock()
    watcher_with_callback = WalletWatcher(on_signal=callback)
    # Do not add wallet

    watcher_with_callback.process_event(sample_event)

    callback.assert_not_called()


def test_watcher_wallets_property_returns_copy(watcher: WalletWatcher) -> None:
    """Watcher wallets property should return a copy of the set."""
    watcher.add_wallet("0x1234")

    wallets = watcher.wallets
    wallets.add("0x5678")

    # Original should not be modified
    assert "0x5678" not in watcher.wallets


@pytest.mark.asyncio
async def test_watcher_start_sets_running(watcher: WalletWatcher) -> None:
    """Watcher start should set _running to True."""
    import asyncio

    # Start and immediately stop
    task = asyncio.create_task(watcher.start())
    await asyncio.sleep(0.1)  # Let it run briefly
    await watcher.stop()
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_watcher_stop_sets_not_running(watcher: WalletWatcher) -> None:
    """Watcher stop should set _running to False."""
    import asyncio

    task = asyncio.create_task(watcher.start())
    await asyncio.sleep(0.1)
    await watcher.stop()

    assert watcher._running is False

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_watcher_polls_data_api() -> None:
    """WalletWatcher should poll Data API for trades."""
    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(return_value=[
        {
            "market": "0x123",
            "asset_id": "token1",
            "side": "BUY",
            "size": "100",
            "price": "0.55",
            "timestamp": "1704067200",
            "transaction_hash": "0xabc",
            "maker": "0xwallet123",
        },
    ])

    signals_received: list[TradeSignal] = []

    def on_signal(signal: TradeSignal) -> None:
        signals_received.append(signal)

    watcher = WalletWatcher(
        data_api=mock_data_api, on_signal=on_signal, poll_interval=0.1
    )
    watcher.add_wallet("0xwallet123")

    # Start watcher in background
    task = asyncio.create_task(watcher.start())

    # Let it poll once
    await asyncio.sleep(0.2)
    await watcher.stop()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Should have received the trade
    assert len(signals_received) >= 1
    assert signals_received[0].wallet == "0xwallet123"


@pytest.mark.asyncio
async def test_watcher_deduplicates_trades() -> None:
    """WalletWatcher should not emit duplicate trades."""
    # Same trade returned twice
    trade = {
        "market": "0x123",
        "asset_id": "token1",
        "side": "BUY",
        "size": "100",
        "price": "0.55",
        "timestamp": "1704067200",
        "transaction_hash": "0xabc",
        "maker": "0xwallet123",
    }

    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(return_value=[trade])

    signals_received: list[TradeSignal] = []
    watcher = WalletWatcher(
        data_api=mock_data_api,
        on_signal=lambda s: signals_received.append(s),
        poll_interval=0.1,
    )
    watcher.add_wallet("0xwallet123")

    task = asyncio.create_task(watcher.start())
    await asyncio.sleep(0.35)  # Allow 3+ polls
    await watcher.stop()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Should only emit once despite multiple polls
    assert len(signals_received) == 1


@pytest.mark.asyncio
async def test_watcher_handles_api_errors() -> None:
    """WalletWatcher should handle API errors gracefully."""
    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(
        side_effect=Exception("API error")
    )

    watcher = WalletWatcher(data_api=mock_data_api, poll_interval=0.1)
    watcher.add_wallet("0xwallet123")

    task = asyncio.create_task(watcher.start())
    await asyncio.sleep(0.15)  # Let it try to poll
    await watcher.stop()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Should not crash - just continue
    assert True


@pytest.mark.asyncio
async def test_watcher_tracks_last_timestamp_per_wallet() -> None:
    """WalletWatcher should track last timestamp per wallet for incremental polling."""
    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(return_value=[
        {
            "market": "0x123",
            "asset_id": "token1",
            "side": "BUY",
            "size": "100",
            "price": "0.55",
            "timestamp": "1704067200",
            "transaction_hash": "0xabc",
            "maker": "0xwallet123",
        },
    ])

    watcher = WalletWatcher(data_api=mock_data_api, poll_interval=0.1)
    watcher.add_wallet("0xwallet123")

    task = asyncio.create_task(watcher.start())
    await asyncio.sleep(0.25)  # Let it poll twice
    await watcher.stop()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Should have updated last timestamp
    assert "0xwallet123" in watcher._last_timestamp
    assert watcher._last_timestamp["0xwallet123"] == 1704067200


@pytest.mark.asyncio
async def test_watcher_passes_since_timestamp_to_api() -> None:
    """WalletWatcher should pass since_timestamp to API after first poll."""
    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(return_value=[
        {
            "market": "0x123",
            "asset_id": "token1",
            "side": "BUY",
            "size": "100",
            "price": "0.55",
            "timestamp": "1704067200",
            "transaction_hash": "0xabc",
            "maker": "0xwallet123",
        },
    ])

    watcher = WalletWatcher(data_api=mock_data_api, poll_interval=0.1)
    watcher.add_wallet("0xwallet123")

    task = asyncio.create_task(watcher.start())
    await asyncio.sleep(0.25)  # Let it poll twice
    await watcher.stop()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Check the API was called with since_timestamp on second call
    calls = mock_data_api.get_wallet_trades.call_args_list
    assert len(calls) >= 2
    # First call should have no since_timestamp
    assert calls[0].kwargs.get("since_timestamp") is None
    # Second call should have since_timestamp set
    assert calls[1].kwargs.get("since_timestamp") == 1704067200
