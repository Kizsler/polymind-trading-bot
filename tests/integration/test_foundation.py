"""Integration tests for Phase 1 foundation."""

from polymind import __version__
from polymind.config.settings import Settings
from polymind.interfaces.cli.main import app
from polymind.storage.models import Trade, Wallet


def test_version_is_set() -> None:
    """Package version should be set."""
    assert __version__ == "0.1.0"


def test_settings_can_be_loaded() -> None:
    """Settings should load without errors."""
    settings = Settings()
    assert settings.app_name == "polymind"
    assert settings.mode == "paper"


def test_models_can_be_instantiated() -> None:
    """Database models should be instantiable."""
    wallet = Wallet(address="0x" + "a" * 40, alias="test")
    assert wallet.address.startswith("0x")

    trade = Trade(
        wallet_id=1,
        market_id="test-market",
        side="YES",
        size=100.0,
        price=0.5,
        source="clob",
    )
    assert trade.side == "YES"


def test_cli_app_exists() -> None:
    """CLI app should be importable."""
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "polymind" in result.stdout.lower()
