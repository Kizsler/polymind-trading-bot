"""Tests for CLI commands."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from polymind.interfaces.cli.main import app

runner = CliRunner()


def test_cli_version() -> None:
    """CLI should show version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_cli_status_command() -> None:
    """CLI should have status command."""
    mock_context = MagicMock()
    mock_context.db = AsyncMock()
    mock_context.cache = AsyncMock()
    mock_context.db.get_all_wallets = AsyncMock(return_value=[])
    mock_context.cache.get_mode = AsyncMock(return_value="paper")
    mock_context.cache.get_daily_pnl = AsyncMock(return_value=0.0)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "PolyMind" in result.stdout


def test_cli_wallets_list() -> None:
    """CLI should have wallets list command."""
    mock_context = MagicMock()
    mock_context.db = AsyncMock()
    mock_context.db.get_all_wallets = AsyncMock(return_value=[])

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "list"])

    assert result.exit_code == 0


def test_cli_mode_command_sets_paper() -> None:
    """CLI mode should set mode to paper."""
    mock_context = MagicMock()
    mock_context.cache = AsyncMock()
    mock_context.cache.set_mode = AsyncMock()

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["mode", "paper"])

    assert result.exit_code == 0
    assert "paper" in result.stdout


def test_cli_mode_invalid_mode() -> None:
    """CLI mode should reject invalid modes."""
    result = runner.invoke(app, ["mode", "invalid"])
    assert result.exit_code == 1
    assert "Invalid mode" in result.stdout


def test_cli_pause_command() -> None:
    """CLI pause should pause trading."""
    mock_context = MagicMock()
    mock_context.cache = AsyncMock()
    mock_context.cache.set_mode = AsyncMock()

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["pause"])

    assert result.exit_code == 0
    assert "PAUSING" in result.stdout


def test_cli_trades_command() -> None:
    """CLI trades should show trades table."""
    mock_context = MagicMock()
    mock_context.db = AsyncMock()
    mock_context.db.get_recent_trades = AsyncMock(return_value=[])

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["trades"])

    assert result.exit_code == 0
    assert "No trades yet" in result.stdout
