import re
from decimal import Decimal, InvalidOperation

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}

# Allow digits in symbol names (e.g. 1INCHUSDT, BTCUSDT)
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,20}$")

# Minimum meaningful quantity (avoids Binance rejecting dust amounts)
MIN_QUANTITY = Decimal("0.00001")


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(symbol):
        raise ValueError(
            f"Invalid symbol '{symbol}'. "
            "Expected uppercase letters/digits only (e.g. BTCUSDT, 1INCHUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> str:
    try:
        qty = Decimal(str(quantity))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")

    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")

    if qty < MIN_QUANTITY:
        raise ValueError(
            f"Quantity {qty} is too small (minimum {MIN_QUANTITY}). "
            "Binance will reject dust quantities."
        )

    return str(qty)


def validate_price(price: str | float | None, order_type: str) -> str | None:
    if order_type == "MARKET":
        return None

    if price is None:
        raise ValueError("Price is required for LIMIT orders.")

    try:
        p = Decimal(str(price))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")

    if p <= 0:
        raise ValueError(f"Price must be positive, got {p}.")

    return str(p)
