"""Tests for CLI context management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.interfaces.cli.context import CLIContext, get_context


def test_cli_context_has_required_attributes() -> None:
    """CLI context should have db, cache, and settings."""
    context = CLIContext(
        db=MagicMock(),
        cache=MagicMock(),
        settings=MagicMock(),
    )

    assert context.db is not None
    assert context.cache is not None
    assert context.settings is not None


@pytest.mark.asyncio
async def test_get_context_creates_connections() -> None:
    """get_context should create database and cache connections."""
    with (
        patch("polymind.interfaces.cli.context.Database") as mock_db_class,
        patch("polymind.interfaces.cli.context.create_cache") as mock_cache,
        patch("polymind.interfaces.cli.context.load_settings") as mock_settings,
    ):
        mock_db_class.return_value = MagicMock()
        mock_cache.return_value = AsyncMock()
        mock_settings.return_value = MagicMock()
        mock_settings.return_value.redis = MagicMock()
        mock_settings.return_value.redis.url = "redis://localhost"

        # Reset global context
        import polymind.interfaces.cli.context as ctx_module

        ctx_module._context = None

        context = await get_context()

        assert context is not None
        mock_settings.assert_called_once()
        mock_db_class.assert_called_once()
