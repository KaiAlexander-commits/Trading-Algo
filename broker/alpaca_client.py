from datetime import datetime, timedelta

import alpaca_trade_api as tradeapi
import pandas as pd

from config import SYMBOLS, TRADES_PER_ROUND


class AlpacaClient:
    def __init__(self, key: str, secret: str, url: str):
        self.api = tradeapi.REST(key, secret, url)
        self.symbols = SYMBOLS
        self.trades_per_round = TRADES_PER_ROUND

    def get_current_price(self, symbol: str):
        try:
            return self.api.get_last_trade(symbol).price
        except Exception as exc:
            print(f"Unable to get price for {symbol}: {exc}")
            return None

    def buy(self, symbol: str, quantity: float) -> bool:
        try:
            self.api.submit_order(symbol, str(round(quantity, 6)), "buy", "market", "gtc")
            return True
        except Exception as exc:
            print(f"Unable to buy {symbol}: {exc}")
            return False

    def sell(self, symbol: str, quantity: float) -> bool:
        try:
            self.api.submit_order(symbol, str(round(quantity, 6)), "sell", "market", "gtc")
            return True
        except Exception as exc:
            print(f"Unable to sell {symbol}: {exc}")
            return False

    def get_historical_data(self, symbol: str, window: int = 5) -> pd.DataFrame:
        try:
            end = datetime.utcnow()
            start = end - timedelta(minutes=window)
            bars = self.api.get_bars(
                symbol,
                "1Min",
                start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            return pd.DataFrame({"close": [bar.c for bar in bars]})
        except Exception as exc:
            print(f"Unable to get historical data for {symbol}: {exc}")
            return pd.DataFrame()
