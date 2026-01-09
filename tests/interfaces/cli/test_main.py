"""Tests for CLI commands."""

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
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "PolyMind" in result.stdout


def test_cli_wallets_list() -> None:
    """CLI should have wallets list command."""
    result = runner.invoke(app, ["wallets", "list"])
    assert result.exit_code == 0
