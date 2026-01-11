"""PolyMind CLI application."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, FloatPrompt
from rich.table import Table
from rich.text import Text

from polymind import __version__
from polymind.interfaces.cli.context import get_context

# Create Typer app
app = typer.Typer(
    name="polymind",
    help="AI-powered prediction market trading bot",
    no_args_is_help=True,
)

# Create subcommand groups
wallets_app = typer.Typer(help="Manage tracked wallets")
app.add_typer(wallets_app, name="wallets")

# Rich console for pretty output
console = Console()


def run_startup_configuration() -> dict:
    """Interactive startup configuration wizard."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]PolyMind Startup Configuration[/bold cyan]\n"
            "[dim]Configure your trading parameters before starting[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    config = {}

    # Trading Mode
    console.print("[bold]1. Trading Mode[/bold]")
    mode_choice = Prompt.ask(
        "  Select mode",
        choices=["paper", "live"],
        default="paper",
    )
    config["trading_mode"] = mode_choice

    if mode_choice == "live":
        if not Confirm.ask(
            "  [bold red]WARNING:[/bold red] Live mode uses REAL money. Continue?",
            default=False,
        ):
            config["trading_mode"] = "paper"
            console.print("  [yellow]Switched to paper mode[/yellow]")

    console.print()

    # Starting Balance (Paper Trading)
    console.print("[bold]2. Starting Balance[/bold]")
    console.print("  [dim]Virtual balance for paper trading simulation[/dim]")
    starting_balance = FloatPrompt.ask(
        "  Starting balance ($)",
        default=1000.0,
    )
    config["starting_balance"] = max(100.0, starting_balance)
    console.print()

    # Slippage Tolerance
    console.print("[bold]3. Slippage Tolerance[/bold]")
    console.print("  [dim]Max allowed price slippage before rejecting trade[/dim]")
    slippage = FloatPrompt.ask(
        "  Max slippage (%)",
        default=3.0,
    )
    config["max_slippage"] = max(0.1, min(slippage, 20.0)) / 100.0  # Convert to decimal
    console.print()

    # Trade Size Percentage
    console.print("[bold]4. Trade Size (Copy Percentage)[/bold]")
    console.print("  [dim]What % of detected wallet trade to copy[/dim]")
    trade_pct = FloatPrompt.ask(
        "  Copy percentage (%)",
        default=100.0,
    )
    config["copy_percentage"] = max(1.0, min(trade_pct, 200.0)) / 100.0
    console.print()

    # Max Single Trade
    console.print("[bold]5. Max Single Trade Size[/bold]")
    console.print("  [dim]Maximum USD per individual trade[/dim]")
    max_trade = FloatPrompt.ask(
        "  Max trade size ($)",
        default=100.0,
    )
    config["max_single_trade"] = max(10.0, max_trade)
    console.print()

    # Daily Loss Limit
    console.print("[bold]6. Daily Loss Limit[/bold]")
    console.print("  [dim]Stop trading if daily losses exceed this amount[/dim]")
    daily_loss = FloatPrompt.ask(
        "  Daily loss limit ($)",
        default=500.0,
    )
    config["daily_loss_limit"] = max(50.0, daily_loss)
    console.print()

    # Max Total Exposure
    console.print("[bold]7. Max Total Exposure[/bold]")
    console.print("  [dim]Maximum total open positions value[/dim]")
    max_exposure = FloatPrompt.ask(
        "  Max exposure ($)",
        default=2000.0,
    )
    config["max_daily_exposure"] = max(100.0, max_exposure)
    console.print()

    # AI Confidence Threshold
    console.print("[bold]8. AI Confidence Threshold[/bold]")
    console.print("  [dim]Minimum AI confidence to execute trade[/dim]")
    confidence = FloatPrompt.ask(
        "  Min confidence (%)",
        default=70.0,
    )
    config["confidence_threshold"] = max(10.0, min(confidence, 99.0)) / 100.0
    console.print()

    # Auto-trade enabled
    console.print("[bold]9. Auto-Trade[/bold]")
    auto_trade = Confirm.ask(
        "  Enable automatic trading?",
        default=True,
    )
    config["auto_trade"] = auto_trade
    console.print()

    # AI Enabled
    console.print("[bold]10. AI Decision Engine[/bold]")
    ai_enabled = Confirm.ask(
        "  Enable Claude AI for trade decisions?",
        default=True,
    )
    config["ai_enabled"] = ai_enabled
    console.print()

    return config


def display_config_summary(config: dict) -> None:
    """Display configuration summary."""
    table = Table(title="Configuration Summary", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Trading Mode", config["trading_mode"].upper())
    table.add_row("Starting Balance", f"${config['starting_balance']:,.2f}")
    table.add_row("Max Slippage", f"{config['max_slippage'] * 100:.1f}%")
    table.add_row("Copy Percentage", f"{config['copy_percentage'] * 100:.0f}%")
    table.add_row("Max Trade Size", f"${config['max_single_trade']:,.2f}")
    table.add_row("Daily Loss Limit", f"${config['daily_loss_limit']:,.2f}")
    table.add_row("Max Exposure", f"${config['max_daily_exposure']:,.2f}")
    table.add_row("AI Confidence", f"{config['confidence_threshold'] * 100:.0f}%")
    table.add_row("Auto-Trade", "Enabled" if config["auto_trade"] else "Disabled")
    table.add_row("AI Engine", "Enabled" if config["ai_enabled"] else "Disabled")

    console.print()
    console.print(table)
    console.print()


async def save_config_to_cache(config: dict) -> None:
    """Save configuration to Redis cache."""
    ctx = await get_context()
    await ctx.cache.set_mode(config["trading_mode"])
    await ctx.cache.update_settings({
        "trading_mode": config["trading_mode"],
        "starting_balance": config["starting_balance"],
        "max_slippage": config["max_slippage"],
        "copy_percentage": config["copy_percentage"],
        "max_position_size": config["max_single_trade"],
        "max_daily_exposure": config["max_daily_exposure"],
        "daily_loss_limit": config["daily_loss_limit"],
        "confidence_threshold": config["confidence_threshold"],
        "auto_trade": config["auto_trade"],
        "ai_enabled": config["ai_enabled"],
    })


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"PolyMind v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """PolyMind - AI-powered prediction market trading bot."""
    pass


@app.command()
def start(
    configure: bool = typer.Option(
        False,
        "--configure",
        "-c",
        help="Run interactive configuration wizard before starting",
    ),
    quick: bool = typer.Option(
        False,
        "--quick",
        "-q",
        help="Skip configuration and use defaults/cached settings",
    ),
) -> None:
    """Start the trading bot.

    By default, prompts for configuration on first run.
    Use --configure to always show the wizard.
    Use --quick to skip configuration entirely.
    """
    from polymind.runner import run_bot

    # Determine if we should run configuration
    run_config = configure

    if not quick and not configure:
        # Check if this is first run or user wants to configure
        if Confirm.ask(
            "\n[cyan]Configure trading parameters before starting?[/cyan]",
            default=True,
        ):
            run_config = True

    if run_config:
        # Run interactive configuration
        config = run_startup_configuration()
        display_config_summary(config)

        if not Confirm.ask("Start bot with these settings?", default=True):
            console.print("[yellow]Startup cancelled[/yellow]")
            raise typer.Exit(0)

        # Save configuration to cache
        asyncio.run(save_config_to_cache(config))
        console.print("[green]Configuration saved![/green]")

    console.print()
    console.print(
        Panel.fit(
            "[bold green]Starting PolyMind...[/bold green]\n"
            "Press Ctrl+C to stop",
            title="PolyMind",
        )
    )

    try:
        run_bot()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def configure() -> None:
    """Configure trading parameters interactively."""
    config = run_startup_configuration()
    display_config_summary(config)

    if Confirm.ask("Save these settings?", default=True):
        asyncio.run(save_config_to_cache(config))
        console.print("[green]Configuration saved![/green]")
    else:
        console.print("[yellow]Configuration not saved[/yellow]")


@app.command()
def stop() -> None:
    """Stop the trading bot gracefully."""
    console.print("[yellow]Stopping PolyMind...[/yellow]")
    console.print("[green]Bot stopped[/green]")


@app.command()
def status() -> None:
    """Show current bot status."""

    async def _status() -> None:
        ctx = await get_context()

        mode = await ctx.cache.get_mode()
        daily_pnl = await ctx.cache.get_daily_pnl()
        wallets = await ctx.db.get_all_wallets()

        table = Table(title="PolyMind Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Version", __version__)
        table.add_row("Mode", mode)
        table.add_row("Status", "running" if mode != "paused" else "paused")
        table.add_row("Tracked Wallets", str(len(wallets)))
        table.add_row("Daily P&L", f"${daily_pnl:.2f}")

        console.print(table)

    asyncio.run(_status())


@app.command()
def pause() -> None:
    """Pause trading (emergency stop)."""

    async def _pause() -> None:
        ctx = await get_context()
        await ctx.cache.set_mode("paused")
        console.print("[bold red]PAUSING ALL TRADING[/bold red]")
        console.print(
            "[yellow]Trading paused. Use 'polymind mode paper' or "
            "'polymind mode live' to resume.[/yellow]"
        )

    asyncio.run(_pause())


@app.command()
def mode(
    new_mode: str = typer.Argument(
        ...,
        help="Trading mode: paper, live, or paused",
    ),
) -> None:
    """Switch trading mode."""
    valid_modes = ["paper", "live", "paused"]
    if new_mode not in valid_modes:
        console.print(f"[red]Invalid mode. Choose from: {', '.join(valid_modes)}[/red]")
        raise typer.Exit(1)

    if new_mode == "live":
        typer.confirm(
            "Are you sure you want to enable LIVE trading with real money?",
            abort=True,
        )

    async def _set_mode() -> None:
        ctx = await get_context()
        await ctx.cache.set_mode(new_mode)
        console.print(f"[green]Mode set to: {new_mode}[/green]")

    asyncio.run(_set_mode())


@app.command()
def trades(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of trades to show"),
) -> None:
    """Show recent trades."""

    async def _trades() -> None:
        ctx = await get_context()
        recent_trades = await ctx.db.get_recent_trades(limit=limit)

        table = Table(title=f"Recent Trades (last {limit})")
        table.add_column("Time", style="dim")
        table.add_column("Wallet")
        table.add_column("Market")
        table.add_column("Side")
        table.add_column("Size")
        table.add_column("AI Decision")
        table.add_column("P&L")

        for trade in recent_trades:
            table.add_row(
                trade.detected_at.strftime("%Y-%m-%d %H:%M"),
                trade.wallet.alias or trade.wallet.address[:10] + "...",
                trade.market_id[:20] + "...",
                trade.side,
                f"${trade.size:.2f}",
                "Y" if trade.ai_decision else "N",
                f"${trade.pnl:.2f}" if trade.pnl else "-",
            )

        console.print(table)
        if not recent_trades:
            console.print("[dim]No trades yet[/dim]")

    asyncio.run(_trades())


# Wallets subcommands


@wallets_app.command("list")
def wallets_list() -> None:
    """List all tracked wallets."""

    async def _list() -> None:
        ctx = await get_context()
        wallets = await ctx.db.get_all_wallets()

        table = Table(title="Tracked Wallets")
        table.add_column("Address", style="cyan")
        table.add_column("Alias")
        table.add_column("Enabled")
        table.add_column("Win Rate")
        table.add_column("Total P&L")

        for wallet in wallets:
            metrics = wallet.metrics
            table.add_row(
                wallet.address[:10] + "...",
                wallet.alias or "-",
                "Y" if wallet.enabled else "N",
                f"{metrics.win_rate * 100:.1f}%" if metrics else "-",
                f"${metrics.total_pnl:.2f}" if metrics else "-",
            )

        console.print(table)
        if not wallets:
            console.print(
                "[dim]No wallets tracked. "
                "Use 'polymind wallets add <address>' to add one.[/dim]"
            )

    asyncio.run(_list())


@wallets_app.command("add")
def wallets_add(
    address: str = typer.Argument(..., help="Wallet address to track"),
    alias: str | None = typer.Option(None, "--alias", "-a", help="Friendly name"),
) -> None:
    """Add a wallet to track."""

    async def _add() -> None:
        ctx = await get_context()
        wallet = await ctx.db.add_wallet(address=address, alias=alias)
        display = alias or address[:10] + "..."
        console.print(f"[green]Added wallet: {display} (id={wallet.id})[/green]")

    asyncio.run(_add())


@wallets_app.command("remove")
def wallets_remove(
    address: str = typer.Argument(..., help="Wallet address to remove"),
) -> None:
    """Remove a wallet from tracking."""

    async def _remove() -> None:
        ctx = await get_context()
        removed = await ctx.db.remove_wallet(address=address)
        if removed:
            console.print(f"[yellow]Removed wallet: {address[:10]}...[/yellow]")
        else:
            console.print(f"[red]Wallet not found: {address[:10]}...[/red]")

    asyncio.run(_remove())


@wallets_app.command("enable")
def wallets_enable(
    address: str = typer.Argument(..., help="Wallet address to enable"),
) -> None:
    """Enable trading for a wallet."""

    async def _enable() -> None:
        ctx = await get_context()
        updated = await ctx.db.update_wallet(address=address, enabled=True)
        if updated:
            console.print(f"[green]Enabled wallet: {address[:10]}...[/green]")
        else:
            console.print(f"[red]Wallet not found: {address[:10]}...[/red]")

    asyncio.run(_enable())


@wallets_app.command("disable")
def wallets_disable(
    address: str = typer.Argument(..., help="Wallet address to disable"),
) -> None:
    """Disable trading for a wallet."""

    async def _disable() -> None:
        ctx = await get_context()
        updated = await ctx.db.update_wallet(address=address, enabled=False)
        if updated:
            console.print(f"[yellow]Disabled wallet: {address[:10]}...[/yellow]")
        else:
            console.print(f"[red]Wallet not found: {address[:10]}...[/red]")

    asyncio.run(_disable())


if __name__ == "__main__":
    app()
