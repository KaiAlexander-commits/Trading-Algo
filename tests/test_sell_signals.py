import unittest

from strategy.sell_signals import SellSignalDetector


class SellSignalDetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = SellSignalDetector(0.03, 0.03, 0.02)

    def test_profit_target(self):
        self.assertTrue(self.detector.should_sell("AAPL", 100, 103))

    def test_stop_loss(self):
        self.assertTrue(self.detector.should_sell("AAPL", 100, 97))

    def test_trailing_stop(self):
        self.assertFalse(self.detector.should_sell("AAPL", 100, 102))
        self.assertTrue(self.detector.should_sell("AAPL", 100, 99.9))

    def test_holds_without_signal(self):
        self.assertFalse(self.detector.should_sell("AAPL", 100, 101))


if __name__ == "__main__":
    unittest.main()
