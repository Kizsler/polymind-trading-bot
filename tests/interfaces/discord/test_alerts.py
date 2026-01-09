"""Tests for Discord trade alerts."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from polymind.core.brain.decision import AIDecision, Urgency
from polymind.data.models import SignalSource, TradeSignal
from polymind.interfaces.discord.alerts import TradeAlertService, format_trade_alert


def test_format_trade_alert_creates_embed() -> None:
    """format_trade_alert should create Discord embed."""
    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="will-btc-hit-50k",
        token_id="token1",
        side="YES",
        size=500.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=250.0,
        confidence=0.78,
        reasoning="Strong wallet, good liquidity",
    )

    embed = format_trade_alert(
        signal=signal,
        decision=decision,
        wallet_alias="whale.eth",
        paper_mode=True,
    )

    assert embed.title == "🔔 Trade Alert"
    assert len(embed.fields) >= 5


def test_format_trade_alert_shows_paper_mode() -> None:
    """Alert should indicate paper mode."""
    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="will-btc-hit-50k",
        token_id="token1",
        side="YES",
        size=500.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=250.0,
        confidence=0.78,
        reasoning="Strong wallet",
    )

    embed = format_trade_alert(signal, decision, "whale", paper_mode=True)
    embed_text = str(embed.to_dict())
    assert "paper" in embed_text.lower() or "Paper" in embed_text


@pytest.mark.asyncio
async def test_trade_alert_service_sends_to_channel() -> None:
    """TradeAlertService should send embeds to channel."""
    mock_channel = AsyncMock()

    service = TradeAlertService(channel=mock_channel)

    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="will-btc-hit-50k",
        token_id="token1",
        side="YES",
        size=500.0,
        price=0.65,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=250.0,
        confidence=0.78,
        reasoning="Strong wallet",
    )

    await service.send_trade_alert(
        signal=signal,
        decision=decision,
        wallet_alias="whale.eth",
        paper_mode=True,
    )

    mock_channel.send.assert_called_once()
