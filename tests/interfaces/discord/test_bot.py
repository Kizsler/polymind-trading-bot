"""Tests for Discord bot."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.interfaces.discord.bot import PolymindBot


def test_bot_has_required_attributes() -> None:
    """Bot should have required attributes."""
    bot = PolymindBot(command_prefix="!")

    assert bot.command_prefix == "!"
    assert hasattr(bot, "cache")
    assert hasattr(bot, "db")


def test_bot_creates_with_intents() -> None:
    """Bot should be created with proper intents."""
    bot = PolymindBot(command_prefix="!")

    assert bot.intents.message_content is True


@pytest.mark.asyncio
async def test_bot_setup_hook_loads_cogs() -> None:
    """Bot setup should load cogs."""
    bot = PolymindBot(command_prefix="!")

    with patch.object(bot, "load_extension", new_callable=AsyncMock) as mock_load:
        with patch("polymind.interfaces.discord.bot.load_settings") as mock_settings:
            with patch("polymind.interfaces.discord.bot.Database") as mock_db:
                with patch("polymind.interfaces.discord.bot.create_cache", new_callable=AsyncMock) as mock_cache:
                    mock_settings.return_value = MagicMock()
                    mock_settings.return_value.database = MagicMock()
                    mock_settings.return_value.redis = MagicMock()
                    mock_settings.return_value.redis.url = "redis://localhost"

                    await bot.setup_hook()

                    mock_load.assert_called()
