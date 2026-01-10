"""Application settings with Pydantic validation."""

from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RiskConfig(BaseSettings):
    """Risk management configuration."""

    model_config = SettingsConfigDict(
        env_prefix="POLYMIND_RISK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_daily_loss: float = Field(
        default=500.0, description="Maximum daily loss in USD"
    )
    max_exposure_per_market: float = Field(
        default=200.0, description="Max exposure per market"
    )
    max_exposure_per_wallet: float = Field(
        default=500.0, description="Max exposure per wallet"
    )
    max_total_exposure: float = Field(default=2000.0, description="Max total exposure")
    max_single_trade: float = Field(default=100.0, description="Max single trade size")
    max_slippage: float = Field(default=0.03, description="Max slippage (3%)")

    @field_validator(
        "max_daily_loss",
        "max_exposure_per_market",
        "max_exposure_per_wallet",
        "max_total_exposure",
        "max_single_trade",
        mode="before",
    )
    @classmethod
    def validate_positive(cls, v: float | str) -> float:
        v_float = float(v)
        if v_float <= 0:
            raise ValueError("Value must be positive")
        return v_float


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="POLYMIND_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="polymind")
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(
        env_prefix="POLYMIND_REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class ClaudeConfig(BaseSettings):
    """Claude API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="POLYMIND_CLAUDE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(default="")
    model: str = Field(default="claude-sonnet-4-20250514")
    max_tokens: int = Field(default=1024)


class DiscordConfig(BaseSettings):
    """Discord bot configuration."""

    model_config = SettingsConfigDict(
        env_prefix="POLYMIND_DISCORD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(default="")
    channel_id: str = Field(default="")
    enabled: bool = Field(default=False)


class ArbitrageConfig(BaseSettings):
    """Arbitrage monitoring configuration."""

    model_config = SettingsConfigDict(
        env_prefix="POLYMIND_ARBITRAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=False, description="Enable arbitrage monitoring")
    min_spread: float = Field(default=0.03, description="Minimum spread to trigger (3%)")
    poll_interval: float = Field(default=30.0, description="Seconds between scans")
    max_signal_size: float = Field(default=100.0, description="Max USD per arbitrage signal")


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="POLYMIND_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="polymind")
    mode: Literal["paper", "live", "paused"] = Field(default="paper")
    log_level: str = Field(default="INFO")

    risk: RiskConfig = Field(default_factory=RiskConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    arbitrage: ArbitrageConfig = Field(default_factory=ArbitrageConfig)


def load_settings() -> Settings:
    """Load settings from environment."""
    return Settings()
