"""
Market News Ingestion Pipeline
Collects public news feeds, normalizes content, and enriches articles with sentiment
for downstream LLM agents and dashboards.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..api.database_extensions import DataRefreshLog, MarketNewsArticle, StockMaster

logger = logging.getLogger(__name__)

GOOGLE_NEWS_ENDPOINT = "https://news.google.com/rss/search"
BISNIS_ENDPOINT = "https://www.bisnis.com/rss"


@dataclass
class NewsIngestionResult:
    stock_code: str
    articles_saved: int
    success: bool
    error_message: Optional[str] = None


class SentimentAnalyzer:
    """
    Lazy sentiment analyzer that prefers domain-specific transformer models.
    Falls back to rule-based scoring if transformers are unavailable.
    """

    def __init__(
        self,
        model_name: str = "ProsusAI/finbert",
        use_gpu: bool = False,
    ) -> None:
        self.model_name = model_name
        self.use_gpu = use_gpu
        self._pipeline = None

    def score(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        if not text:
            return None, None
        pipe = self._ensure_pipeline()
        if pipe is None:
            return self._fallback_score(text)
        try:
            result = pipe(text[:512])[0]
            label = result.get("label", "").lower()
            score = float(result.get("score", 0.0))
            if label in {"positive", "negative"}:
                sentiment_score = score if label == "positive" else -score
            else:
                sentiment_score = 0.0
            return sentiment_score, label
        except Exception as exc:
            logger.debug("Sentiment pipeline failed (%s), falling back: %s", self.model_name, exc)
            return self._fallback_score(text)

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline  # type: ignore

            device = 0 if self.use_gpu else -1
            self._pipeline = pipeline("sentiment-analysis", model=self.model_name, device=device)
        except Exception:
            self._pipeline = None
        return self._pipeline

    @staticmethod
    def _fallback_score(text: str) -> Tuple[Optional[float], Optional[str]]:
        positive_keywords = {"gain", "rally", "upgrade", "profit", "beat"}
        negative_keywords = {"loss", "downgrade", "fall", "lawsuit", "fraud"}

        text_lower = text.lower()
        pos_hits = sum(1 for word in positive_keywords if word in text_lower)
        neg_hits = sum(1 for word in negative_keywords if word in text_lower)

        if pos_hits == neg_hits == 0:
            return 0.0, "neutral"
        sentiment = pos_hits - neg_hits
        label = "positive" if sentiment > 0 else "negative"
        score = min(1.0, max(-1.0, sentiment / 5))
        return score, label


class NewsIngestionService:
    """
    Aggregates news across Google News and Indonesian finance outlets.
    Persists deduplicated articles with sentiment metadata.
    """

    def __init__(
        self,
        db_session: Session,
        *,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        throttle_seconds: float = 2.0,
        default_language: str = "en",
    ) -> None:
        self.db_session = db_session
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        self.throttle_seconds = throttle_seconds
        self.default_language = default_language

    def ingest_market_news(
        self,
        *,
        stock_codes: Optional[List[str]] = None,
        country: str = "ID",
        max_articles: int = 20,
    ) -> Tuple[List[NewsIngestionResult], str]:
        stocks = self._resolve_symbols(stock_codes)
        if not stocks:
            raise ValueError("No active stocks available for news scraping.")

        job_id, job_log = self._start_job(stocks, country, max_articles)

        results: List[NewsIngestionResult] = []
        total_articles = 0
        total_failed = 0

        try:
            for stock in stocks:
                try:
                    articles = self._collect_articles(
                        stock_code=stock.stock_code,
                        company_name=stock.company_name,
                        country=country,
                        max_articles=max_articles,
                    )
                    saved = self._persist_articles(stock.stock_code, articles)
                    results.append(
                        NewsIngestionResult(
                            stock_code=stock.stock_code,
                            articles_saved=saved,
                            success=True,
                        )
                    )
                    total_articles += saved
                except Exception as exc:
                    logger.warning("News ingestion failed for %s: %s", stock.stock_code, exc)
                    results.append(
                        NewsIngestionResult(
                            stock_code=stock.stock_code,
                            articles_saved=0,
                            success=False,
                            error_message=str(exc),
                        )
                    )
                    total_failed += 1

                time.sleep(self.throttle_seconds)

            job_log.completed_at = datetime.utcnow()
            job_log.status = "completed" if total_failed == 0 else "partial"
            job_log.records_inserted = total_articles
            job_log.records_processed = total_articles
            job_log.records_failed = total_failed
            job_log.duration_seconds = (job_log.completed_at - job_log.started_at).total_seconds()
            self.db_session.commit()
            return results, job_id
        except Exception as exc:
            logger.exception("News ingestion job %s failed: %s", job_id, exc)
            job_log.status = "failed"
            job_log.completed_at = datetime.utcnow()
            job_log.error_message = str(exc)
            self.db_session.commit()
            raise

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _resolve_symbols(self, stock_codes: Optional[List[str]]) -> List[StockMaster]:
        query = self.db_session.query(StockMaster).filter(StockMaster.is_active.is_(True))
        if stock_codes:
            query = query.filter(StockMaster.stock_code.in_(stock_codes))
        return query.all()

    def _start_job(
        self,
        stocks: List[StockMaster],
        country: str,
        max_articles: int,
    ) -> Tuple[str, DataRefreshLog]:
        job = DataRefreshLog(
            job_name="news_ingest",
            job_type="news",
            started_at=datetime.utcnow(),
            status="running",
            stock_codes=[s.stock_code for s in stocks],
            meta_data={
                "country": country,
                "max_articles": max_articles,
                "providers": ["google_news", "bisnis"],
            },
        )
        self.db_session.add(job)
        self.db_session.commit()
        return str(job.id), job

    def _collect_articles(
        self,
        *,
        stock_code: str,
        company_name: str,
        country: str,
        max_articles: int,
    ) -> List[dict]:
        queries = [
            f"{company_name} {stock_code} IDX",
            f"{stock_code}.JK",
            f"{company_name} saham",
        ]

        articles: List[dict] = []
        seen_urls = set()

        for query in queries:
            google_results = self._fetch_google_news(query=query, country=country, limit=max_articles)
            for article in google_results:
                if article["source_url"] in seen_urls:
                    continue
                articles.append(article)
                seen_urls.add(article["source_url"])

        bisnis_results = self._fetch_bisnis_feed(stock_code, company_name)
        for article in bisnis_results:
            if article["source_url"] in seen_urls:
                continue
            articles.append(article)
            seen_urls.add(article["source_url"])

        return articles[:max_articles]

    def _fetch_google_news(self, *, query: str, country: str, limit: int) -> List[dict]:
        params = {
            "q": quote_plus(query),
            "hl": f"{self.default_language}-{country}",
            "gl": country,
            "ceid": f"{country}:{self.default_language}",
        }
        response = requests.get(GOOGLE_NEWS_ENDPOINT, params=params, timeout=20)
        response.raise_for_status()

        root = ElementTree.fromstring(response.content)
        items = root.findall("./channel/item")
        articles: List[dict] = []

        for item in items[:limit]:
            title = self._strip_html(item.findtext("title", default=""))
            link = item.findtext("link", default="")
            description = self._strip_html(item.findtext("{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}description", default=""))
            pub_date_raw = item.findtext("pubDate")
            published_at = self._parse_pub_date(pub_date_raw)
            sentiment_score, sentiment_label = self.sentiment_analyzer.score(f"{title}. {description}")

            articles.append(
                dict(
                    title=title,
                    summary=description,
                    content=None,
                    source="google_news",
                    source_url=link,
                    published_at=published_at,
                    sentiment_score=sentiment_score,
                    sentiment_label=sentiment_label,
                    language=self.default_language,
                    topics=None,
                )
            )
        return articles

    def _fetch_bisnis_feed(self, stock_code: str, company_name: str) -> List[dict]:
        response = requests.get(BISNIS_ENDPOINT, timeout=20)
        if not response.ok:
            return []

        root = ElementTree.fromstring(response.content)
        items = root.findall("./channel/item")
        keywords = {stock_code.lower(), company_name.lower()}

        results: List[dict] = []
        for item in items:
            title = self._strip_html(item.findtext("title", default=""))
            description = self._strip_html(item.findtext("description", default=""))
            text = f"{title} {description}".lower()
            if not any(keyword in text for keyword in keywords):
                continue
            link = item.findtext("link", default="")
            pub_date_raw = item.findtext("pubDate")
            published_at = self._parse_pub_date(pub_date_raw)
            sentiment_score, sentiment_label = self.sentiment_analyzer.score(f"{title}. {description}")
            results.append(
                dict(
                    title=title,
                    summary=description,
                    content=None,
                    source="bisnis",
                    source_url=link,
                    published_at=published_at,
                    sentiment_score=sentiment_score,
                    sentiment_label=sentiment_label,
                    language="id",
                    topics=["local_news"],
                )
            )
        return results

    def _persist_articles(self, stock_code: str, articles: List[dict]) -> int:
        if not articles:
            return 0

        now = datetime.utcnow()
        records = []
        for article in articles:
            record = dict(
                stock_codes=[stock_code],
                sector_tags=None,
                country="ID",
                title=article["title"][:500],
                summary=article.get("summary"),
                content=article.get("content"),
                language=article.get("language", self.default_language),
                source=article["source"],
                source_url=article["source_url"][:500],
                author=None,
                published_at=article.get("published_at"),
                fetched_at=now,
                sentiment_score=article.get("sentiment_score"),
                sentiment_label=article.get("sentiment_label"),
                embedding_vector=None,
                topics=article.get("topics"),
                meta_data={"ingested_at": now.isoformat()},
            )
            records.append(record)

        stmt = pg_insert(MarketNewsArticle).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source_url"],
            set_={
                "summary": stmt.excluded.summary,
                "content": stmt.excluded.content,
                "sentiment_score": stmt.excluded.sentiment_score,
                "sentiment_label": stmt.excluded.sentiment_label,
                "topics": stmt.excluded.topics,
                "meta_data": stmt.excluded.meta_data,
                "updated_at": datetime.utcnow(),
            },
        )
        self.db_session.execute(stmt)
        self.db_session.flush()
        return len(records)

    @staticmethod
    def _strip_html(raw: Optional[str]) -> str:
        if not raw:
            return ""
        return re.sub("<[^<]+?>", "", raw)

    @staticmethod
    def _parse_pub_date(raw: Optional[str]) -> Optional[datetime]:
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S %Z")
        except ValueError:
            return None


__all__ = ["NewsIngestionService", "NewsIngestionResult", "SentimentAnalyzer"]
