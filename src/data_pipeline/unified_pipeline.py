"""
Unified Data Pipeline Orchestrator
Coordinates daily, intraday, fundamentals, and news ingestion with feature store exports.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..api.config import settings
from .daily_price_fetcher import DailyPriceFetcher
from .data_integration_service import DataIntegrationService
from .fundamentals_ingestion import FundamentalsIngestionService
from .intraday_price_fetcher import IntradayPriceFetcher
from .multi_asset_fetcher import GoldFetcher, ForexFetcher, BinanceFetcher, MultiAssetRetentionCleaner
from .news_ingestion import NewsIngestionService
from ..shared.feature_store import FeatureStore, FeatureStoreConfig
from ..domains.market_data.application.amt_service import AuctionMarketTheoryService

logger = logging.getLogger(__name__)


@dataclass
class PipelineRunConfig:
    stock_codes: Optional[List[str]] = None
    intraday_intervals: Iterable[str] = ("5m",)
    fundamentals_frequency: str = "weekly"  # daily, weekly, monthly
    news_max_articles: int = 15
    export_feature_store: bool = True


class UnifiedDataPipeline:
    """
    High-level orchestrator aligning all ingestion steps.
    Designed for cron-based execution or manual triggers.
    """

    def __init__(
        self,
        *,
        db_url: Optional[str] = None,
        feature_store_path: Path = Path("data/feature_store"),
    ) -> None:
        self.db_url = db_url or self._build_db_url()
        self.engine = create_engine(self.db_url, pool_pre_ping=True)
        self.SessionFactory = sessionmaker(bind=self.engine)
        self.feature_store = FeatureStore(
            FeatureStoreConfig(root_path=feature_store_path, categories=("ml", "llm", "amt"))
        )

    def run_end_of_day(self, config: PipelineRunConfig = PipelineRunConfig()) -> None:
        with self.session_scope() as session:
            self._run_retention_cleanup(session)
            self._run_daily_prices(session, config.stock_codes)
            self._run_intraday(session, config.stock_codes, config.intraday_intervals)
            self._run_news(session, config.stock_codes, config.news_max_articles)
            self._maybe_run_fundamentals(session, config.stock_codes, config.fundamentals_frequency)
            self._run_multi_asset(session)
            if config.export_feature_store:
                self._export_feature_store(session, config.stock_codes)

    # ------------------------------------------------------------------ #
    # Individual pipeline stages
    # ------------------------------------------------------------------ #

    def _run_daily_prices(self, session: Session, stock_codes: Optional[List[str]]) -> None:
        fetcher = DailyPriceFetcher(session)
        results, job_id = fetcher.fetch_daily_prices(stock_codes=stock_codes, backfill_days=7)
        successful = len([r for r in results if r.success])
        logger.info("Daily price fetch completed (job=%s). Successful=%s", job_id, successful)
        if successful == 0:
            raise RuntimeError(
                "Daily price fetch returned no data. Verify network access to yahoo finance endpoints "
                "or adjust data source configuration before continuing."
            )

    def _run_intraday(
        self,
        session: Session,
        stock_codes: Optional[List[str]],
        intervals: Iterable[str],
    ) -> None:
        fetcher = IntradayPriceFetcher(session)
        for index, interval in enumerate(intervals):
            results, job_id = fetcher.fetch_intraday_prices(
                stock_codes=stock_codes,
                interval=interval,
                lookback_minutes=390 if interval in {"1m", "2m", "5m"} else 1440,
            )
            logger.info(
                "Intraday fetch interval=%s job=%s inserted=%s",
                interval,
                job_id,
                sum(r.records_fetched for r in results if r.success),
            )
            if index == 0:
                processed_codes = [r.stock_code for r in results if r.success]
                if processed_codes:
                    self._run_amt_profiles(session, processed_codes, datetime.utcnow().date())

    def _maybe_run_fundamentals(
        self,
        session: Session,
        stock_codes: Optional[List[str]],
        frequency: str,
    ) -> None:
        should_run = self._should_run_fundamentals(frequency)
        if not should_run:
            logger.info("Skipping fundamentals ingestion (frequency=%s)", frequency)
            return
        service = FundamentalsIngestionService(session)
        results, job_id = service.ingest_fundamentals(stock_codes=stock_codes)
        logger.info(
            "Fundamentals ingestion job=%s saved_reports=%s saved_metrics=%s",
            job_id,
            sum(r.reports_saved for r in results if r.success),
            sum(r.metrics_saved for r in results if r.success),
        )

    def _run_news(
        self,
        session: Session,
        stock_codes: Optional[List[str]],
        max_articles: int,
    ) -> None:
        service = NewsIngestionService(session)
        results, job_id = service.ingest_market_news(
            stock_codes=stock_codes,
            max_articles=max_articles,
        )
        logger.info(
            "News ingestion job=%s total_articles=%s",
            job_id,
            sum(r.articles_saved for r in results if r.success),
        )

    def _run_amt_profiles(
        self,
        session: Session,
        stock_codes: List[str],
        session_date: date,
    ) -> None:
        service = AuctionMarketTheoryService(session)
        for code in stock_codes:
            results = service.compute_range(code, session_date, session_date)
            logger.info(
                "AMT profiles computed for %s on %s (success=%s)",
                code,
                session_date,
                sum(1 for r in results if r.success),
            )

    def _run_retention_cleanup(self, session: Session) -> None:
        cleaner = MultiAssetRetentionCleaner(session)
        deleted = cleaner.purge_old_1m_data(retain_days=60)
        logger.info("Retention cleanup: removed %s stale 1m crypto rows", deleted)

    def _run_multi_asset(self, session: Session) -> None:
        gold_results, gold_job = GoldFetcher(session).fetch(backfill_days=3)
        logger.info(
            "Gold fetch job=%s success=%s records=%s",
            gold_job, gold_results[0].success, gold_results[0].records_fetched,
        )

        forex_results, forex_job = ForexFetcher(session, symbol="USDIDR=X").fetch(backfill_days=3)
        logger.info(
            "Forex fetch job=%s success=%s records=%s",
            forex_job, forex_results[0].success, forex_results[0].records_fetched,
        )

        btc_results, btc_job = BinanceFetcher(session).fetch(lookback_minutes=1440)
        logger.info(
            "BTC 1m fetch job=%s success=%s records=%s",
            btc_job, btc_results[0].success, btc_results[0].records_fetched,
        )

    def _export_feature_store(self, session: Session, stock_codes: Optional[List[str]]) -> None:
        integration = DataIntegrationService(session)
        feature_payload = integration.prepare_feature_data_for_ml(
            stock_codes=stock_codes,
            include_fundamentals=True,
            include_news=True,
        )
        price_data = feature_payload.get("price_data", None)
        metadata = feature_payload.get("metadata", None)
        fundamentals = feature_payload.get("fundamental_data", None)
        news_data = feature_payload.get("news_data", None)
        amt_data = feature_payload.get("amt_data", None)

        if price_data is not None and not price_data.empty:
            self.feature_store.write_dataset(
                name="daily_prices",
                category="ml",
                frame=price_data,
                metadata={"source": "database", "generated_at": datetime.utcnow().isoformat()},
                overwrite=True,
            )
        if fundamentals is not None and not fundamentals.empty:
            self.feature_store.write_dataset(
                name="fundamentals",
                category="ml",
                frame=fundamentals,
                metadata={"source": "database"},
                overwrite=True,
            )
        if metadata is not None and not metadata.empty:
            self.feature_store.write_dataset(
                name="stock_metadata",
                category="llm",
                frame=metadata,
                metadata={"source": "database"},
                overwrite=True,
            )
        if news_data is not None and not news_data.empty:
            self.feature_store.write_dataset(
                name="news_articles",
                category="llm",
                frame=news_data,
                metadata={"source": "database"},
                overwrite=True,
            )
        if amt_data is not None and not amt_data.empty:
            self.feature_store.write_dataset(
                name="auction_market_profiles",
                category="amt",
                frame=amt_data,
                metadata={"source": "database"},
                overwrite=True,
            )
        logger.info("Feature store export completed.")

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def _build_db_url(self) -> str:
        try:
            return (
                f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
                f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            )
        except Exception:
            return "sqlite:///data/trading_system.db"

    @contextmanager
    def session_scope(self):
        session: Session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _should_run_fundamentals(frequency: str) -> bool:
        today = datetime.utcnow()
        if frequency == "daily":
            return True
        if frequency == "weekly":
            return today.weekday() == 0  # Monday UTC
        if frequency == "monthly":
            return today.day <= 3  # first three days
        return False


__all__ = ["UnifiedDataPipeline", "PipelineRunConfig"]
