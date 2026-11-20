import asyncio
import threading
import time
from datetime import datetime

import pytz

from broker.alpaca_client import AlpacaClient
from config import (
    ALPACA_API_KEY, ALPACA_BASE_URL, ALPACA_SECRET_KEY, MAX_DOLLARS_PER_TRADE,
    PROFIT_TARGET, STOP_LOSS, TRADE_INTERVAL, TRAILING_STOP_PERCENT,
    validate_runtime_config,
)
from logger import get_session_summary, log_system_event
from messaging.notify import discord_bot, send_notification
from strategy.momentum_strategy import MomentumStrategy
from strategy.sell_signals import SellSignalDetector
from trading_state import is_trading_enabled, set_trading_enabled

client = None
strategy = None


def initialize_runtime() -> None:
    global client, strategy
    if client is not None:
        return
    validate_runtime_config()
    client = AlpacaClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
    sell_detector = SellSignalDetector(PROFIT_TARGET, STOP_LOSS, TRAILING_STOP_PERCENT)
    strategy = MomentumStrategy(client, sell_detector)


def run_discord_bot() -> None:
    if discord_bot:
        asyncio.run(discord_bot.start_bot())


def check_market_status():
    initialize_runtime()
    clock = client.api.get_clock()
    return clock.is_open, clock.next_open, clock.next_close


def notify_market_status(is_open: bool) -> None:
    state = "OPEN" if is_open else "CLOSED"
    send_notification(f"Market is now {state}. Trading {'resumed' if is_open else 'paused'}.")


def _notify_trades(buys=(), sells=()) -> None:
    for symbol, price, quantity in buys:
        send_notification(f"Bought {quantity:.4f} shares of {symbol} at ${price:.2f}")
    for symbol, buy_price, sell_price, quantity, profit in sells:
        profit_pct = ((sell_price - buy_price) / buy_price) * 100
        send_notification(
            f"Sold {quantity:.4f} shares of {symbol} at ${sell_price:.2f}; "
            f"profit: ${profit:.2f} ({profit_pct:+.2f}%)"
        )


def run_trading_bot() -> None:
    initialize_runtime()
    log_system_event("BOT_START", "Trading bot starting")
    is_open, next_open, _ = check_market_status()
    current_time = datetime.now(pytz.timezone("US/Eastern"))
    status = "OPEN" if is_open else f"CLOSED; next open: {next_open}"
    send_notification(f"Trading bot started at {current_time:%Y-%m-%d %H:%M:%S %Z}. Market: {status}")

    previous_market_open = is_open
    loop_counter = 0
    while True:
        loop_counter += 1
        is_open, _, _ = check_market_status()
        if is_open != previous_market_open:
            notify_market_status(is_open)
            previous_market_open = is_open

        if is_open and is_trading_enabled():
            _notify_trades(buys=strategy.buy_round(MAX_DOLLARS_PER_TRADE))
            time.sleep(TRADE_INTERVAL)
            _notify_trades(sells=strategy.check_and_sell())
        elif is_open:
            _notify_trades(sells=strategy.check_and_sell())
            time.sleep(60)
        else:
            time.sleep(60)

        if loop_counter % 30 == 0:
            print(get_session_summary())


def main() -> None:
    if discord_bot:
        threading.Thread(target=run_discord_bot, daemon=True).start()
        for _ in range(10):
            if discord_bot.is_ready:
                break
            time.sleep(1)
    run_trading_bot()


if __name__ == "__main__":
    main()
