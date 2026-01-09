"""Tests for CLI wallet commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from polymind.interfaces.cli.main import app

runner = CliRunner()


@pytest.fixture
def mock_context():
    """Create mock CLI context."""
    context = MagicMock()
    context.db = AsyncMock()
    context.cache = AsyncMock()
    context.settings = MagicMock()
    return context


def test_wallets_list_shows_wallets(mock_context) -> None:
    """wallets list should show tracked wallets from database."""
    # Mock database returning wallets
    mock_wallet = MagicMock()
    mock_wallet.address = "0x1234567890abcdef"
    mock_wallet.alias = "whale.eth"
    mock_wallet.enabled = True

    mock_metrics = MagicMock()
    mock_metrics.win_rate = 0.72
    mock_metrics.total_pnl = 1500.0

    mock_wallet.metrics = mock_metrics

    mock_context.db.get_all_wallets = AsyncMock(return_value=[mock_wallet])

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "list"])

    assert result.exit_code == 0
    assert "whale.eth" in result.stdout or "0x1234" in result.stdout


def test_wallets_list_empty_shows_message(mock_context) -> None:
    """wallets list should show helpful message when no wallets."""
    mock_context.db.get_all_wallets = AsyncMock(return_value=[])

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "list"])

    assert result.exit_code == 0
    assert "No wallets tracked" in result.stdout


def test_wallets_add_creates_wallet(mock_context) -> None:
    """wallets add should create wallet in database."""
    mock_wallet = MagicMock()
    mock_wallet.id = 1
    mock_context.db.add_wallet = AsyncMock(return_value=mock_wallet)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(
            app, ["wallets", "add", "0x1234567890abcdef", "--alias", "test"]
        )

    assert result.exit_code == 0
    assert "Added" in result.stdout


def test_wallets_add_with_alias_shows_alias(mock_context) -> None:
    """wallets add with alias should show alias in output."""
    mock_wallet = MagicMock()
    mock_wallet.id = 1
    mock_context.db.add_wallet = AsyncMock(return_value=mock_wallet)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(
            app, ["wallets", "add", "0x1234567890abcdef", "--alias", "my-wallet"]
        )

    assert result.exit_code == 0
    assert "my-wallet" in result.stdout


def test_wallets_remove_deletes_wallet(mock_context) -> None:
    """wallets remove should delete wallet from database."""
    mock_context.db.remove_wallet = AsyncMock(return_value=True)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "remove", "0x1234567890abcdef"])

    assert result.exit_code == 0
    assert "Removed" in result.stdout


def test_wallets_remove_not_found(mock_context) -> None:
    """wallets remove should show error when wallet not found."""
    mock_context.db.remove_wallet = AsyncMock(return_value=False)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "remove", "0xnonexistent"])

    assert result.exit_code == 0
    assert "not found" in result.stdout


def test_wallets_enable_enables_wallet(mock_context) -> None:
    """wallets enable should enable wallet in database."""
    mock_context.db.update_wallet = AsyncMock(return_value=True)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "enable", "0x1234567890abcdef"])

    assert result.exit_code == 0
    assert "Enabled" in result.stdout
    mock_context.db.update_wallet.assert_called_once_with(
        address="0x1234567890abcdef", enabled=True
    )


def test_wallets_enable_not_found(mock_context) -> None:
    """wallets enable should show error when wallet not found."""
    mock_context.db.update_wallet = AsyncMock(return_value=False)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "enable", "0xnonexistent"])

    assert result.exit_code == 0
    assert "not found" in result.stdout


def test_wallets_disable_disables_wallet(mock_context) -> None:
    """wallets disable should disable wallet in database."""
    mock_context.db.update_wallet = AsyncMock(return_value=True)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "disable", "0x1234567890abcdef"])

    assert result.exit_code == 0
    assert "Disabled" in result.stdout
    mock_context.db.update_wallet.assert_called_once_with(
        address="0x1234567890abcdef", enabled=False
    )


def test_wallets_disable_not_found(mock_context) -> None:
    """wallets disable should show error when wallet not found."""
    mock_context.db.update_wallet = AsyncMock(return_value=False)

    with patch(
        "polymind.interfaces.cli.main.get_context",
        return_value=mock_context,
    ):
        result = runner.invoke(app, ["wallets", "disable", "0xnonexistent"])

    assert result.exit_code == 0
    assert "not found" in result.stdout
