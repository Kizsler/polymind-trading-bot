"""Status cog for Discord bot."""

import discord
from discord import app_commands
from discord.ext import commands

from polymind import __version__


class StatusCog(commands.Cog):
    """Cog for status commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the cog."""
        self.bot = bot

    @app_commands.command(name="status", description="Show bot status")
    async def status(self, interaction: discord.Interaction) -> None:
        """Show current bot status."""
        cache = getattr(self.bot, "cache", None)
        db = getattr(self.bot, "db", None)

        mode = await cache.get_mode() if cache else "unknown"
        daily_pnl = await cache.get_daily_pnl() if cache else 0.0
        wallets = await db.get_all_wallets() if db else []

        embed = discord.Embed(
            title="PolyMind Status",
            color=discord.Color.green() if mode != "paused" else discord.Color.red(),
        )
        embed.add_field(name="Version", value=__version__, inline=True)
        embed.add_field(name="Mode", value=mode.upper(), inline=True)
        embed.add_field(name="Wallets", value=str(len(wallets)), inline=True)
        embed.add_field(name="Daily P&L", value=f"${daily_pnl:.2f}", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause", description="Pause all trading")
    async def pause(self, interaction: discord.Interaction) -> None:
        """Pause all trading."""
        cache = getattr(self.bot, "cache", None)
        if cache:
            await cache.set_mode("paused")

        await interaction.response.send_message(
            "🛑 **Trading Paused**\nAll trading has been stopped.",
            ephemeral=True,
        )

    @app_commands.command(name="resume", description="Resume trading in paper mode")
    async def resume(self, interaction: discord.Interaction) -> None:
        """Resume trading in paper mode."""
        cache = getattr(self.bot, "cache", None)
        if cache:
            await cache.set_mode("paper")

        await interaction.response.send_message(
            "✅ **Trading Resumed**\nTrading has resumed in paper mode.",
            ephemeral=True,
        )

    @app_commands.command(name="pnl", description="Show daily P&L")
    async def pnl(self, interaction: discord.Interaction) -> None:
        """Show daily P&L."""
        cache = getattr(self.bot, "cache", None)
        daily_pnl = await cache.get_daily_pnl() if cache else 0.0

        color = discord.Color.green() if daily_pnl >= 0 else discord.Color.red()
        sign = "+" if daily_pnl >= 0 else ""

        embed = discord.Embed(
            title="Daily P&L",
            description=f"**{sign}${daily_pnl:.2f}**",
            color=color,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Setup function for loading the cog."""
    await bot.add_cog(StatusCog(bot))
