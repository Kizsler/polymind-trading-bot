"""PolyMind CLI application."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from polymind import __version__

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
    console.print(
        Panel.fit(
            "[bold green]Starting PolyMind...[/bold green]\n"
            "Mode: [yellow]paper[/yellow]\n"
            "Press Ctrl+C to stop",
            title="PolyMind",
        )
    )
    console.print("[dim]Bot start not yet implemented[/dim]")


@app.command()
def stop() -> None:
    """Stop the trading bot gracefully."""
    console.print("[yellow]Stopping PolyMind...[/yellow]")
    console.print("[green]Bot stopped[/green]")


@app.command()
def status() -> None:
    """Show current bot status."""
    table = Table(title="PolyMind Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Version", __version__)
    table.add_row("Mode", "paper")
    table.add_row("Status", "stopped")
    table.add_row("Tracked Wallets", "0")
    table.add_row("Open Positions", "0")
    table.add_row("Daily P&L", "$0.00")

    console.print(table)


@app.command()
def pause() -> None:
    """Pause trading (emergency stop)."""
    console.print("[bold red]PAUSING ALL TRADING[/bold red]")
    console.print("[yellow]Trading paused. Use 'polymind start' to resume.[/yellow]")


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

    console.print(f"[green]Mode set to: {new_mode}[/green]")


@app.command()
def trades(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of trades to show"),
) -> None:
    """Show recent trades."""
    table = Table(title=f"Recent Trades (last {limit})")
    table.add_column("Time", style="dim")
    table.add_column("Wallet")
    table.add_column("Market")
    table.add_column("Side")
    table.add_column("Size")
    table.add_column("AI Decision")
    table.add_column("P&L")

    console.print(table)
    console.print("[dim]No trades yet[/dim]")


# Wallets subcommands


@wallets_app.command("list")
def wallets_list() -> None:
    """List all tracked wallets."""
    table = Table(title="Tracked Wallets")
    table.add_column("Address", style="cyan")
    table.add_column("Alias")
    table.add_column("Enabled")
    table.add_column("Win Rate")
    table.add_column("Total P&L")

    console.print(table)
    console.print(
        "[dim]No wallets tracked. Use 'polymind wallets add <address>' to add one.[/dim]"
    )


@wallets_app.command("add")
def wallets_add(
    address: str = typer.Argument(..., help="Wallet address to track"),
    alias: str | None = typer.Option(None, "--alias", "-a", help="Friendly name"),
) -> None:
    """Add a wallet to track."""
    display = alias or address[:10] + "..."
    console.print(f"[green]Added wallet: {display}[/green]")


@wallets_app.command("remove")
def wallets_remove(
    address: str = typer.Argument(..., help="Wallet address to remove"),
) -> None:
    """Remove a wallet from tracking."""
    console.print(f"[yellow]Removed wallet: {address[:10]}...[/yellow]")


@wallets_app.command("enable")
def wallets_enable(
    address: str = typer.Argument(..., help="Wallet address to enable"),
) -> None:
    """Enable trading for a wallet."""
    console.print(f"[green]Enabled wallet: {address[:10]}...[/green]")


@wallets_app.command("disable")
def wallets_disable(
    address: str = typer.Argument(..., help="Wallet address to disable"),
) -> None:
    """Disable trading for a wallet."""
    console.print(f"[yellow]Disabled wallet: {address[:10]}...[/yellow]")


if __name__ == "__main__":
    app()
