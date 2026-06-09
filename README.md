You'll need Python 3.10+ and a Binance Futures Testnet account.

1. Go to https://testnet.binancefuture.com, sign in with GitHub, and grab an API key + secret.

2. Clone the repo and install deps:

```
git clone <repo-url>
cd trading_bot
python -m venv venv
venv\Scripts\activate        # on Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your credentials:

```
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
```

## Usage

Place a market buy:

```
python cli.py place-order -s BTCUSDT -S BUY -t MARKET -q 0.001
```

Place a limit sell:

```
python cli.py place-order -s ETHUSDT -S SELL -t LIMIT -q 0.05 -p 3500
```

Preview an order without sending it (dry run):

```
python cli.py place-order -s BTCUSDT -S BUY -t MARKET -q 0.001 --dry-run
```

Skip the confirmation prompt:

```
python cli.py place-order -s BTCUSDT -S BUY -t MARKET -q 0.001 --yes
```

Cancel an open order:

```
python cli.py cancel-order -s BTCUSDT -i 123456789
```

List all open orders:

```
python cli.py list-orders
```

List open orders for a specific symbol:

```
python cli.py list-orders -s BTCUSDT
```

Run `python cli.py -h` or `python cli.py <command> -h` to see all options.

## Project structure

```
bot/
  client.py          - Binance API client, handles signing, HTTP, and retries
  orders.py          - order placement, cancel, query, and response formatting
  validators.py      - input validation (symbol, side, qty, price)
  logging_config.py  - sets up file + console logging
cli.py               - CLI entry point (Click) with place-order, cancel-order, list-orders
```

## Logging

All requests and responses are logged to `logs/trading_bot.log` at DEBUG level. The console only shows INFO and above so it stays clean.

You can check the log file to see exactly what was sent to the API and what came back — useful for debugging.

## Error handling

- Missing or invalid inputs are caught before hitting the API
- Binance error responses (wrong symbol, insufficient balance, etc.) are parsed and displayed
- Network timeouts and connection failures are retried up to 3 times with backoff
- If something unexpected happens, the full traceback goes to the log file

## Assumptions

- This only works against the testnet (`https://testnet.binancefuture.com`). Don't point it at production.
- Uses USDT-margined futures (`/fapi/v1/order`).
- Limit orders default to GTC (Good-Til-Cancelled).
- No position tracking or auto-closing — it just places and manages individual orders.

## Dependencies

- `httpx` – HTTP client
- `click` – CLI argument parsing
- `python-dotenv` – loads `.env` file
- `rich` – colored terminal output
