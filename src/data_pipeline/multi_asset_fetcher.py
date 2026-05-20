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
    Fetches BTC/USDT 1-minute klines from Binance public REST API.
    No API key required. Paginates automatically for long lookbacks.
    """

    SYMBOL = "BTCUSDT"
    INTERVAL = "1m"

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def fetch(self, lookback_minutes: int = 1440) -> Tuple[List[FetchResult], str]:
        """
        Fetch last `lookback_minutes` of 1m BTC candles.
        Paginates in 1000-bar chunks if needed.
        """
        job = self._start_job()
        try:
            end_ms = int(datetime.utcnow().timestamp() * 1000)
            start_ms = end_ms - lookback_minutes * 60 * 1000

            all_klines: list = []
            current_start = start_ms

            while current_start < end_ms:
                resp = requests.get(
                    BINANCE_KLINES_URL,
                    params={
                        "symbol": self.SYMBOL,
                        "interval": self.INTERVAL,
                        "startTime": current_start,
                        "endTime": end_ms,
                        "limit": BINANCE_MAX_LIMIT,
                    },
                    timeout=30,
                )
                if not resp.ok:
                    raise RuntimeError(f"Binance API error: HTTP {resp.status_code}")

                batch = resp.json()
                if not batch:
                    break

                all_klines.extend(batch)

                if len(batch) < BINANCE_MAX_LIMIT:
                    break  # got all remaining bars

                # Advance past last candle's open time by one interval
                current_start = batch[-1][0] + 60 * 1000

            records = [
                dict(
                    symbol=self.SYMBOL,
                    timestamp=datetime.utcfromtimestamp(k[0] / 1000),
                    interval=self.INTERVAL,
                    open_price=float(k[1]),
                    high_price=float(k[2]),
                    low_price=float(k[3]),
                    close_price=float(k[4]),
                    volume=float(k[5]),
                    quote_volume=float(k[7]),
                    fetched_at=datetime.utcnow(),
                )
                for k in all_klines
            ]
            self._upsert(records)
            self._complete_job(job, len(records))
            return [FetchResult(symbol=self.SYMBOL, success=True, records_fetched=len(records))], str(job.id)

        except Exception as exc:
            logger.warning("BinanceFetcher failed: %s", exc)
            self._fail_job(job, str(exc))
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
