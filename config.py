import os


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

TRADE_INTERVAL = 120
TRADES_PER_ROUND = 6
MAX_DOLLARS_PER_TRADE = 20
PROFIT_TARGET = 0.03
STOP_LOSS = 0.03
TRAILING_STOP_PERCENT = 0.02
RISK_PER_TRADE = 0.02
MAX_POSITION_PCT = 0.10
NEWS_SENTIMENT_THRESHOLD = -0.3
EMERGENCY_SELL_THRESHOLD = -0.5

SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX",
    "BA", "LMT", "NOC", "GE", "CAT", "DE", "JPM", "BAC", "GS", "WFC",
    "XOM", "CVX", "COP", "OXY", "SLB", "PFE", "MRNA", "JNJ", "ABBV", "LLY",
    "WMT", "TGT", "COST", "HD", "LOW", "MCD", "SBUX", "KO", "PEP", "PG",
    "DIS", "CMCSA", "VZ", "T", "BABA", "TSM", "SHOP", "SQ", "PYPL", "UBER",
    "SPY", "IVV", "VOO", "QQQ", "DIA", "IWM", "VTI", "XLK", "XLF", "XLV",
]


def validate_runtime_config() -> None:
    _required("ALPACA_API_KEY")
    _required("ALPACA_SECRET_KEY")
