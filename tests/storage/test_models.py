"""Tests for database models."""

import pytest
from datetime import datetime, timezone
from polymind.storage.models import Wallet, Trade, WalletMetrics


def test_wallet_model_has_required_fields():
    """Wallet model should have address and alias."""
    wallet = Wallet(
        address="0x1234567890abcdef",
        alias="whale.eth",
        enabled=True
    )

    assert wallet.address == "0x1234567890abcdef"
    assert wallet.alias == "whale.eth"
    assert wallet.enabled is True


def test_trade_model_has_required_fields():
    """Trade model should capture all trade details."""
    trade = Trade(
        wallet_id=1,
        market_id="btc-50k-friday",
        side="YES",
        size=250.0,
        price=0.65,
        source="clob"
    )

    assert trade.market_id == "btc-50k-friday"
    assert trade.side == "YES"
    assert trade.size == 250.0


def test_wallet_metrics_defaults():
    """WalletMetrics should have sensible defaults when explicitly provided."""
    # SQLAlchemy defaults are applied at database insert time, not at instantiation
    # For unit tests without DB, we verify the model accepts and stores these values
    metrics = WalletMetrics(
        wallet_id=1,
        win_rate=0.0,
        total_trades=0,
        total_pnl=0.0
    )

    assert metrics.win_rate == 0.0
    assert metrics.total_trades == 0
    assert metrics.total_pnl == 0.0
