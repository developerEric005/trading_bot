import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("trading_bot.client")

BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000
TIMEOUT = 10.0

# Retry config: retries on transient network errors only
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5  # seconds, multiplied per attempt


class BinanceAPIError(Exception):
    def __init__(self, status_code: int, code: int, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message} (HTTP {status_code})")


class BinanceClient:
    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError(
                "API key and secret are required. "
                "Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file."
            )
        self._api_key = api_key
        self._api_secret = api_secret.encode("utf-8")
        self._http = httpx.Client(
            base_url=BASE_URL,
            timeout=TIMEOUT,
            headers={"X-MBX-APIKEY": self._api_key},
        )
        logger.debug("BinanceClient initialised (base_url=%s)", BASE_URL)

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret, query_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self, method: str, path: str, params: dict | None = None, signed: bool = True
    ) -> dict:
        params = dict(params or {})

        if signed:
            params = self._sign(params)

        log_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("→ %s %s params=%s", method.upper(), path, log_params)

        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if method.upper() == "GET":
                    response = self._http.get(path, params=params)
                else:
                    response = self._http.post(path, params=params)

                logger.debug("← HTTP %d | %s", response.status_code, response.text)

                data = response.json()

                if isinstance(data, dict) and "code" in data and data["code"] < 0:
                    raise BinanceAPIError(
                        status_code=response.status_code,
                        code=data["code"],
                        message=data.get("msg", "Unknown error"),
                    )

                response.raise_for_status()
                return data

            except BinanceAPIError:
                # API errors are not retryable (wrong params, bad balance, etc.)
                raise

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF * attempt
                    logger.warning(
                        "Network error on attempt %d/%d (%s). Retrying in %.1fs...",
                        attempt, MAX_RETRIES, type(exc).__name__, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "Request failed after %d attempts: %s", MAX_RETRIES, exc
                    )

        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------ #
    # Order methods                                                        #
    # ------------------------------------------------------------------ #

    def place_order(self, **params) -> dict:
        logger.info(
            "Placing %s %s order: %s qty=%s%s",
            params.get("side"),
            params.get("type"),
            params.get("symbol"),
            params.get("quantity"),
            f" price={params.get('price')}" if params.get("price") else "",
        )
        return self._request("POST", "/fapi/v1/order", params=params)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order by symbol + orderId."""
        logger.info("Cancelling order %s on %s", order_id, symbol)
        return self._request(
            "POST",
            "/fapi/v1/order/cancel",
            params={"symbol": symbol, "orderId": order_id},
        )

    def get_open_orders(self, symbol: str | None = None) -> list[dict]:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        logger.info("Fetching open orders%s", f" for {symbol}" if symbol else "")
        return self._request("GET", "/fapi/v1/openOrders", params=params)

    # ------------------------------------------------------------------ #
    # Account / exchange info                                              #
    # ------------------------------------------------------------------ #

    def get_exchange_info(self) -> dict:
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_account(self) -> dict:
        return self._request("GET", "/fapi/v2/account")

    # ------------------------------------------------------------------ #
    # Context manager                                                      #
    # ------------------------------------------------------------------ #

    def close(self):
        self._http.close()
        logger.debug("HTTP client closed.")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
