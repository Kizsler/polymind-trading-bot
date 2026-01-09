"""Integration tests for Polymarket API clients."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.data.models import SignalSource, TradeSignal
from polymind.data.polymarket.gamma import GammaClient
from polymind.data.polymarket.data_api import DataAPIClient
from polymind.data.polymarket.watcher import WalletWatcher


# Test client initialization


def test_gamma_client_initializes() -> None:
    """GammaClient should initialize with correct defaults."""
    client = GammaClient()
    assert client.base_url == "https://gamma-api.polymarket.com"


def test_data_api_client_initializes() -> None:
    """DataAPIClient should initialize with correct defaults."""
    client = DataAPIClient()
    assert client.base_url == "https://data-api.polymarket.com"


def test_wallet_watcher_initializes() -> None:
    """WalletWatcher should initialize with Data API client."""
    data_api = DataAPIClient()
    watcher = WalletWatcher(data_api=data_api, poll_interval=1.0)
    assert watcher._data_api is data_api
    assert watcher._poll_interval == 1.0


# Test trade signal parsing


def test_watcher_parses_trade_to_signal() -> None:
    """WalletWatcher should parse API response to TradeSignal."""
    raw_trade = {
        "market": "0xmarket123",
        "asset_id": "token456",
        "side": "BUY",
        "size": "100.5",
        "price": "0.65",
        "timestamp": "1704067200",
        "transaction_hash": "0xtxhash789",
        "maker": "0xWallet123",  # Mixed case
    }

    signal = WalletWatcher.parse_trade_event(raw_trade)

    assert signal.wallet == "0xwallet123"  # Lowercased
    assert signal.market_id == "0xmarket123"
    assert signal.token_id == "token456"
    assert signal.side == "YES"  # BUY -> YES
    assert signal.size == 100.5
    assert signal.price == 0.65
    assert signal.source == SignalSource.CLOB
    assert signal.tx_hash == "0xtxhash789"


def test_watcher_parses_sell_as_no() -> None:
    """WalletWatcher should parse SELL side as NO."""
    raw_trade = {
        "market": "0xmarket",
        "asset_id": "token",
        "side": "SELL",
        "size": "50",
        "price": "0.35",
        "timestamp": "1704067200",
        "transaction_hash": "0xhash",
        "taker": "0xwallet",
    }

    signal = WalletWatcher.parse_trade_event(raw_trade)
    assert signal.side == "NO"


# Test full flow with mocks


@pytest.mark.asyncio
async def test_full_flow_with_mocked_apis() -> None:
    """Test the full flow from API response to signal emission."""
    # Create mock Data API
    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(return_value=[
        {
            "market": "0xelection2024",
            "asset_id": "yes_token",
            "side": "BUY",
            "size": "500",
            "price": "0.55",
            "timestamp": "1704067200",
            "transaction_hash": "0xabc123",
            "maker": "0xsmarttrader",
        },
    ])

    # Track emitted signals
    emitted_signals: list[TradeSignal] = []

    def on_signal(signal: TradeSignal) -> None:
        emitted_signals.append(signal)

    # Create watcher with mock
    watcher = WalletWatcher(
        data_api=mock_data_api,
        on_signal=on_signal,
        poll_interval=0.1,
    )
    watcher.add_wallet("0xsmarttrader")

    # Poll once
    signals = await watcher._poll_wallet("0xsmarttrader")

    # Verify signal was emitted
    assert len(signals) == 1
    assert len(emitted_signals) == 1

    signal = emitted_signals[0]
    assert signal.wallet == "0xsmarttrader"
    assert signal.market_id == "0xelection2024"
    assert signal.side == "YES"
    assert signal.size == 500.0


@pytest.mark.asyncio
async def test_deduplication_across_polls() -> None:
    """Test that the same trade is not emitted twice."""
    trade = {
        "market": "0xmarket",
        "asset_id": "token",
        "side": "BUY",
        "size": "100",
        "price": "0.50",
        "timestamp": "1704067200",
        "transaction_hash": "0xhash",
        "maker": "0xtrader",
    }

    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(return_value=[trade])

    emitted_signals: list[TradeSignal] = []

    watcher = WalletWatcher(
        data_api=mock_data_api,
        on_signal=lambda s: emitted_signals.append(s),
        poll_interval=0.1,
    )
    watcher.add_wallet("0xtrader")

    # Poll twice
    await watcher._poll_wallet("0xtrader")
    await watcher._poll_wallet("0xtrader")

    # Should only emit once
    assert len(emitted_signals) == 1


@pytest.mark.asyncio
async def test_multiple_wallets() -> None:
    """Test watching multiple wallets."""
    mock_data_api = AsyncMock()

    # Return different trades for different wallets
    async def mock_trades(wallet: str, **kwargs):
        if "trader1" in wallet:
            return [{"market": "m1", "asset_id": "t1", "side": "BUY",
                    "size": "100", "price": "0.5", "timestamp": "1704067200",
                    "transaction_hash": "0x1", "maker": wallet}]
        elif "trader2" in wallet:
            return [{"market": "m2", "asset_id": "t2", "side": "SELL",
                    "size": "200", "price": "0.6", "timestamp": "1704067201",
                    "transaction_hash": "0x2", "maker": wallet}]
        return []

    mock_data_api.get_wallet_trades = AsyncMock(side_effect=mock_trades)

    emitted_signals: list[TradeSignal] = []

    watcher = WalletWatcher(
        data_api=mock_data_api,
        on_signal=lambda s: emitted_signals.append(s),
        poll_interval=0.1,
    )
    watcher.add_wallet("0xtrader1")
    watcher.add_wallet("0xtrader2")

    # Poll both wallets
    await watcher._poll_wallet("0xtrader1")
    await watcher._poll_wallet("0xtrader2")

    # Should have signals from both
    assert len(emitted_signals) == 2
    wallets = {s.wallet for s in emitted_signals}
    assert "0xtrader1" in wallets
    assert "0xtrader2" in wallets


# Test error handling


@pytest.mark.asyncio
async def test_api_error_does_not_crash_watcher() -> None:
    """WalletWatcher should handle API errors gracefully."""
    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(
        side_effect=Exception("Network error")
    )

    watcher = WalletWatcher(
        data_api=mock_data_api,
        poll_interval=0.1,
    )
    watcher.add_wallet("0xtrader")

    # Should not raise
    signals = await watcher._poll_wallet("0xtrader")
    assert signals == []


@pytest.mark.asyncio
async def test_watcher_without_data_api() -> None:
    """WalletWatcher should handle missing Data API gracefully."""
    watcher = WalletWatcher(poll_interval=0.1)
    watcher.add_wallet("0xtrader")

    # Should return empty list, not crash
    signals = await watcher._poll_wallet("0xtrader")
    assert signals == []
