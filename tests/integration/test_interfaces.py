"""Integration tests for user interfaces."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from typer.testing import CliRunner

from polymind.core.brain.decision import AIDecision
from polymind.data.models import SignalSource, TradeSignal
from polymind.interfaces.api.main import app as api_app
from polymind.interfaces.cli.main import app as cli_app
from polymind.interfaces.discord.alerts import TradeAlertService, format_trade_alert


runner = CliRunner()


# CLI Integration Tests


def test_cli_version_command() -> None:
    """CLI version should show version."""
    result = runner.invoke(cli_app, ["--version"])
    assert result.exit_code == 0
    assert "PolyMind" in result.stdout


def test_cli_status_command_with_mock_context() -> None:
    """CLI status should show status from cache."""
    mock_context = MagicMock()
    mock_context.cache = AsyncMock()
    mock_context.cache.get_mode = AsyncMock(return_value="paper")
    mock_context.cache.get_daily_pnl = AsyncMock(return_value=-50.0)
    mock_context.db = AsyncMock()
    mock_context.db.get_all_wallets = AsyncMock(return_value=[])

    with patch("polymind.interfaces.cli.main.get_context", return_value=mock_context):
        result = runner.invoke(cli_app, ["status"])

    assert result.exit_code == 0
    assert "paper" in result.stdout.lower()


def test_cli_mode_command_sets_mode() -> None:
    """CLI mode should set mode in cache."""
    mock_context = MagicMock()
    mock_context.cache = AsyncMock()
    mock_context.cache.set_mode = AsyncMock()

    with patch("polymind.interfaces.cli.main.get_context", return_value=mock_context):
        result = runner.invoke(cli_app, ["mode", "paper"])

    assert result.exit_code == 0
    assert "paper" in result.stdout.lower()


# API Integration Tests


@pytest.mark.asyncio
async def test_api_health_returns_ok() -> None:
    """API health should return OK."""
    async with AsyncClient(
        transport=ASGITransport(app=api_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_api_wallets_crud_flow() -> None:
    """API wallets should support full CRUD."""
    from polymind.interfaces.api.deps import get_db

    mock_wallet = MagicMock()
    mock_wallet.id = 1
    mock_wallet.address = "0xtest"
    mock_wallet.alias = "test"
    mock_wallet.enabled = True
    mock_wallet.metrics = None

    mock_db = AsyncMock()
    mock_db.get_all_wallets = AsyncMock(return_value=[mock_wallet])
    mock_db.add_wallet = AsyncMock(return_value=mock_wallet)
    mock_db.remove_wallet = AsyncMock(return_value=True)

    api_app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
        ) as client:
            # Create
            response = await client.post(
                "/wallets",
                json={"address": "0xtest", "alias": "test"},
            )
            assert response.status_code == 201

            # List
            response = await client.get("/wallets")
            assert response.status_code == 200
            assert len(response.json()) == 1

            # Delete
            response = await client.delete("/wallets/0xtest")
            assert response.status_code == 204
    finally:
        api_app.dependency_overrides.clear()


# Discord Integration Tests


def test_discord_trade_alert_format() -> None:
    """Discord trade alert should format correctly."""
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


@pytest.mark.asyncio
async def test_discord_alert_service_sends_embed() -> None:
    """Discord alert service should send embeds."""
    mock_channel = AsyncMock()

    service = TradeAlertService(channel=mock_channel)

    signal = TradeSignal(
        wallet="0x1234567890abcdef",
        market_id="test-market",
        token_id="token1",
        side="YES",
        size=100.0,
        price=0.50,
        source=SignalSource.CLOB,
        timestamp=datetime.now(UTC),
        tx_hash="0xabc",
    )

    decision = AIDecision.approve(
        size=50.0,
        confidence=0.80,
        reasoning="Test trade",
    )

    await service.send_trade_alert(signal, decision, "test", True)

    mock_channel.send.assert_called_once()
    call_kwargs = mock_channel.send.call_args.kwargs
    assert "embed" in call_kwargs
