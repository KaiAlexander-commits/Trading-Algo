import unittest

from trading_state import is_trading_enabled, set_trading_enabled


class TradingStateTests(unittest.TestCase):
    def tearDown(self):
        set_trading_enabled(True)

    def test_trading_can_be_enabled_and_disabled(self):
        set_trading_enabled(False)
        self.assertFalse(is_trading_enabled())
        set_trading_enabled(True)
        self.assertTrue(is_trading_enabled())


if __name__ == "__main__":
    unittest.main()
