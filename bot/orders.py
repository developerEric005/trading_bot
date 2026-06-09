import logging
from typing import Any

from .client import BinanceClient

logger = logging.getLogger("trading_bot.orders")


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: str,
) -> dict:
    return client.place_order(
        symbol=symbol,
        side=side,
        type="MARKET",
        quantity=quantity,
    )


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: str,
    price: str,
    time_in_force: str = "GTC",
) -> dict:
    return client.place_order(
        symbol=symbol,
        side=side,
        type="LIMIT",
        quantity=quantity,
        price=price,
        timeInForce=time_in_force,
    )


def cancel_order(client: BinanceClient, symbol: str, order_id: int) -> dict:
    """Cancel an open order by symbol and order ID."""
    return client.cancel_order(symbol=symbol, order_id=order_id)


def get_open_orders(client: BinanceClient, symbol: str | None = None) -> list[dict]:
    """Return all open orders, optionally filtered by symbol."""
    return client.get_open_orders(symbol=symbol)


def format_order_response(response: dict[str, Any]) -> dict[str, str]:
    return {
        "Order ID": str(response.get("orderId", "—")),
        "Symbol": response.get("symbol", "—"),
        "Side": response.get("side", "—"),
        "Type": response.get("type", "—"),
        "Status": response.get("status", "—"),
        "Quantity": response.get("origQty", "—"),
        "Executed Qty": response.get("executedQty", "—"),
        "Price": response.get("price", "—"),
        "Avg Price": response.get("avgPrice", "—"),
        "Time In Force": response.get("timeInForce", "—"),
    }


def format_cancel_response(response: dict[str, Any]) -> dict[str, str]:
    return {
        "Order ID": str(response.get("orderId", "—")),
        "Symbol": response.get("symbol", "—"),
        "Side": response.get("side", "—"),
        "Type": response.get("type", "—"),
        "Status": response.get("status", "—"),
        "Quantity": response.get("origQty", "—"),
        "Executed Qty": response.get("executedQty", "—"),
    }


def format_open_orders(orders: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "Order ID": str(o.get("orderId", "—")),
            "Symbol": o.get("symbol", "—"),
            "Side": o.get("side", "—"),
            "Type": o.get("type", "—"),
            "Status": o.get("status", "—"),
            "Quantity": o.get("origQty", "—"),
            "Price": o.get("price", "—"),
        }
        for o in orders
    ]
