"""PolyMind CLI application."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
def start() -> None:
    """Start the trading bot."""
    from polymind.runner import run_bot

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
        console.print("[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)


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
