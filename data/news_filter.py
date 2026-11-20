from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple


class NewsFilter:
    NEGATIVE_KEYWORDS = {
        "lawsuit", "investigation", "fraud", "bankruptcy", "downgrade",
        "earnings miss", "guidance cut", "recalled", "fda rejection", "suspended",
        "delisted", "data breach", "regulatory action", "profit warning",
    }
    POSITIVE_KEYWORDS = {
        "upgrade", "beats earnings", "strong guidance", "acquisition", "partnership",
        "breakthrough", "fda approval", "expansion", "growth", "outperform",
    }
    HIGH_IMPACT_KEYWORDS = {"earnings miss", "guidance cut", "lawsuit", "investigation", "suspended"}

    def __init__(self, alpaca_client):
        self.client = alpaca_client
        self._cache = {}
        self._cache_expiry = {}
        self._cache_duration = timedelta(minutes=30)

    def get_recent_news(self, symbol: str, hours_back: int = 24) -> List[Dict]:
        cache_key = (symbol, hours_back)
        now = datetime.now(timezone.utc)
        if now < self._cache_expiry.get(cache_key, datetime.min.replace(tzinfo=timezone.utc)):
            return self._cache[cache_key]

        try:
            articles = self.client.api.get_news(
                symbols=symbol,
                start=(now - timedelta(hours=hours_back)).isoformat() + "Z",
                end=now.isoformat() + "Z",
                sort="desc",
                limit=50,
            )
        except Exception as exc:
            print(f"Unable to get news for {symbol}: {exc}")
            return []

        news = [
            {
                "headline": article.headline,
                "summary": getattr(article, "summary", ""),
                "created_at": article.created_at,
                "url": getattr(article, "url", ""),
                "symbols": getattr(article, "symbols", []),
            }
            for article in articles
        ]
        self._cache[cache_key] = news
        self._cache_expiry[cache_key] = now + self._cache_duration
        return news

    def analyze_news_sentiment(self, articles: List[Dict]) -> Tuple[float, int, int]:
        positive = negative = 0
        for article in articles:
            text = f"{article.get('headline', '')} {article.get('summary', '')}".lower()
            positive += sum(keyword in text for keyword in self.POSITIVE_KEYWORDS)
            negative += sum(keyword in text for keyword in self.NEGATIVE_KEYWORDS)
        total = positive + negative
        score = (positive - negative) / total if total else 0.0
        return score, positive, negative

    def should_avoid_symbol(self, symbol: str, sentiment_threshold: float = -0.3) -> Tuple[bool, str]:
        news = self.get_recent_news(symbol)
        if not news:
            return False, "No recent news"
        score, positive, negative = self.analyze_news_sentiment(news)
        if score <= sentiment_threshold:
            return True, f"Negative sentiment: {score:.2f} (positive={positive}, negative={negative})"
        for headline in (article["headline"].lower() for article in news[:5]):
            match = next((keyword for keyword in self.HIGH_IMPACT_KEYWORDS if keyword in headline), None)
            if match:
                return True, f"High-impact negative event: {match}"
        return False, f"News sentiment acceptable: {score:.2f}"

    def filter_symbols_by_news(self, symbols: List[str], sentiment_threshold: float = -0.3):
        accepted, rejected = [], {}
        for symbol in symbols:
            avoid, reason = self.should_avoid_symbol(symbol, sentiment_threshold)
            if avoid:
                rejected[symbol] = reason
            else:
                accepted.append(symbol)
        return accepted, rejected
