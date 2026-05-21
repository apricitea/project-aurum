"""
Multi-asset price fetchers: Gold (yfinance), Forex (yfinance), BTC 1m (Binance REST).

Design mirrors DailyPriceFetcher — each fetcher:
  - accepts a SQLAlchemy Session
  - returns (List[FetchResult], job_id)
  - writes a DataRefreshLog row
  - upserts via ON CONFLICT DO NOTHING (idempotent)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import requests
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..api.database_extensions import CryptoPrice, DataRefreshLog, ForexRate, GoldPrice

logger = logging.getLogger(__name__)

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_MAX_LIMIT = 1000  # max bars per Binance request


@dataclass
class FetchResult:
    symbol: str
    success: bool
    records_fetched: int
    error_message: Optional[str] = None


# ------------------------------------------------------------------ #
# Gold
# ------------------------------------------------------------------ #

class GoldFetcher:
    """Fetches daily gold futures (GC=F) via yfinance."""

    SYMBOL = "GC=F"
    INTERVAL = "1d"

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def fetch(
        self,
        backfill_days: int = 7,
        start_date: Optional[datetime] = None,
    ) -> Tuple[List[FetchResult], str]:
        job = self._start_job()
        try:
            start = start_date or (datetime.utcnow() - timedelta(days=backfill_days))
            df = yf.Ticker(self.SYMBOL).history(start=start.strftime("%Y-%m-%d"))

            if df.empty:
                raise ValueError("yfinance returned empty dataframe for GC=F")

            records = [
                dict(
                    timestamp=ts.to_pydatetime().replace(tzinfo=None),
                    interval=self.INTERVAL,
                    open_price=float(row["Open"]) if row.get("Open") is not None else None,
                    high_price=float(row["High"]) if row.get("High") is not None else None,
                    low_price=float(row["Low"]) if row.get("Low") is not None else None,
                    close_price=float(row["Close"]),
                    volume=float(row["Volume"]) if row.get("Volume") is not None else None,
                    fetched_at=datetime.utcnow(),
                )
                for ts, row in df.iterrows()
            ]
            self._upsert(records)
            self._complete_job(job, len(records))
            return [FetchResult(symbol=self.SYMBOL, success=True, records_fetched=len(records))], str(job.id)

        except Exception as exc:
            logger.warning("GoldFetcher failed: %s", exc)
            self._fail_job(job, str(exc))
            return [FetchResult(symbol=self.SYMBOL, success=False, records_fetched=0, error_message=str(exc))], str(job.id)

    def _upsert(self, records: list) -> None:
        if not records:
            return
        stmt = pg_insert(GoldPrice).values(records)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_gold_ts_interval")
        self.db_session.execute(stmt)
        self.db_session.flush()

    def _start_job(self) -> DataRefreshLog:
        job = DataRefreshLog(
            job_name="gold_prices",
            job_type="multi_asset",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.db_session.add(job)
        self.db_session.flush()
        return job

    def _complete_job(self, job: DataRefreshLog, count: int) -> None:
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.records_inserted = count
        job.records_processed = count
        job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
        self.db_session.flush()

    def _fail_job(self, job: DataRefreshLog, error: str) -> None:
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        job.error_message = error
        self.db_session.flush()


# ------------------------------------------------------------------ #
# Forex
# ------------------------------------------------------------------ #

class ForexFetcher:
    """Fetches daily forex rates via yfinance (e.g. USDIDR=X)."""

    INTERVAL = "1d"

    def __init__(self, db_session: Session, symbol: str = "USDIDR=X") -> None:
        self.db_session = db_session
        self.symbol = symbol

    def fetch(
        self,
        backfill_days: int = 7,
        start_date: Optional[datetime] = None,
    ) -> Tuple[List[FetchResult], str]:
        job = self._start_job()
        try:
            start = start_date or (datetime.utcnow() - timedelta(days=backfill_days))
            df = yf.Ticker(self.symbol).history(start=start.strftime("%Y-%m-%d"))

            if df.empty:
                raise ValueError(f"yfinance returned empty dataframe for {self.symbol}")

            records = [
                dict(
                    symbol=self.symbol,
                    timestamp=ts.to_pydatetime().replace(tzinfo=None),
                    interval=self.INTERVAL,
                    rate=float(row["Close"]),
                    open_rate=float(row["Open"]) if row.get("Open") is not None else None,
                    high_rate=float(row["High"]) if row.get("High") is not None else None,
                    low_rate=float(row["Low"]) if row.get("Low") is not None else None,
                    fetched_at=datetime.utcnow(),
                )
                for ts, row in df.iterrows()
            ]
            self._upsert(records)
            self._complete_job(job, len(records))
            return [FetchResult(symbol=self.symbol, success=True, records_fetched=len(records))], str(job.id)

        except Exception as exc:
            logger.warning("ForexFetcher(%s) failed: %s", self.symbol, exc)
            self._fail_job(job, str(exc))
            return [FetchResult(symbol=self.symbol, success=False, records_fetched=0, error_message=str(exc))], str(job.id)

    def _upsert(self, records: list) -> None:
        if not records:
            return
        stmt = pg_insert(ForexRate).values(records)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_forex_symbol_ts_interval")
        self.db_session.execute(stmt)
        self.db_session.flush()

    def _start_job(self) -> DataRefreshLog:
        job = DataRefreshLog(
            job_name=f"forex_{self.symbol}",
            job_type="multi_asset",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.db_session.add(job)
        self.db_session.flush()
        return job

    def _complete_job(self, job: DataRefreshLog, count: int) -> None:
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.records_inserted = count
        job.records_processed = count
        job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
        self.db_session.flush()

    def _fail_job(self, job: DataRefreshLog, error: str) -> None:
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        job.error_message = error
        self.db_session.flush()


# ------------------------------------------------------------------ #
# Binance (BTC 1m)
# ------------------------------------------------------------------ #

class BinanceFetcher:
    """
    Fetches BTC 1-minute candles via yfinance (BTC-USD).

    Uses yfinance as the primary source — Binance REST is blocked on this homelab.
    yfinance supports max 7-day lookback for 1m interval; the daily pipeline timer
    ensures continuous accumulation up to the 60-day retention window.

    To swap in Binance REST when network access is available:
      Replace the yfinance call with the Binance klines endpoint:
      GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m
    """

    SYMBOL = "BTC-USD"
    YF_SYMBOL = "BTC-USD"
    INTERVAL = "1m"
    MAX_LOOKBACK_DAYS = 7  # yfinance 1m hard limit

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def fetch(self, lookback_minutes: int = 1440) -> Tuple[List[FetchResult], str]:
        """
        Fetch last `lookback_minutes` of 1m BTC candles.
        Capped at MAX_LOOKBACK_DAYS * 1440 due to yfinance limits.
        """
        job = self._start_job()
        try:
            max_minutes = self.MAX_LOOKBACK_DAYS * 24 * 60
            actual_minutes = min(lookback_minutes, max_minutes)
            # yfinance 1m: period must be ≤ 7d
            period_days = max(1, min(7, (actual_minutes + 1439) // 1440))

            df = yf.Ticker(self.YF_SYMBOL).history(period=f"{period_days}d", interval="1m")

            if df.empty:
                raise ValueError(f"yfinance returned empty dataframe for {self.YF_SYMBOL} 1m")

            records = [
                dict(
                    symbol=self.SYMBOL,
                    timestamp=ts.to_pydatetime().replace(tzinfo=None),
                    interval=self.INTERVAL,
                    open_price=float(row["Open"]),
                    high_price=float(row["High"]),
                    low_price=float(row["Low"]),
                    close_price=float(row["Close"]),
                    volume=float(row["Volume"]),
                    quote_volume=None,  # not available from yfinance
                    fetched_at=datetime.utcnow(),
                )
                for ts, row in df.iterrows()
            ]
            self._upsert(records)
            self._complete_job(job, len(records))
            return [FetchResult(symbol=self.SYMBOL, success=True, records_fetched=len(records))], str(job.id)

        except Exception as exc:
            logger.warning("BinanceFetcher failed: %s", exc)
            self._fail_job(job, str(exc))
            return [FetchResult(symbol=self.SYMBOL, success=False, records_fetched=0, error_message=str(exc))], str(job.id)

    def fetch_daily(self, backfill_days: int = 3) -> Tuple[List[FetchResult], str]:
        """
        Fetch recent daily BTC-USD candles via yfinance.
        Runs alongside fetch() in the daily pipeline to keep interval='1d' rows current.
        Daily rows are retained forever (retention cleaner only purges interval='1m').
        """
        job = DataRefreshLog(
            job_name="crypto_btc_1d",
            job_type="multi_asset",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.db_session.add(job)
        self.db_session.flush()

        try:
            df = yf.Ticker(self.YF_SYMBOL).history(period=f"{max(backfill_days, 5)}d", interval="1d")
            if df.empty:
                raise ValueError(f"yfinance returned empty dataframe for {self.YF_SYMBOL} 1d")

            records = [
                dict(
                    symbol=self.SYMBOL,
                    timestamp=ts.to_pydatetime().replace(tzinfo=None),
                    interval="1d",
                    open_price=float(row["Open"]),
                    high_price=float(row["High"]),
                    low_price=float(row["Low"]),
                    close_price=float(row["Close"]),
                    volume=float(row["Volume"]),
                    quote_volume=None,
                    fetched_at=datetime.utcnow(),
                )
                for ts, row in df.iterrows()
            ]
            self._upsert(records)
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.records_inserted = len(records)
            job.records_processed = len(records)
            job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            self.db_session.flush()
            return [FetchResult(symbol=self.SYMBOL, success=True, records_fetched=len(records))], str(job.id)

        except Exception as exc:
            logger.warning("BinanceFetcher.fetch_daily failed: %s", exc)
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(exc)
            self.db_session.flush()
            return [FetchResult(symbol=self.SYMBOL, success=False, records_fetched=0, error_message=str(exc))], str(job.id)

    def _upsert(self, records: list) -> None:
        if not records:
            return
        # Batch insert in 5000-row chunks to avoid parameter limits
        for i in range(0, len(records), 5000):
            chunk = records[i : i + 5000]
            stmt = pg_insert(CryptoPrice).values(chunk)
            stmt = stmt.on_conflict_do_nothing(constraint="uq_crypto_symbol_ts_interval")
            self.db_session.execute(stmt)
        self.db_session.flush()

    def _start_job(self) -> DataRefreshLog:
        job = DataRefreshLog(
            job_name="crypto_btc_1m",
            job_type="multi_asset",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.db_session.add(job)
        self.db_session.flush()
        return job

    def _complete_job(self, job: DataRefreshLog, count: int) -> None:
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.records_inserted = count
        job.records_processed = count
        job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
        self.db_session.flush()

    def _fail_job(self, job: DataRefreshLog, error: str) -> None:
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        job.error_message = error
        self.db_session.flush()


# ------------------------------------------------------------------ #
# Retention Cleaner
# ------------------------------------------------------------------ #

class MultiAssetRetentionCleaner:
    """
    Purges high-frequency rows beyond retention window.
    Run at the start of each pipeline execution.

    Policy:
      - crypto_prices interval='1m' older than 60 days → delete
    """

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def purge_old_1m_data(self, retain_days: int = 60) -> int:
        cutoff = datetime.utcnow() - timedelta(days=retain_days)
        deleted = (
            self.db_session.query(CryptoPrice)
            .filter(CryptoPrice.interval == "1m", CryptoPrice.timestamp < cutoff)
            .delete(synchronize_session=False)
        )
        self.db_session.commit()
        logger.info(
            "Retention cleaner: deleted %s old 1m crypto rows (cutoff=%s)",
            deleted,
            cutoff.date(),
        )
        return deleted


__all__ = [
    "GoldFetcher",
    "ForexFetcher",
    "BinanceFetcher",
    "MultiAssetRetentionCleaner",
    "FetchResult",
]
