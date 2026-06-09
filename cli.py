#!/usr/bin/env python3

import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import (
    cancel_order,
    format_cancel_response,
    format_open_orders,
    format_order_response,
    get_open_orders,
    place_limit_order,
    place_market_order,
)
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

load_dotenv()
logger = setup_logging()
console = Console(force_terminal=True)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _get_credentials() -> tuple[str, str]:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        console.print(
            "[bold red]✖ Missing API credentials.[/bold red]\n"
            "  Set BINANCE_API_KEY and BINANCE_API_SECRET in a .env file:\n\n"
            "  [dim]BINANCE_API_KEY=your_key_here\n"
            "  BINANCE_API_SECRET=your_secret_here[/dim]"
        )
        logger.error("Missing API credentials in environment.")
        sys.exit(1)
    return api_key, api_secret


def _print_request_summary(symbol: str, side: str, order_type: str, quantity: str, price: str | None):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("Symbol", symbol)
    table.add_row("Side", f"[green]{side}[/green]" if side == "BUY" else f"[red]{side}[/red]")
    table.add_row("Type", order_type)
    table.add_row("Quantity", quantity)
    if price:
        table.add_row("Price", price)

    console.print()
    console.print(Panel(table, title="[bold]📋 Order Request[/bold]", border_style="blue"))


def _print_response_summary(data: dict, title: str = "✅ Order Response"):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", style="white")

    for key, value in data.items():
        if key == "Status":
            if value in ("FILLED", "NEW"):
                value = f"[green]{value}[/green]"
            elif value in ("CANCELED", "REJECTED", "EXPIRED"):
                value = f"[red]{value}[/red]"
            else:
                value = f"[yellow]{value}[/yellow]"
        table.add_row(key, str(value))

    console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="green"))


def _handle_api_error(exc: BinanceAPIError):
    console.print(f"[bold red]✖ Binance API error:[/bold red] {exc.message} (code {exc.code})")
    logger.error("API error: %s", exc)
    sys.exit(1)


def _handle_unexpected_error(exc: Exception):
    console.print(f"[bold red]✖ Unexpected error:[/bold red] {exc}")
    logger.exception("Unexpected error")
    sys.exit(1)


# ------------------------------------------------------------------ #
# CLI group                                                            #
# ------------------------------------------------------------------ #

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Binance Futures Testnet trading bot."""
    pass


# ------------------------------------------------------------------ #
# place-order command                                                  #
# ------------------------------------------------------------------ #

@cli.command("place-order")
@click.option("--symbol", "-s", required=True, help="Trading pair (e.g. BTCUSDT).")
@click.option(
    "--side", "-S", required=True,
    type=click.Choice(["BUY", "SELL"], case_sensitive=False),
    help="Order side.",
)
@click.option(
    "--type", "-t", "order_type", required=True,
    type=click.Choice(["MARKET", "LIMIT"], case_sensitive=False),
    help="Order type.",
)
@click.option("--quantity", "-q", required=True, help="Order quantity.")
@click.option("--price", "-p", default=None, help="Limit price (required for LIMIT orders).")
@click.option("--dry-run", is_flag=True, default=False, help="Preview the order without sending it.")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
def place_order(symbol: str, side: str, order_type: str, quantity: str, price: str | None, dry_run: bool, yes: bool):
    """Place a market or limit order."""
    try:
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        order_type = validate_order_type(order_type)
        quantity = validate_quantity(quantity)
        price = validate_price(price, order_type)
    except ValueError as exc:
        console.print(f"[bold red]✖ Validation error:[/bold red] {exc}")
        logger.error("Validation failed: %s", exc)
        sys.exit(1)

    _print_request_summary(symbol, side, order_type, quantity, price)

    if dry_run:
        console.print("[bold yellow]⚠ Dry run — order not sent.[/bold yellow]\n")
        logger.info("Dry run: order not placed.")
        return

    if not yes:
        click.confirm("  Send this order?", abort=True)

    api_key, api_secret = _get_credentials()

    try:
        with BinanceClient(api_key, api_secret) as client:
            if order_type == "MARKET":
                response = place_market_order(client, symbol, side, quantity)
            else:
                response = place_limit_order(client, symbol, side, quantity, price)

    except BinanceAPIError as exc:
        _handle_api_error(exc)
    except Exception as exc:
        _handle_unexpected_error(exc)

    formatted = format_order_response(response)
    _print_response_summary(formatted)
    console.print("[bold green]✔ Order placed successfully![/bold green]\n")
    logger.info("Order placed successfully: orderId=%s", response.get("orderId"))


# ------------------------------------------------------------------ #
# cancel-order command                                                 #
# ------------------------------------------------------------------ #

@cli.command("cancel-order")
@click.option("--symbol", "-s", required=True, help="Trading pair (e.g. BTCUSDT).")
@click.option("--order-id", "-i", required=True, type=int, help="Order ID to cancel.")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
def cancel_order_cmd(symbol: str, order_id: int, yes: bool):
    """Cancel an open order by symbol and order ID."""
    try:
        symbol = validate_symbol(symbol)
    except ValueError as exc:
        console.print(f"[bold red]✖ Validation error:[/bold red] {exc}")
        sys.exit(1)

    console.print(f"\n  Cancelling order [bold]{order_id}[/bold] on [bold]{symbol}[/bold]...")

    if not yes:
        click.confirm("  Are you sure?", abort=True)

    api_key, api_secret = _get_credentials()

    try:
        with BinanceClient(api_key, api_secret) as client:
            response = cancel_order(client, symbol, order_id)

    except BinanceAPIError as exc:
        _handle_api_error(exc)
    except Exception as exc:
        _handle_unexpected_error(exc)

    formatted = format_cancel_response(response)
    _print_response_summary(formatted, title="🚫 Cancel Response")
    console.print("[bold green]✔ Order cancelled.[/bold green]\n")
    logger.info("Order cancelled: orderId=%s", order_id)


# ------------------------------------------------------------------ #
# list-orders command                                                  #
# ------------------------------------------------------------------ #

@cli.command("list-orders")
@click.option("--symbol", "-s", default=None, help="Filter by trading pair (optional).")
def list_orders(symbol: str | None):
    """List all open orders (optionally filtered by symbol)."""
    if symbol:
        try:
            symbol = validate_symbol(symbol)
        except ValueError as exc:
            console.print(f"[bold red]✖ Validation error:[/bold red] {exc}")
            sys.exit(1)

    api_key, api_secret = _get_credentials()

    try:
        with BinanceClient(api_key, api_secret) as client:
            orders = get_open_orders(client, symbol)

    except BinanceAPIError as exc:
        _handle_api_error(exc)
    except Exception as exc:
        _handle_unexpected_error(exc)

    if not orders:
        console.print("\n[dim]No open orders found.[/dim]\n")
        return

    formatted = format_open_orders(orders)

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    for col in formatted[0].keys():
        table.add_column(col)

    for row in formatted:
        status = row.get("Status", "")
        if status in ("FILLED", "NEW"):
            status_str = f"[green]{status}[/green]"
        elif status in ("CANCELED", "REJECTED", "EXPIRED"):
            status_str = f"[red]{status}[/red]"
        else:
            status_str = f"[yellow]{status}[/yellow]"

        values = [
            status_str if k == "Status" else str(v)
            for k, v in row.items()
        ]
        table.add_row(*values)

    console.print()
    console.print(Panel(table, title="[bold]📂 Open Orders[/bold]", border_style="blue"))
    console.print()


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    cli()
