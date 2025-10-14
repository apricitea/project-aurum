"""
Intraday Stock Price Fetcher
Collects multi-interval OHLCV bars for IDX symbols from public sources
Supports Yahoo Finance as primary provider with pluggable fallback scrapers
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..api.database_extensions import (
    DataRefreshLog,
    IntradayStockPrice,
    StockMaster,
)

logger = logging.getLogger(__name__)


SUPPORTED_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m"}


@dataclass
class IntradayFetchResult:
    stock_code: str
    interval: str
    success: bool
    records_fetched: int
    error_message: Optional[str] = None
    data_quality_score: Optional[float] = None


class IntradayPriceFetcher:
    """
    Fetches intraday OHLCV data for IDX stocks.
    - Pulls from Yahoo Finance `yfinance` endpoints by default.
    - Provides hook for IDX website scraping fallback.
    - Persists data with idempotent upsert and quality scoring.
    """

    def __init__(
        self,
        db_session: Session,
        *,
        provider_priority: Optional[List[str]] = None,
        throttle_seconds: float = 0.5,
    ) -> None:
        self.db_session = db_session
        self.provider_priority = provider_priority or ["yfinance", "idx_scraper"]
        self.throttle_seconds = throttle_seconds

    def fetch_intraday_prices(
        self,
        *,
        stock_codes: Optional[List[str]] = None,
        interval: str = "5m",
        lookback_minutes: int = 390,
        end_time: Optional[datetime] = None,
    ) -> Tuple[List[IntradayFetchResult], str]:
        """
        Fetch intraday bars for the requested symbols and persist to the database.

        Args:
            stock_codes: Restrict to specific IDX codes. Defaults to all active stocks.
            interval: Interval supported by Yahoo Finance (1m,2m,5m,15m,30m,60m).
            lookback_minutes: How far back to request data. Defaults to a full IDX session.
            end_time: Anchor timestamp; defaults to current UTC.
        """
        if interval not in SUPPORTED_INTERVALS:
            raise ValueError(f"Interval '{interval}' not supported. Options: {SUPPORTED_INTERVALS}")

        symbols = self._resolve_symbols(stock_codes)
        if not symbols:
            raise ValueError("No active stocks available for intraday fetching.")

        end_time = end_time or datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)

        job_id, job_log = self._start_job(interval, start_time, end_time, symbols)

        results: List[IntradayFetchResult] = []
        total_records = 0
        total_failed = 0

        try:
            for stock in symbols:
                fetch_result = self._fetch_single_stock(
                    stock_code=stock.stock_code,
                    yahoo_symbol=stock.yahoo_symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time,
                )
                results.append(fetch_result)

                if fetch_result.success:
                    total_records += fetch_result.records_fetched
                else:
                    total_failed += 1

                time.sleep(self.throttle_seconds)

            job_log.completed_at = datetime.utcnow()
            job_log.duration_seconds = (job_log.completed_at - job_log.started_at).total_seconds()
            job_log.status = "completed" if total_failed == 0 else "partial"
            job_log.records_processed = total_records
            job_log.records_inserted = total_records  # idempotent upsert, inserts dominate
            job_log.records_failed = total_failed

            scores = [r.data_quality_score for r in results if r.data_quality_score is not None]
            if scores:
                job_log.data_quality_score = sum(scores) / len(scores)

            self.db_session.commit()
            return results, job_id

        except Exception as exc:
            logger.exception("Intraday job %s failed: %s", job_id, exc)
            job_log.status = "failed"
            job_log.completed_at = datetime.utcnow()
            job_log.error_message = str(exc)
            self.db_session.commit()
            raise

    # --------------------------------------------------------------------- #
    # Private helpers
    # --------------------------------------------------------------------- #

    def _resolve_symbols(self, stock_codes: Optional[List[str]]) -> List[StockMaster]:
        query = self.db_session.query(StockMaster).filter(StockMaster.is_active.is_(True))
        if stock_codes:
            query = query.filter(StockMaster.stock_code.in_(stock_codes))
        return query.all()

    def _start_job(
        self,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        symbols: Iterable[StockMaster],
    ) -> Tuple[str, DataRefreshLog]:
        job = DataRefreshLog(
            job_name=f"intraday_price_fetch_{interval}",
            job_type="intraday_prices",
            started_at=datetime.utcnow(),
            status="running",
            target_date=end_time.date(),
            stock_codes=[s.stock_code for s in symbols],
            meta_data={
                "interval": interval,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )
        self.db_session.add(job)
        self.db_session.commit()
        return str(job.id), job

    def _fetch_single_stock(
        self,
        *,
        stock_code: str,
        yahoo_symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> IntradayFetchResult:
        for provider in self.provider_priority:
            try:
                df = self._dispatch_provider(
                    provider=provider,
                    yahoo_symbol=yahoo_symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time,
                )
                if df is None or df.empty:
                    raise ValueError("No data returned from provider.")

                normalized = self._normalize_dataframe(df, stock_code, interval)
                score = self._calculate_quality_score(normalized)
                normalized["quality_score"] = score
                inserted = self._persist_intraday_bars(normalized)

                return IntradayFetchResult(
                    stock_code=stock_code,
                    interval=interval,
                    success=True,
                    records_fetched=inserted,
                    data_quality_score=score,
                )
            except Exception as exc:
                logger.warning(
                    "Provider '%s' failed for %s (%s): %s",
                    provider,
                    stock_code,
                    interval,
                    exc,
                )
                last_error = exc
                continue

        return IntradayFetchResult(
            stock_code=stock_code,
            interval=interval,
            success=False,
            records_fetched=0,
            error_message=str(last_error),  # type: ignore
        )

    def _dispatch_provider(
        self,
        *,
        provider: str,
        yahoo_symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[pd.DataFrame]:
        if provider == "yfinance":
            return self._fetch_from_yfinance(yahoo_symbol, interval, start_time, end_time)
        if provider == "idx_scraper":
            return self._fetch_from_idx_scraper(yahoo_symbol, interval, start_time, end_time)
        raise ValueError(f"Unknown provider '{provider}'")

    def _fetch_from_yfinance(
        self,
        yahoo_symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[pd.DataFrame]:
        ticker = yf.Ticker(yahoo_symbol)
        df = ticker.history(
            start=start_time,
            end=end_time + timedelta(minutes=1),
            interval=interval,
            auto_adjust=False,
        )
        if df is not None and not df.empty:
            return df
        alt_df = yf.download(
            yahoo_symbol,
            start=start_time,
            end=end_time + timedelta(minutes=1),
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False
        )
        return alt_df if alt_df is not None and not alt_df.empty else None

    def _fetch_from_idx_scraper(
        self,
        yahoo_symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[pd.DataFrame]:
        """
        Placeholder for IDX website scraper fallback.
        Implemented as stub that currently returns None.
        """
        _ = (yahoo_symbol, interval, start_time, end_time)
        return None

    def _normalize_dataframe(
        self,
        df: pd.DataFrame,
        stock_code: str,
        interval: str,
    ) -> pd.DataFrame:
        df = df.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("Intraday dataframe index must be DatetimeIndex.")
        df.index = df.index.tz_localize(None)
        df.rename(
            columns={
                "Open": "open_price",
                "High": "high_price",
                "Low": "low_price",
                "Close": "close_price",
                "Adj Close": "adjusted_close",
                "Volume": "volume",
            },
            inplace=True,
        )

        df["stock_code"] = stock_code
        df["interval"] = interval
        df["timestamp"] = df.index
        df["session_date"] = df["timestamp"].dt.date
        df["vwap"] = (
            (df["close_price"] * df["volume"]).rolling(window=5, min_periods=1).sum()
            / df["volume"].rolling(window=5, min_periods=1).sum().replace({0: pd.NA})
        )
        df["trade_count"] = None
        df["turnover_value"] = df["close_price"] * df["volume"]
        df["data_source"] = "yfinance"
        df["quality_score"] = None
        return df[
            [
                "stock_code",
                "timestamp",
                "interval",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
                "vwap",
                "trade_count",
                "turnover_value",
                "session_date",
                "data_source",
                "quality_score",
            ]
        ]

    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        if df.empty:
            return 0.0
        completeness = 1.0 - df.isna().mean().mean()
        stability = 1.0 - (df["close_price"].pct_change().abs() > 0.15).mean()
        return max(0.0, min(1.0, 0.7 * completeness + 0.3 * stability))

    def _persist_intraday_bars(self, df: pd.DataFrame) -> int:
        records = df.to_dict(orient="records")
        if not records:
            return 0

        stmt = pg_insert(IntradayStockPrice).values(records)
        update_cols = {
            "open_price": stmt.excluded.open_price,
            "high_price": stmt.excluded.high_price,
            "low_price": stmt.excluded.low_price,
            "close_price": stmt.excluded.close_price,
            "volume": stmt.excluded.volume,
            "vwap": stmt.excluded.vwap,
            "turnover_value": stmt.excluded.turnover_value,
            "updated_at": datetime.utcnow(),
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["stock_code", "timestamp", "interval"],
            set_=update_cols,
        )
        self.db_session.execute(stmt)
        self.db_session.flush()
        return len(records)


__all__ = ["IntradayPriceFetcher", "IntradayFetchResult", "SUPPORTED_INTERVALS"]
