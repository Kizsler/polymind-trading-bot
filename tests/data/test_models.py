"""Tests for trade signal data models."""

from datetime import UTC, datetime

from polymind.data.models import SignalSource, TradeSignal


def test_trade_signal_from_dict():
    """Create TradeSignal from dictionary."""
    data = {
        "wallet": "0x1234567890abcdef1234567890abcdef12345678",
        "market_id": "btc-50k-friday",
        "token_id": "token123",
        "side": "YES",
        "size": 250.0,
        "price": 0.65,
        "source": "clob",
        "timestamp": "2025-01-15T10:30:00+00:00",
        "tx_hash": "0xabc123",
    }

    signal = TradeSignal.from_dict(data)

    assert signal.wallet == "0x1234567890abcdef1234567890abcdef12345678"
    assert signal.market_id == "btc-50k-friday"
    assert signal.token_id == "token123"
    assert signal.side == "YES"
    assert signal.size == 250.0
    assert signal.price == 0.65
    assert signal.source == SignalSource.CLOB
    assert signal.timestamp == datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
    assert signal.tx_hash == "0xabc123"


def test_trade_signal_unique_id():
    """Same trade from CLOB and CHAIN sources should have same dedup_id."""
    base_data = {
        "wallet": "0x1234567890abcdef1234567890abcdef12345678",
        "market_id": "btc-50k-friday",
        "token_id": "token123",
        "side": "YES",
        "size": 250.0,
        "price": 0.65,
        "timestamp": "2025-01-15T10:30:00+00:00",
        "tx_hash": "0xabc123",
    }

    clob_data = {**base_data, "source": "clob"}
    chain_data = {**base_data, "source": "chain"}

    clob_signal = TradeSignal.from_dict(clob_data)
    chain_signal = TradeSignal.from_dict(chain_data)

    # Same trade from different sources should deduplicate
    assert clob_signal.dedup_id == chain_signal.dedup_id


def test_trade_signal_different_trades_have_different_ids():
    """Different trades (e.g., different side) should have different dedup_id."""
    base_data = {
        "wallet": "0x1234567890abcdef1234567890abcdef12345678",
        "market_id": "btc-50k-friday",
        "token_id": "token123",
        "size": 250.0,
        "price": 0.65,
        "source": "clob",
        "timestamp": "2025-01-15T10:30:00+00:00",
        "tx_hash": "0xabc123",
    }

    yes_data = {**base_data, "side": "YES"}
    no_data = {**base_data, "side": "NO"}

    yes_signal = TradeSignal.from_dict(yes_data)
    no_signal = TradeSignal.from_dict(no_data)

    # Different sides should have different dedup_id
    assert yes_signal.dedup_id != no_signal.dedup_id


def test_trade_signal_to_dict():
    """TradeSignal should convert to dictionary."""
    signal = TradeSignal(
        wallet="0x1234567890abcdef1234567890abcdef12345678",
        market_id="btc-50k-friday",
        token_id="token123",
        side="YES",
        size=250.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
        tx_hash="0xabc123",
    )

    data = signal.to_dict()

    assert data["wallet"] == "0x1234567890abcdef1234567890abcdef12345678"
    assert data["market_id"] == "btc-50k-friday"
    assert data["token_id"] == "token123"
    assert data["side"] == "YES"
    assert data["size"] == 250.0
    assert data["price"] == 0.65
    assert data["source"] == "clob"
    assert data["timestamp"] == "2025-01-15T10:30:00+00:00"
    assert data["tx_hash"] == "0xabc123"


def test_trade_signal_timestamp_tolerance():
    """Timestamps within same minute should have same dedup_id."""
    base_data = {
        "wallet": "0x1234567890abcdef1234567890abcdef12345678",
        "market_id": "btc-50k-friday",
        "token_id": "token123",
        "side": "YES",
        "size": 250.0,
        "price": 0.65,
        "source": "clob",
        "tx_hash": "0xabc123",
    }

    # Timestamps 30 seconds apart within same minute
    data1 = {**base_data, "timestamp": "2025-01-15T10:30:00+00:00"}
    data2 = {**base_data, "timestamp": "2025-01-15T10:30:30+00:00"}

    signal1 = TradeSignal.from_dict(data1)
    signal2 = TradeSignal.from_dict(data2)

    # Should have same dedup_id due to minute rounding
    assert signal1.dedup_id == signal2.dedup_id


def test_trade_signal_different_minute_different_id():
    """Timestamps in different minutes should have different dedup_id."""
    base_data = {
        "wallet": "0x1234567890abcdef1234567890abcdef12345678",
        "market_id": "btc-50k-friday",
        "token_id": "token123",
        "side": "YES",
        "size": 250.0,
        "price": 0.65,
        "source": "clob",
        "tx_hash": "0xabc123",
    }

    # Timestamps in different minutes
    data1 = {**base_data, "timestamp": "2025-01-15T10:30:00+00:00"}
    data2 = {**base_data, "timestamp": "2025-01-15T10:31:00+00:00"}

    signal1 = TradeSignal.from_dict(data1)
    signal2 = TradeSignal.from_dict(data2)

    # Should have different dedup_id
    assert signal1.dedup_id != signal2.dedup_id
