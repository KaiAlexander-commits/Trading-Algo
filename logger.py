import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class TradeLogger:
    FIELDS = [
        "timestamp", "action", "symbol", "price", "quantity", "total_value",
        "profit", "profit_pct", "position_size_pct", "volatility_adj",
        "sentiment_adj", "news_sentiment", "atr", "stop_loss", "reason",
        "account_balance", "portfolio_value",
    ]

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        self.trades_csv = self.log_dir / f"trades_{today}.csv"
        self.daily_summary_json = self.log_dir / f"daily_summary_{today}.json"
        if not self.trades_csv.exists():
            with self.trades_csv.open("w", newline="", encoding="utf-8") as file:
                csv.DictWriter(file, fieldnames=self.FIELDS).writeheader()
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "total_volume": 0.0,
            "start_time": datetime.now().isoformat(),
            "symbols_traded": set(),
        }

    def log_trade(
        self, action: str, symbol: str, price: float, quantity: float,
        profit: Optional[float] = None, trade_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = trade_details or {}
        buy_price = details.get("buy_price")
        profit_pct = ((price - buy_price) / buy_price * 100) if profit is not None and buy_price else None
        record = {
            "timestamp": datetime.now().isoformat(), "action": action.upper(), "symbol": symbol,
            "price": round(price, 4), "quantity": round(quantity, 6),
            "total_value": round(price * quantity, 2),
            "profit": round(profit, 2) if profit is not None else None,
            "profit_pct": round(profit_pct, 2) if profit_pct is not None else None,
            "position_size_pct": details.get("position_pct"),
            "volatility_adj": details.get("volatility_adjustment"),
            "sentiment_adj": details.get("sentiment_adjustment"),
            "news_sentiment": details.get("news_sentiment"), "atr": details.get("atr"),
            "stop_loss": details.get("stop_loss_price"), "reason": details.get("reason", ""),
            "account_balance": details.get("account_balance"),
            "portfolio_value": details.get("portfolio_value"),
        }
        with self.trades_csv.open("a", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=self.FIELDS).writerow(record)
        self._update_stats(symbol, price * quantity, profit)
        self._print_trade(record)
        if self.stats["total_trades"] % 5 == 0:
            self._save_summary()

    def _update_stats(self, symbol: str, total_value: float, profit: Optional[float]) -> None:
        self.stats["total_trades"] += 1
        self.stats["total_volume"] += total_value
        self.stats["symbols_traded"].add(symbol)
        if profit is not None:
            self.stats["total_profit"] += profit
            key = "winning_trades" if profit > 0 else "losing_trades"
            self.stats[key] += 1

    @staticmethod
    def _print_trade(record: Dict[str, Any]) -> None:
        message = (
            f"[{datetime.now():%H:%M:%S}] {record['action']} {record['quantity']:.4f} shares "
            f"of {record['symbol']} at ${record['price']:.2f}"
        )
        if record["profit"] is not None:
            message += f" | Profit: ${record['profit']:.2f} ({record['profit_pct']:+.2f}%)"
        if record["reason"]:
            message += f" | Reason: {record['reason']}"
        print(message)

    def _save_summary(self) -> None:
        completed = self.stats["winning_trades"] + self.stats["losing_trades"]
        summary = {
            **self.stats,
            "symbols_traded": sorted(self.stats["symbols_traded"]),
            "win_rate": self.stats["winning_trades"] / completed * 100 if completed else 0.0,
            "last_updated": datetime.now().isoformat(),
        }
        with self.daily_summary_json.open("w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2)

    def get_session_summary(self) -> str:
        completed = self.stats["winning_trades"] + self.stats["losing_trades"]
        win_rate = self.stats["winning_trades"] / completed * 100 if completed else 0.0
        return (
            "Trading Session Summary\n"
            f"Trades: {self.stats['total_trades']} | Completed: {completed} | Win rate: {win_rate:.1f}%\n"
            f"Profit: ${self.stats['total_profit']:.2f} | Volume: ${self.stats['total_volume']:.2f} | "
            f"Symbols: {len(self.stats['symbols_traded'])}"
        )

    def log_system_event(self, event_type: str, message: str, details: Optional[Dict] = None) -> None:
        path = self.log_dir / "system_events.json"
        try:
            with path.open(encoding="utf-8") as file:
                events = json.load(file)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            events = []
        events.append({
            "timestamp": datetime.now().isoformat(), "event_type": event_type,
            "message": message, "details": details or {},
        })
        with path.open("w", encoding="utf-8") as file:
            json.dump(events[-1000:], file, indent=2)
        print(f"[{datetime.now():%H:%M:%S}] {event_type}: {message}")


_logger = None


def _get_logger() -> TradeLogger:
    global _logger
    if _logger is None:
        _logger = TradeLogger()
    return _logger


def log_enhanced_trade(action, symbol, price, quantity, profit=None, trade_details=None):
    _get_logger().log_trade(action, symbol, price, quantity, profit, trade_details)


def log_system_event(event_type, message, details=None):
    _get_logger().log_system_event(event_type, message, details)


def get_session_summary() -> str:
    return _get_logger().get_session_summary()
