import unittest

from data.news_filter import NewsFilter


class NewsFilterTests(unittest.TestCase):
    def setUp(self):
        self.filter = NewsFilter(alpaca_client=None)

    def test_sentiment_counts_keywords(self):
        articles = [
            {"headline": "Company beats earnings after expansion", "summary": ""},
            {"headline": "Company faces lawsuit", "summary": ""},
        ]
        score, positive, negative = self.filter.analyze_news_sentiment(articles)
        self.assertEqual((positive, negative), (2, 1))
        self.assertAlmostEqual(score, 1 / 3)

    def test_empty_news_is_neutral(self):
        self.assertEqual(self.filter.analyze_news_sentiment([]), (0.0, 0, 0))


if __name__ == "__main__":
    unittest.main()
