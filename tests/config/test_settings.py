"""Tests for configuration settings."""

import pytest
from polymind.config.settings import Settings, RiskConfig, DatabaseConfig


def test_settings_loads_defaults():
    """Settings should load with sensible defaults."""
    settings = Settings()

    assert settings.app_name == "polymind"
    assert settings.mode == "paper"
    assert settings.risk.max_daily_loss == 500.0


def test_risk_config_validates_positive_values():
    """Risk config should require positive values."""
    with pytest.raises(ValueError):
        RiskConfig(max_daily_loss=-100)


def test_database_config_builds_url():
    """Database config should build connection URL."""
    db = DatabaseConfig(
        host="localhost",
        port=5432,
        name="polymind",
        user="postgres",
        password="secret"
    )

    assert "postgresql+asyncpg://postgres:secret@localhost:5432/polymind" in db.url
