from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from config import MAX_POSITION_PCT, RISK_PER_TRADE


class PositionSizer:
    def __init__(self, alpaca_client, risk_per_trade=RISK_PER_TRADE, max_position_pct=MAX_POSITION_PCT):
        self.client = alpaca_client
        self.risk_per_trade = risk_per_trade
        self.max_position_pct = max_position_pct
        self._atr_cache = {}

    def get_account_balance(self) -> float:
        try:
            return float(self.client.api.get_account().buying_power)
        except Exception as exc:
            print(f"Unable to get account buying power: {exc}")
            return 0.0

    def get_total_portfolio_value(self) -> float:
        try:
            return float(self.client.api.get_account().portfolio_value)
        except Exception as exc:
            print(f"Unable to get portfolio value: {exc}")
            return 0.0

    def calculate_atr(self, symbol: str, periods: int = 14) -> float:
        cached = self._atr_cache.get((symbol, periods))
        now = datetime.now(timezone.utc)
        if cached and cached[0] > now:
            return cached[1]
        try:
            end = now
            start = end - timedelta(days=30)
            bars = list(self.client.api.get_bars(
                symbol, "1Day", start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")
            ))
            if len(bars) < 2:
                price = self.client.get_current_price(symbol)
                atr = price * 0.02 if price else 0.0
            else:
                ranges = [
                    max(bar.h - bar.l, abs(bar.h - previous.c), abs(bar.l - previous.c))
                    for previous, bar in zip(bars, bars[1:])
                ]
                atr = sum(ranges[-periods:]) / min(len(ranges), periods)
            self._atr_cache[(symbol, periods)] = (now + timedelta(hours=1), atr)
            return atr
        except Exception as exc:
            print(f"Unable to calculate ATR for {symbol}: {exc}")
            return 0.0

    def calculate_position_size(
        self, symbol: str, entry_price: float, stop_loss_pct: float = 0.03,
        news_sentiment: float = 0.0, account_balance: Optional[float] = None,
        max_dollars: Optional[float] = None,
    ) -> Dict[str, float]:
        balance = self.get_account_balance() if account_balance is None else account_balance
        if balance <= 0 or entry_price <= 0 or stop_loss_pct <= 0:
            return self._empty_result()

        atr = self.calculate_atr(symbol)
        volatility_pct = atr / entry_price
        volatility_adjustment = 0.7 if volatility_pct > 0.05 else 0.85 if volatility_pct > 0.03 else 1.0
        sentiment_adjustment = 0.5 if news_sentiment < -0.5 else 0.75 if news_sentiment < -0.2 else 1.1 if news_sentiment > 0.3 else 1.0
        risk_shares = balance * self.risk_per_trade / (entry_price * stop_loss_pct)
        position_cap = balance * self.max_position_pct / entry_price
        dollar_cap = max_dollars / entry_price if max_dollars is not None else float("inf")
        shares = min(risk_shares * volatility_adjustment * sentiment_adjustment, position_cap, dollar_cap)
        if shares * entry_price < 10:
            return self._empty_result(atr, volatility_pct, volatility_adjustment, sentiment_adjustment)

        dollar_amount = shares * entry_price
        return {
            "shares": round(shares, 6), "dollar_amount": round(dollar_amount, 2),
            "risk_amount": round(shares * entry_price * stop_loss_pct, 2),
            "position_pct": round(dollar_amount / balance * 100, 2),
            "volatility_adjustment": volatility_adjustment, "sentiment_adjustment": sentiment_adjustment,
            "atr": round(atr, 4), "volatility_pct": round(volatility_pct * 100, 2),
        }

    @staticmethod
    def _empty_result(atr=0.0, volatility_pct=0.0, volatility_adjustment=1.0, sentiment_adjustment=1.0):
        return {
            "shares": 0.0, "dollar_amount": 0.0, "risk_amount": 0.0, "position_pct": 0.0,
            "volatility_adjustment": volatility_adjustment, "sentiment_adjustment": sentiment_adjustment,
            "atr": round(atr, 4), "volatility_pct": round(volatility_pct * 100, 2),
        }

    def get_current_position_value(self, symbol: str) -> float:
        try:
            return float(self.client.api.get_position(symbol).market_value)
        except Exception:
            return 0.0

    def check_position_limits(self, symbol: str, planned_investment: float) -> Tuple[bool, str]:
        portfolio = self.get_total_portfolio_value()
        if portfolio <= 0:
            return False, "Portfolio value unavailable"
        position_pct = (self.get_current_position_value(symbol) + planned_investment) / portfolio
        if position_pct > self.max_position_pct:
            return False, f"Position would be {position_pct:.1%} of portfolio (max {self.max_position_pct:.1%})"
        return True, f"Position would be {position_pct:.1%} of portfolio"
