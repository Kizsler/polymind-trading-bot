"""Trade alert notifications for Discord."""

import discord

from polymind.core.brain.decision import AIDecision
from polymind.data.models import TradeSignal


def format_trade_alert(
    signal: TradeSignal,
    decision: AIDecision,
    wallet_alias: str | None = None,
    paper_mode: bool = True,
) -> discord.Embed:
    """Format a trade alert as Discord embed."""
    wallet_display = wallet_alias or f"{signal.wallet[:10]}..."
    mode_text = "📝 Paper" if paper_mode else "💰 Live"

    color = discord.Color.green() if decision.execute else discord.Color.red()

    embed = discord.Embed(
        title="🔔 Trade Alert",
        color=color,
    )

    embed.add_field(
        name="Wallet",
        value=f"**{wallet_display}** copied",
        inline=False,
    )
    embed.add_field(
        name="Market",
        value=f'"{signal.market_id}"',
        inline=False,
    )
    embed.add_field(
        name="Side",
        value=f"**{signal.side}** @ ${signal.price:.2f}",
        inline=True,
    )
    embed.add_field(
        name="Size",
        value=f"${decision.size:.2f} ({mode_text})",
        inline=True,
    )
    embed.add_field(
        name="AI Confidence",
        value=f"{decision.confidence * 100:.0f}%",
        inline=True,
    )
    embed.add_field(
        name="Reasoning",
        value=f'"{decision.reasoning}"',
        inline=False,
    )

    embed.set_footer(text=f"Urgency: {decision.urgency.value.upper()}")

    return embed


class TradeAlertService:
    """Service for sending trade alerts to Discord."""

    def __init__(self, channel: discord.TextChannel) -> None:
        """Initialize the alert service."""
        self.channel = channel

    async def send_trade_alert(
        self,
        signal: TradeSignal,
        decision: AIDecision,
        wallet_alias: str | None = None,
        paper_mode: bool = True,
    ) -> None:
        """Send a trade alert to the channel."""
        embed = format_trade_alert(
            signal=signal,
            decision=decision,
            wallet_alias=wallet_alias,
            paper_mode=paper_mode,
        )
        await self.channel.send(embed=embed)

    async def send_error(self, message: str) -> None:
        """Send an error notification."""
        embed = discord.Embed(
            title="⚠️ Error",
            description=message,
            color=discord.Color.orange(),
        )
        await self.channel.send(embed=embed)

    async def send_risk_alert(self, violation: str, details: str) -> None:
        """Send a risk violation alert."""
        embed = discord.Embed(
            title="🛑 Risk Alert",
            color=discord.Color.red(),
        )
        embed.add_field(name="Violation", value=violation, inline=False)
        embed.add_field(name="Details", value=details, inline=False)
        await self.channel.send(embed=embed)
