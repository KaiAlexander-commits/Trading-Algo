from threading import Event


_trading_enabled = Event()
_trading_enabled.set()


def is_trading_enabled() -> bool:
    return _trading_enabled.is_set()


def set_trading_enabled(enabled: bool) -> None:
    _trading_enabled.set() if enabled else _trading_enabled.clear()
