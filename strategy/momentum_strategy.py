from datetime import datetime

from config import EMERGENCY_SELL_THRESHOLD, NEWS_SENTIMENT_THRESHOLD, STOP_LOSS
from data.news_filter import NewsFilter
from logger import log_enhanced_trade, log_system_event
from strategy.position_sizing import PositionSizer


class MomentumStrategy:
    def __init__(self, client, sell_detector):
        self.client = client
        self.sell_detector = sell_detector
        self.positions = {}
        self.news_filter = NewsFilter(client)
        self.position_sizer = PositionSizer(client)

    def pick_symbols_to_buy(self, limit):
        changes = []
        for symbol in self.client.symbols:
            prices = self.client.get_historical_data(symbol, window=5)
            if len(prices) >= 2 and prices["close"].iloc[0] > 0:
                change = prices["close"].iloc[-1] / prices["close"].iloc[0] - 1
                if change > 0:
                    changes.append((symbol, change))
        candidates = [symbol for symbol, _ in sorted(changes, key=lambda item: item[1], reverse=True)]
        accepted, rejected = self.news_filter.filter_symbols_by_news(
            candidates[: limit * 2], NEWS_SENTIMENT_THRESHOLD
        )
        if rejected:
            log_system_event("NEWS_FILTER", f"Excluded: {', '.join(rejected)}")
        return accepted[:limit]

    def buy_round(self, max_dollars):
        trades = []
        for symbol in self.pick_symbols_to_buy(self.client.trades_per_round):
            try:
                if symbol in self.positions:
                    continue
                price = self.client.get_current_price(symbol)
                if not price:
                    continue
                sentiment, _, _ = self.news_filter.analyze_news_sentiment(
                    self.news_filter.get_recent_news(symbol)
                )
                position = self.position_sizer.calculate_position_size(
                    symbol, price, news_sentiment=sentiment, max_dollars=max_dollars
                )
                quantity = position["shares"]
                if quantity <= 0:
                    continue
                allowed, reason = self.position_sizer.check_position_limits(symbol, position["dollar_amount"])
                if not allowed:
                    log_system_event("BUY_SKIP", f"{symbol}: {reason}")
                    continue
                if not self.client.buy(symbol, quantity):
                    continue

                self.positions[symbol] = (price, quantity, sentiment, datetime.now())
                details = {
                    **position,
                    "news_sentiment": sentiment,
                    "account_balance": self.position_sizer.get_account_balance(),
                    "portfolio_value": self.position_sizer.get_total_portfolio_value(),
                    "stop_loss_price": price * (1 - STOP_LOSS),
                }
                log_enhanced_trade("buy", symbol, price, quantity, trade_details=details)
                trades.append((symbol, price, quantity))
            except Exception as exc:
                log_system_event("BUY_ERROR", f"{symbol}: {exc}")
        return trades

    def check_and_sell(self):
        results = []
        for symbol, (buy_price, quantity, entry_sentiment, entry_time) in list(self.positions.items()):
            try:
                current_price = self.client.get_current_price(symbol)
                if not current_price:
                    continue
                avoid, news_reason = self.news_filter.should_avoid_symbol(
                    symbol, EMERGENCY_SELL_THRESHOLD
                )
                emergency = avoid and news_reason.startswith("High-impact")
                technical = self.sell_detector.should_sell(symbol, buy_price, current_price)
                if not (emergency or technical):
                    continue

                if emergency:
                    reason = f"Emergency: {news_reason}"
                else:
                    change = (current_price - buy_price) / buy_price
                    reason = "Profit target reached" if change >= self.sell_detector.profit_target else (
                        "Stop loss triggered" if change <= -self.sell_detector.stop_loss else "Trailing stop triggered"
                    )
                if not self.client.sell(symbol, quantity):
                    continue

                profit = (current_price - buy_price) * quantity
                log_enhanced_trade(
                    "sell", symbol, current_price, quantity, profit,
                    {
                        "buy_price": buy_price,
                        "reason": reason,
                        "news_sentiment": entry_sentiment,
                        "holding_period": str(datetime.now() - entry_time),
                        "account_balance": self.position_sizer.get_account_balance(),
                        "portfolio_value": self.position_sizer.get_total_portfolio_value(),
                    },
                )
                results.append((symbol, buy_price, current_price, quantity, profit))
                del self.positions[symbol]
                self.sell_detector.highest.pop(symbol, None)
            except Exception as exc:
                log_system_event("SELL_ERROR", f"{symbol}: {exc}")
        return results
