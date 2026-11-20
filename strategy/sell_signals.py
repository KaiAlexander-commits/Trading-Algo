class SellSignalDetector:
    def __init__(self, profit_target, stop_loss, trailing_stop):
        self.profit_target = profit_target
        self.stop_loss = stop_loss
        self.trailing_stop = trailing_stop
        self.highest = {}

    def should_sell(self, symbol, buy_price, current_price):
        if symbol not in self.highest:
            self.highest[symbol] = buy_price

        self.highest[symbol] = max(self.highest[symbol], current_price)

        gain_ratio = (current_price - buy_price) / buy_price
        if gain_ratio >= self.profit_target:
            return True

        if gain_ratio <= -self.stop_loss:
            return True

        if current_price < self.highest[symbol] * (1 - self.trailing_stop):
            return True

        return False
