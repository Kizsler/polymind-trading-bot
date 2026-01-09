"""Discord bot implementation."""

import discord
from discord.ext import commands

from polymind.config.settings import Settings, load_settings
from polymind.storage.cache import Cache, create_cache
from polymind.storage.database import Database


class PolymindBot(commands.Bot):
    """PolyMind Discord bot."""

    def __init__(self, command_prefix: str = "!", **kwargs) -> None:
        """Initialize the bot."""
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            **kwargs,
        )

        self.cache: Cache | None = None
        self.db: Database | None = None
        self.settings: Settings | None = None

    async def setup_hook(self) -> None:
        """Setup hook called when bot is ready."""
        self.settings = load_settings()
        self.db = Database(self.settings)
        self.cache = await create_cache(self.settings.redis.url)

        await self.load_extension("polymind.interfaces.discord.cogs.status")

    async def close(self) -> None:
        """Clean up connections on close."""
        if self.db:
            await self.db.close()
        if self.cache:
            await self.cache.close()
        await super().close()


async def create_bot() -> PolymindBot:
    """Create and configure the Discord bot."""
    return PolymindBot()
