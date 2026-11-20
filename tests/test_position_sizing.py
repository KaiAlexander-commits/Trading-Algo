import unittest
from types import SimpleNamespace

from strategy.position_sizing import PositionSizer


class FakeApi:
    def get_account(self):
        return SimpleNamespace(buying_power="10000", portfolio_value="10000")

    def get_bars(self, *_args):
        return []

    def get_position(self, _symbol):
        raise RuntimeError("No position")


class FakeClient:
    api = FakeApi()

    @staticmethod
    def get_current_price(_symbol):
        return 100.0


class PositionSizerTests(unittest.TestCase):
    def test_respects_dollar_cap(self):
        result = PositionSizer(FakeClient()).calculate_position_size(
            "AAPL", 100.0, account_balance=10000, max_dollars=20
        )
        self.assertEqual(result["shares"], 0.2)
        self.assertEqual(result["dollar_amount"], 20.0)

    def test_invalid_balance_produces_no_order(self):
        result = PositionSizer(FakeClient()).calculate_position_size(
            "AAPL", 100.0, account_balance=0
        )
        self.assertEqual(result["shares"], 0.0)


if __name__ == "__main__":
    unittest.main()
