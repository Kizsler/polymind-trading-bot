"""Tests for WalletMonitorService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.data.models import TradeSignal
from polymind.services.monitor import WalletMonitorService


def test_monitor_service_initializes() -> None:
    """WalletMonitorService should initialize with dependencies."""
    mock_db = MagicMock()
    mock_data_api = MagicMock()

    service = WalletMonitorService(db=mock_db, data_api=mock_data_api)

    assert service._db is mock_db
    assert service._data_api is mock_data_api


@pytest.mark.asyncio
async def test_load_wallets_from_database() -> None:
    """Service should load enabled wallets from database."""
    mock_db = AsyncMock()
    mock_wallet = MagicMock()
    mock_wallet.address = "0xtrader1"
    mock_wallet.enabled = True
    mock_wallet.alias = None
    mock_db.get_all_wallets = AsyncMock(return_value=[mock_wallet])

    service = WalletMonitorService(db=mock_db, data_api=MagicMock())
    await service.load_wallets()

    assert "0xtrader1" in service.watched_wallets


@pytest.mark.asyncio
async def test_ignores_disabled_wallets() -> None:
    """Service should ignore disabled wallets."""
    mock_db = AsyncMock()

    enabled_wallet = MagicMock()
    enabled_wallet.address = "0xenabled"
    enabled_wallet.enabled = True
    enabled_wallet.alias = None

    disabled_wallet = MagicMock()
    disabled_wallet.address = "0xdisabled"
    disabled_wallet.enabled = False
    disabled_wallet.alias = None

    mock_db.get_all_wallets = AsyncMock(return_value=[enabled_wallet, disabled_wallet])

    service = WalletMonitorService(db=mock_db, data_api=MagicMock())
    await service.load_wallets()

    assert "0xenabled" in service.watched_wallets
    assert "0xdisabled" not in service.watched_wallets


@pytest.mark.asyncio
async def test_on_signal_callback_invoked() -> None:
    """Service should invoke callback when signal detected."""
    mock_db = AsyncMock()
    mock_db.get_all_wallets = AsyncMock(return_value=[])

    received_signals = []
    async def on_signal(signal: TradeSignal) -> None:
        received_signals.append(signal)

    service = WalletMonitorService(
        db=mock_db,
        data_api=MagicMock(),
        on_signal=on_signal
    )

    # Create a fake signal with all required attributes
    mock_signal = MagicMock(spec=TradeSignal)
    mock_signal.wallet = "0xtest"
    mock_signal.market_id = "test-market-12345"
    mock_signal.side = "YES"
    mock_signal.size = 100.0

    # Invoke internal handler
    await service._handle_signal(mock_signal)

    assert len(received_signals) == 1


@pytest.mark.asyncio
async def test_start_begins_watching() -> None:
    """Service start should begin wallet watching."""
    mock_db = AsyncMock()
    mock_wallet = MagicMock()
    mock_wallet.address = "0xtrader"
    mock_wallet.enabled = True
    mock_wallet.alias = None
    mock_db.get_all_wallets = AsyncMock(return_value=[mock_wallet])

    mock_data_api = AsyncMock()
    mock_data_api.get_wallet_trades = AsyncMock(return_value=[])

    service = WalletMonitorService(db=mock_db, data_api=mock_data_api, poll_interval=0.1)

    # Start in background
    task = asyncio.create_task(service.start())
    await asyncio.sleep(0.15)
    await service.stop()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Should have polled for trades
    mock_data_api.get_wallet_trades.assert_called()


@pytest.mark.asyncio
async def test_refresh_wallets() -> None:
    """Service should support refreshing wallet list."""
    mock_db = AsyncMock()

    # Initially one wallet
    wallet1 = MagicMock()
    wallet1.address = "0xwallet1"
    wallet1.enabled = True
    wallet1.alias = None
    mock_db.get_all_wallets = AsyncMock(return_value=[wallet1])

    service = WalletMonitorService(db=mock_db, data_api=MagicMock())
    await service.load_wallets()

    assert "0xwallet1" in service.watched_wallets

    # Now add another wallet
    wallet2 = MagicMock()
    wallet2.address = "0xwallet2"
    wallet2.enabled = True
    wallet2.alias = None
    mock_db.get_all_wallets = AsyncMock(return_value=[wallet1, wallet2])

    await service.refresh_wallets()

    assert "0xwallet1" in service.watched_wallets
    assert "0xwallet2" in service.watched_wallets


@pytest.mark.asyncio
async def test_stop_stops_watcher() -> None:
    """Service stop should stop the watcher."""
    service = WalletMonitorService(db=MagicMock(), data_api=MagicMock())

    # Manually set running state
    service._running = True

    await service.stop()

    assert service._running is False


@pytest.mark.asyncio
async def test_get_wallet_alias() -> None:
    """Service should return wallet alias when available."""
    mock_db = AsyncMock()

    wallet = MagicMock()
    wallet.address = "0xWalletWithAlias"
    wallet.enabled = True
    wallet.alias = "TopTrader"
    mock_db.get_all_wallets = AsyncMock(return_value=[wallet])

    service = WalletMonitorService(db=mock_db, data_api=MagicMock())
    await service.load_wallets()

    assert service.get_wallet_alias("0xwalletwithalias") == "TopTrader"
    assert service.get_wallet_alias("0xunknown") is None


@pytest.mark.asyncio
async def test_is_running_property() -> None:
    """Service should expose running state."""
    service = WalletMonitorService(db=MagicMock(), data_api=MagicMock())

    assert service.is_running is False

    service._running = True
    assert service.is_running is True
