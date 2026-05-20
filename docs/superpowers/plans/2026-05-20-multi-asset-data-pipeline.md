# Multi-Asset Data Pipeline (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add gold, USD/IDR forex, and BTC 1-minute price data to the existing pipeline — minimal footprint, maximum signal quality — wired into the daily systemd job.

**Architecture:** Three new SQLAlchemy models (`GoldPrice`, `ForexRate`, `CryptoPrice`) in `database_extensions.py`, one new fetcher file (`multi_asset_fetcher.py`) following the exact pattern of `DailyPriceFetcher`, and a one-line hook in `UnifiedDataPipeline.run_end_of_day()`. A retention cleanup runs at pipeline start to keep 1m BTC rows ≤ 60 days. No websocket stream for now — REST polling on the daily timer is enough for the feature engineering that follows.

**Tech Stack:** yfinance (gold `GC=F`, forex `USDIDR=X`), Binance public REST API (BTC/USDT 1m klines, no API key), SQLAlchemy 2.0, Alembic, existing `DailyPriceFetcher`/`DataRefreshLog` patterns.

**Scope (minimal first):**
- Gold: `GC=F` daily bars only (yfinance)
- Forex: `USDIDR=X` daily bars only (yfinance)
- Crypto: `BTCUSDT` 1m bars only (Binance public REST)
- Retention: 1m rows older than 60 days deleted at pipeline start

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `src/api/database_extensions.py` | Add `GoldPrice`, `ForexRate`, `CryptoPrice` ORM models |
| Create | `src/data_pipeline/multi_asset_fetcher.py` | `GoldFetcher`, `ForexFetcher`, `BinanceFetcher`, `MultiAssetRetentionCleaner` |
| Modify | `src/data_pipeline/unified_pipeline.py` | Call multi-asset stage in `run_end_of_day()` |
| Create | `migrations/versions/YYYYMMDD_multi_asset_tables.py` | Alembic migration for 3 new tables |
| Create | `scripts/backfill_multi_asset.py` | One-shot historical backfill (2yr gold/forex, 60d BTC 1m) |
| Create | `tests/data_pipeline/test_multi_asset_fetcher.py` | Unit tests for all fetchers + cleaner |

---

## Task 1: Add ORM Models

**Files:**
- Modify: `src/api/database_extensions.py` (append after existing model classes)

- [ ] **Step 1: Read the bottom of `database_extensions.py` to find the last model**

Run: `grep -n "^class " src/api/database_extensions.py`

- [ ] **Step 2: Append three new models**

Add to the end of `src/api/database_extensions.py`:

```python
class GoldPrice(Base):
    """Daily gold futures OHLCV (GC=F via yfinance)."""
    __tablename__ = "gold_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)  # UTC midnight for daily
    interval = Column(String(5), nullable=False, default="1d")
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float, nullable=False)
    volume = Column(Float)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("timestamp", "interval", name="uq_gold_ts_interval"),
        Index("idx_gold_ts_desc", "timestamp"),
    )


class ForexRate(Base):
    """Daily forex OHLCV — one row per (symbol, timestamp, interval)."""
    __tablename__ = "forex_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)  # e.g. USDIDR=X
    timestamp = Column(DateTime, nullable=False, index=True)
    interval = Column(String(5), nullable=False, default="1d")
    rate = Column(Float, nullable=False)        # close
    open_rate = Column(Float)
    high_rate = Column(Float)
    low_rate = Column(Float)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", "interval", name="uq_forex_symbol_ts_interval"),
        Index("idx_forex_symbol_ts", "symbol", "timestamp"),
    )


class CryptoPrice(Base):
    """
    OHLCV for crypto assets. Interval '1m' rows are purged after 60 days.
    Uses Binance kline timestamps (open time, UTC).
    """
    __tablename__ = "crypto_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)  # e.g. BTCUSDT
    timestamp = Column(DateTime, nullable=False, index=True)  # candle open time UTC
    interval = Column(String(5), nullable=False)             # 1m, 1d
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float, nullable=False)
    volume = Column(Float)        # base asset (BTC)
    quote_volume = Column(Float)  # USDT volume — useful for liquidity signal
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", "interval", name="uq_crypto_symbol_ts_interval"),
        Index("idx_crypto_symbol_ts", "symbol", "timestamp"),
        Index("idx_crypto_retention", "interval", "timestamp"),  # fast deletes
    )
```

- [ ] **Step 3: Verify models import cleanly**

```bash
cd /home/vlain/workspaces/personal/project-aurum
uv run python -c "from src.api.database_extensions import GoldPrice, ForexRate, CryptoPrice; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/api/database_extensions.py
git commit -m "feat: add GoldPrice, ForexRate, CryptoPrice ORM models [nyx-auto]"
```

---

## Task 2: Alembic Migration

**Files:**
- Create: `migrations/versions/YYYYMMDD_multi_asset_tables.py` (use `alembic revision --autogenerate`)

- [ ] **Step 1: Generate the migration**

```bash
cd /home/vlain/workspaces/personal/project-aurum
uv run alembic revision --autogenerate -m "multi_asset_tables"
```

Expected: creates a file like `migrations/versions/20260520_XXXXXXXX_multi_asset_tables.py`

- [ ] **Step 2: Inspect the generated file — check it contains `create_table` for all three new tables**

Open the file and confirm `gold_prices`, `forex_rates`, `crypto_prices` tables are present. No unexpected drops.

- [ ] **Step 3: Add the missing import (same fix as previous migration)**

At the top of the generated migration file, after the existing `import` block, add:

```python
import src.api.database  # noqa: F401 — registers custom GUID/JSONB types
```

- [ ] **Step 4: Apply the migration**

```bash
uv run alembic upgrade head
```

Expected: no errors.

- [ ] **Step 5: Verify tables exist in DB**

```bash
uv run python -c "
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv; load_dotenv('.env')
from src.api.config import settings
e = create_engine(f'postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}')
print(inspect(e).get_table_names())
"
```

Expected: `gold_prices`, `forex_rates`, `crypto_prices` in the list.

- [ ] **Step 6: Commit**

```bash
git add migrations/
git commit -m "feat: migration — gold_prices, forex_rates, crypto_prices tables [nyx-auto]"
```

---

## Task 3: Write Multi-Asset Fetcher (with tests first)

**Files:**
- Create: `tests/data_pipeline/test_multi_asset_fetcher.py`
- Create: `src/data_pipeline/multi_asset_fetcher.py`

### 3a — Write the failing tests

- [ ] **Step 1: Create test file**

Create `tests/data_pipeline/test_multi_asset_fetcher.py`:

```python
"""Tests for GoldFetcher, ForexFetcher, BinanceFetcher, MultiAssetRetentionCleaner."""
from __future__ import annotations

from datetime import datetime, timedelta, date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data_pipeline.multi_asset_fetcher import (
    BinanceFetcher,
    ForexFetcher,
    GoldFetcher,
    MultiAssetRetentionCleaner,
)
from src.api.database_extensions import GoldPrice, ForexRate, CryptoPrice


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def db_session():
    session = MagicMock()
    session.query.return_value.filter.return_value.delete.return_value = 5
    return session


def _make_ohlcv_df(rows: int = 3) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "Open": [1800.0] * rows,
            "High": [1820.0] * rows,
            "Low": [1790.0] * rows,
            "Close": [1810.0] * rows,
            "Volume": [100.0] * rows,
        },
        index=idx,
    )


# ------------------------------------------------------------------ #
# GoldFetcher
# ------------------------------------------------------------------ #

class TestGoldFetcher:
    def test_fetch_saves_records(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = _make_ohlcv_df(3)
            fetcher = GoldFetcher(db_session)
            results, job_id = fetcher.fetch(backfill_days=7)

        assert len(results) == 1
        assert results[0].success
        assert results[0].records_fetched == 3
        assert job_id

    def test_fetch_handles_empty_response(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            fetcher = GoldFetcher(db_session)
            results, _ = fetcher.fetch(backfill_days=7)

        assert results[0].success is False

    def test_fetch_handles_exception(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.side_effect = RuntimeError("network error")
            fetcher = GoldFetcher(db_session)
            results, _ = fetcher.fetch(backfill_days=7)

        assert results[0].success is False
        assert "network error" in results[0].error_message


# ------------------------------------------------------------------ #
# ForexFetcher
# ------------------------------------------------------------------ #

class TestForexFetcher:
    def test_fetch_saves_records(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = _make_ohlcv_df(5)
            fetcher = ForexFetcher(db_session, symbol="USDIDR=X")
            results, job_id = fetcher.fetch(backfill_days=7)

        assert results[0].success
        assert results[0].records_fetched == 5

    def test_fetch_uses_correct_symbol(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = _make_ohlcv_df(1)
            ForexFetcher(db_session, symbol="USDIDR=X").fetch(backfill_days=3)

        mock_ticker.assert_called_once_with("USDIDR=X")


# ------------------------------------------------------------------ #
# BinanceFetcher
# ------------------------------------------------------------------ #

def _binance_klines(n: int = 5) -> list:
    """Minimal Binance kline format: [open_time, o, h, l, c, vol, close_time, quote_vol, ...]"""
    base = int(datetime(2026, 1, 1).timestamp() * 1000)
    return [
        [base + i * 60000, "50000", "50100", "49900", "50050", "1.5",
         base + i * 60000 + 59999, "75075.0", 100, "0.8", "40000", "0"]
        for i in range(n)
    ]


class TestBinanceFetcher:
    def test_fetch_saves_records(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.requests.get") as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.json.return_value = _binance_klines(10)
            fetcher = BinanceFetcher(db_session)
            results, job_id = fetcher.fetch(lookback_minutes=60)

        assert results[0].success
        assert results[0].records_fetched == 10

    def test_fetch_handles_api_error(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.requests.get") as mock_get:
            mock_get.return_value.ok = False
            mock_get.return_value.status_code = 429
            fetcher = BinanceFetcher(db_session)
            results, _ = fetcher.fetch(lookback_minutes=60)

        assert results[0].success is False

    def test_fetch_paginates_when_needed(self, db_session):
        """lookback > 1000 bars triggers multiple API calls."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock = MagicMock()
            mock.ok = True
            mock.json.return_value = _binance_klines(1000) if call_count == 1 else _binance_klines(200)
            return mock

        with patch("src.data_pipeline.multi_asset_fetcher.requests.get", side_effect=side_effect):
            fetcher = BinanceFetcher(db_session)
            results, _ = fetcher.fetch(lookback_minutes=1500)  # > 1000 bars

        assert call_count == 2
        assert results[0].records_fetched == 1200


# ------------------------------------------------------------------ #
# Retention Cleaner
# ------------------------------------------------------------------ #

class TestMultiAssetRetentionCleaner:
    def test_deletes_old_1m_rows(self, db_session):
        cleaner = MultiAssetRetentionCleaner(db_session)
        deleted = cleaner.purge_old_1m_data(retain_days=60)

        assert isinstance(deleted, int)
        db_session.commit.assert_called()
```

- [ ] **Step 2: Run tests to confirm they all fail (module not found)**

```bash
uv run pytest tests/data_pipeline/test_multi_asset_fetcher.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'src.data_pipeline.multi_asset_fetcher'`

### 3b — Implement the fetchers

- [ ] **Step 3: Ensure `tests/data_pipeline/__init__.py` exists**

```bash
touch tests/data_pipeline/__init__.py
```

- [ ] **Step 4: Create `src/data_pipeline/multi_asset_fetcher.py`**

```python
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
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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

                # Next page starts after the last candle's close time
                last_open_ms = batch[-1][0]
                if len(batch) < BINANCE_MAX_LIMIT:
                    break  # got all remaining bars
                current_start = last_open_ms + 60 * 1000  # advance by 1 interval

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
        logger.info("Retention cleaner: deleted %s old 1m crypto rows (cutoff=%s)", deleted, cutoff.date())
        return deleted


__all__ = [
    "GoldFetcher",
    "ForexFetcher",
    "BinanceFetcher",
    "MultiAssetRetentionCleaner",
    "FetchResult",
]
```

- [ ] **Step 5: Run the tests**

```bash
uv run pytest tests/data_pipeline/test_multi_asset_fetcher.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/data_pipeline/multi_asset_fetcher.py tests/data_pipeline/test_multi_asset_fetcher.py tests/data_pipeline/__init__.py
git commit -m "feat: add GoldFetcher, ForexFetcher, BinanceFetcher, RetentionCleaner [nyx-auto]"
```

---

## Task 4: Wire Into UnifiedDataPipeline

**Files:**
- Modify: `src/data_pipeline/unified_pipeline.py`

- [ ] **Step 1: Add import at top of `unified_pipeline.py`**

After the existing imports, add:

```python
from .multi_asset_fetcher import GoldFetcher, ForexFetcher, BinanceFetcher, MultiAssetRetentionCleaner
```

- [ ] **Step 2: Add retention + multi-asset stage to `run_end_of_day()`**

In `run_end_of_day()`, add two lines — retention cleanup first, then the new stage:

```python
def run_end_of_day(self, config: PipelineRunConfig = PipelineRunConfig()) -> None:
    with self.session_scope() as session:
        self._run_retention_cleanup(session)          # <-- add this
        self._run_daily_prices(session, config.stock_codes)
        self._run_intraday(session, config.stock_codes, config.intraday_intervals)
        self._run_news(session, config.stock_codes, config.news_max_articles)
        self._maybe_run_fundamentals(session, config.stock_codes, config.fundamentals_frequency)
        self._run_multi_asset(session)                # <-- add this
        if config.export_feature_store:
            self._export_feature_store(session, config.stock_codes)
```

- [ ] **Step 3: Add the two new private methods to `UnifiedDataPipeline`**

Add before `_export_feature_store`:

```python
def _run_retention_cleanup(self, session: Session) -> None:
    cleaner = MultiAssetRetentionCleaner(session)
    deleted = cleaner.purge_old_1m_data(retain_days=60)
    logger.info("Retention cleanup: removed %s stale 1m crypto rows", deleted)

def _run_multi_asset(self, session: Session) -> None:
    gold_results, gold_job = GoldFetcher(session).fetch(backfill_days=3)
    logger.info("Gold fetch job=%s success=%s records=%s",
                gold_job, gold_results[0].success, gold_results[0].records_fetched)

    forex_results, forex_job = ForexFetcher(session, symbol="USDIDR=X").fetch(backfill_days=3)
    logger.info("Forex fetch job=%s success=%s records=%s",
                forex_job, forex_results[0].success, forex_results[0].records_fetched)

    btc_results, btc_job = BinanceFetcher(session).fetch(lookback_minutes=1440)
    logger.info("BTC 1m fetch job=%s success=%s records=%s",
                btc_job, btc_results[0].success, btc_results[0].records_fetched)
```

- [ ] **Step 4: Verify import works**

```bash
uv run python -c "from src.data_pipeline.unified_pipeline import UnifiedDataPipeline; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Run the full test suite to check no regressions**

```bash
uv run pytest tests/ -v --tb=short -q 2>&1 | tail -20
```

Expected: all existing tests still pass, new fetcher tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/data_pipeline/unified_pipeline.py
git commit -m "feat: wire multi-asset pipeline into UnifiedDataPipeline [nyx-auto]"
```

---

## Task 5: Historical Backfill Script

**Files:**
- Create: `scripts/backfill_multi_asset.py`

- [ ] **Step 1: Create the backfill script**

```python
"""
One-shot historical backfill for multi-asset data.

  Gold (GC=F): 2 years daily
  Forex (USDIDR=X): 2 years daily
  BTC 1m: 60 days (retention limit — no point going further)

Run once after deploying the new tables:
    uv run python scripts/backfill_multi_asset.py
"""
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.config import settings
from src.data_pipeline.multi_asset_fetcher import GoldFetcher, ForexFetcher, BinanceFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    db_url = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    two_years_ago = datetime.utcnow() - timedelta(days=730)
    sixty_days_ago = datetime.utcnow() - timedelta(days=60)

    errors = 0

    # Gold — 2 years daily
    logger.info("Backfilling gold (2yr daily)...")
    with Session() as session:
        results, job_id = GoldFetcher(session).fetch(start_date=two_years_ago)
        session.commit()
    r = results[0]
    if r.success:
        logger.info("Gold OK: %s records (job=%s)", r.records_fetched, job_id)
    else:
        logger.error("Gold FAILED: %s", r.error_message)
        errors += 1

    # Forex USD/IDR — 2 years daily
    logger.info("Backfilling USDIDR=X (2yr daily)...")
    with Session() as session:
        results, job_id = ForexFetcher(session, symbol="USDIDR=X").fetch(start_date=two_years_ago)
        session.commit()
    r = results[0]
    if r.success:
        logger.info("Forex OK: %s records (job=%s)", r.records_fetched, job_id)
    else:
        logger.error("Forex FAILED: %s", r.error_message)
        errors += 1

    # BTC 1m — 60 days (Binance)
    # 60 days × 24h × 60min = 86,400 bars → ~87 paginated requests
    logger.info("Backfilling BTC 1m (60 days, ~87 API calls)...")
    with Session() as session:
        results, job_id = BinanceFetcher(session).fetch(lookback_minutes=60 * 24 * 60)
        session.commit()
    r = results[0]
    if r.success:
        logger.info("BTC 1m OK: %s records (job=%s)", r.records_fetched, job_id)
    else:
        logger.error("BTC 1m FAILED: %s", r.error_message)
        errors += 1

    return errors


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the backfill**

```bash
cd /home/vlain/workspaces/personal/project-aurum
uv run python scripts/backfill_multi_asset.py
```

Expected output (approximate):
```
Gold OK: ~520 records
Forex OK: ~520 records
BTC 1m OK: ~86400 records
```

BTC backfill takes ~5–10 minutes due to pagination throttling. If it fails partway, re-run — the `ON CONFLICT DO NOTHING` upsert makes it safe to re-run.

- [ ] **Step 3: Verify row counts in DB**

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv('.env')
from sqlalchemy import create_engine, text
from src.api.config import settings
e = create_engine(f'postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}')
with e.connect() as c:
    for t in ['gold_prices', 'forex_rates', 'crypto_prices']:
        n = c.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
        print(f'{t}: {n} rows')
"
```

Expected:
```
gold_prices: ~520 rows
forex_rates: ~520 rows
crypto_prices: ~86000 rows
```

- [ ] **Step 4: Commit**

```bash
git add scripts/backfill_multi_asset.py
git commit -m "feat: add multi-asset historical backfill script [nyx-auto]"
```

---

## Task 6: Smoke Test Against Live Pipeline

- [ ] **Step 1: Run a single pipeline cycle manually**

```bash
uv run python scripts/run_pipeline.py
```

Watch for these log lines:
```
Retention cleanup: removed N stale 1m crypto rows
Gold fetch job=... success=True records=1
Forex fetch job=... success=True records=1
BTC 1m fetch job=... success=True records=1440
```

- [ ] **Step 2: If any fetch returns `success=False`, check the error**

Common issues:
- `yfinance returned empty dataframe` → Yahoo Finance rate-limit. Wait 60s and retry.
- `Binance API error: HTTP 429` → rate limit. Binance public REST allows 1200 requests/min — if hitting it, add `time.sleep(0.05)` between paginated calls in `BinanceFetcher.fetch()`.

- [ ] **Step 3: Confirm systemd timer will pick this up automatically**

```bash
systemctl status nyx-aurum-data.timer
```

The existing timer already triggers `run_pipeline.py` daily at 09:30 WIB. No changes needed.

- [ ] **Step 4: Final commit if any rate-limit fixes were made**

```bash
git add -A
git commit -m "fix: multi-asset rate limit handling if needed [nyx-auto]"
```

---

## Done — What's Been Built

After completing all tasks:

| Asset | Data | Rows/day | Retention |
|---|---|---|---|
| Gold (GC=F) | Daily OHLCV | 1 | Forever |
| USD/IDR | Daily OHLCV | 1 | Forever |
| BTC/USDT | 1m OHLCV | 1,440 | 60 days rolling |

Daily systemd job handles ongoing collection automatically. BTC 1m rows are auto-purged.

**Next step (Sub-Plan B):** Wait until ≥30 days of multi-asset data has accumulated, then run the feature engineering overhaul to fill in the cross-asset feature stubs.
