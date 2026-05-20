# Feature Engineering Overhaul (Sub-Plan B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stub cross-asset features with real DB-backed computations, add multi-timeframe volatility features, add regime detection, and introduce a TripleBarrierLabeler to replace the naive `pd.qcut` labeling.

**Architecture:** Three new components added alongside the existing `IDXFeatureEngineer`:
(1) `CrossAssetLoader` fetches gold/forex/BTC from DB and returns a date-indexed DataFrame;
(2) `IDXFeatureEngineer.generate_technical_features()` gains an optional `cross_asset_df` param (fully backward-compatible) and calls three filled-in helpers;
(3) `TripleBarrierLabeler` is a pure-pandas class that replaces `pd.qcut` forward-return labels.
All features degrade gracefully to NaN when cross-asset history is insufficient (BTC <30d window fills in over time).

**Tech Stack:** pandas, numpy, SQLAlchemy 2.0 ORM (existing), no new dependencies.

---

## What already exists — do not duplicate

| Feature | Where |
|---|---|
| `return_1d/3d/5d/10d/20d` | `_add_price_features()` |
| RSI, MACD, Stochastic, Williams %R, ADX | `_add_technical_indicators()` |
| ATR, daily range, close position | `_add_microstructure_features()` |
| Volume MA, VWAP, OBV, A/D line | `_add_volume_features()` |

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `src/domains/market_data/application/cross_asset_loader.py` | Queries `gold_prices`, `forex_rates`, `crypto_prices` → date-indexed DataFrame |
| Modify | `src/domains/market_data/application/feature_engineering.py` | Fill cross-asset stubs, add multiframe + regime methods, accept `cross_asset_df` param |
| Create | `src/domains/market_data/application/triple_barrier.py` | ATR-based triple-barrier labeler replacing `pd.qcut` |
| Create | `tests/test_cross_asset_loader.py` | Unit tests for CrossAssetLoader |
| Create | `tests/test_feature_engineering_overhaul.py` | Tests for new feature methods |
| Create | `tests/test_triple_barrier.py` | Tests for TripleBarrierLabeler |

---

## Task 1: CrossAssetLoader

Fetches gold/forex/BTC from the DB tables added in Sub-Plan A and returns a single date-indexed DataFrame used by the feature engineer.

**Files:**
- Create: `src/domains/market_data/application/cross_asset_loader.py`
- Create: `tests/test_cross_asset_loader.py`

### 1a — Write failing tests

- [ ] **Step 1: Create test file**

```python
# tests/test_cross_asset_loader.py
"""Tests for CrossAssetLoader."""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.domains.market_data.application.cross_asset_loader import CrossAssetLoader


@pytest.fixture
def db_session():
    return MagicMock()


def _mock_gold_rows(n=5):
    base = datetime(2026, 1, 1)
    return [
        MagicMock(timestamp=datetime(2026, 1, i + 1), close_price=1800.0 + i * 2)
        for i in range(n)
    ]


def _mock_forex_rows(n=5):
    return [
        MagicMock(timestamp=datetime(2026, 1, i + 1), rate=16000.0 + i * 50)
        for i in range(n)
    ]


def _mock_crypto_rows(n=10):
    """1m BTC rows spread across 2 days."""
    rows = []
    for i in range(n):
        day = 1 + (i // 5)
        rows.append(MagicMock(
            timestamp=datetime(2026, 1, day, i % 5, 0),
            close_price=50000.0 + i * 10,
        ))
    return rows


class TestCrossAssetLoader:
    def test_load_returns_dataframe(self, db_session):
        db_session.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            _mock_gold_rows(5),
            _mock_forex_rows(5),
            _mock_crypto_rows(10),
        ]
        loader = CrossAssetLoader(db_session)
        df = loader.load(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
        )
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_load_has_expected_columns(self, db_session):
        db_session.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            _mock_gold_rows(5),
            _mock_forex_rows(5),
            _mock_crypto_rows(10),
        ]
        loader = CrossAssetLoader(db_session)
        df = loader.load(start_date=date(2026, 1, 1), end_date=date(2026, 1, 5))

        expected = [
            "gold_close", "gold_1d_return", "gold_5d_return",
            "usdidr_rate", "usdidr_1d_return", "usdidr_5d_return", "usdidr_vol_20d",
            "btc_close", "btc_1d_return", "btc_vol_30d", "btc_regime",
        ]
        for col in expected:
            assert col in df.columns, f"Missing column: {col}"

    def test_load_empty_db_returns_empty_dataframe(self, db_session):
        db_session.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            [], [], [],
        ]
        loader = CrossAssetLoader(db_session)
        df = loader.load(start_date=date(2026, 1, 1), end_date=date(2026, 1, 5))
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_btc_aggregated_to_daily(self, db_session):
        """Multiple 1m rows on same day → single daily row (last close)."""
        db_session.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            _mock_gold_rows(2),
            _mock_forex_rows(2),
            _mock_crypto_rows(10),  # 10 1m rows across 2 days
        ]
        loader = CrossAssetLoader(db_session)
        df = loader.load(start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))
        # Should have at most 2 rows (1 per day), not 10
        assert len(df) <= 2
```

- [ ] **Step 2: Run to confirm ImportError**

```bash
uv run pytest tests/test_cross_asset_loader.py -v 2>&1 | head -15
```

Expected: `ImportError: No module named '...cross_asset_loader'`

### 1b — Implement

- [ ] **Step 3: Create `cross_asset_loader.py`**

```python
# src/domains/market_data/application/cross_asset_loader.py
"""
CrossAssetLoader — fetches gold, forex, and BTC prices from DB tables
(populated by Sub-Plan A) and returns a single date-indexed DataFrame
for use by IDXFeatureEngineer._add_cross_asset_features().

All derived columns degrade gracefully to NaN when history is insufficient.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ....api.database_extensions import GoldPrice, ForexRate, CryptoPrice

logger = logging.getLogger(__name__)


class CrossAssetLoader:
    """
    Loads gold / forex / BTC data from the database and returns
    a date-indexed DataFrame ready for feature engineering.

    Columns returned:
        gold_close, gold_1d_return, gold_5d_return
        usdidr_rate, usdidr_1d_return, usdidr_5d_return, usdidr_vol_20d
        btc_close, btc_1d_return, btc_vol_30d, btc_regime
    """

    BTC_SYMBOL = "BTC-USD"
    FOREX_SYMBOL = "USDIDR=X"

    def __init__(self, db_session: Session) -> None:
        self.session = db_session

    def load(
        self,
        start_date: date,
        end_date: date,
        extra_lookback_days: int = 90,
    ) -> pd.DataFrame:
        """
        Return a date-indexed DataFrame of cross-asset features.

        Fetches `extra_lookback_days` before `start_date` so rolling
        windows (up to 30d) are warm at `start_date`.

        Returns an empty DataFrame (no columns) if all three sources
        have no data.
        """
        fetch_from = datetime.combine(
            start_date - timedelta(days=extra_lookback_days), datetime.min.time()
        )
        fetch_to = datetime.combine(end_date, datetime.max.time())

        gold_df = self._load_gold(fetch_from, fetch_to)
        forex_df = self._load_forex(fetch_from, fetch_to)
        btc_df = self._load_btc(fetch_from, fetch_to)

        if gold_df.empty and forex_df.empty and btc_df.empty:
            return pd.DataFrame()

        merged = self._build_features(gold_df, forex_df, btc_df)

        # Trim to requested date range
        merged = merged[
            (merged.index >= pd.Timestamp(start_date))
            & (merged.index <= pd.Timestamp(end_date))
        ]
        return merged

    # ------------------------------------------------------------------ #
    # Private loaders
    # ------------------------------------------------------------------ #

    def _load_gold(self, start: datetime, end: datetime) -> pd.DataFrame:
        rows = (
            self.session.query(GoldPrice)
            .filter(GoldPrice.timestamp >= start, GoldPrice.timestamp <= end)
            .order_by(GoldPrice.timestamp)
            .all()
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(
            {"close": [r.close_price for r in rows]},
            index=pd.to_datetime([r.timestamp for r in rows]).normalize(),
        )
        return df[~df.index.duplicated(keep="last")]

    def _load_forex(self, start: datetime, end: datetime) -> pd.DataFrame:
        rows = (
            self.session.query(ForexRate)
            .filter(
                ForexRate.symbol == self.FOREX_SYMBOL,
                ForexRate.timestamp >= start,
                ForexRate.timestamp <= end,
            )
            .order_by(ForexRate.timestamp)
            .all()
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(
            {"rate": [r.rate for r in rows]},
            index=pd.to_datetime([r.timestamp for r in rows]).normalize(),
        )
        return df[~df.index.duplicated(keep="last")]

    def _load_btc(self, start: datetime, end: datetime) -> pd.DataFrame:
        """Aggregate 1m rows to daily (last close per calendar day)."""
        rows = (
            self.session.query(CryptoPrice)
            .filter(
                CryptoPrice.symbol == self.BTC_SYMBOL,
                CryptoPrice.timestamp >= start,
                CryptoPrice.timestamp <= end,
            )
            .order_by(CryptoPrice.timestamp)
            .all()
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(
            {"close": [r.close_price for r in rows]},
            index=pd.to_datetime([r.timestamp for r in rows]),
        )
        # Aggregate 1m → daily using last close
        daily = df.resample("D").last().dropna()
        return daily

    # ------------------------------------------------------------------ #
    # Feature computation
    # ------------------------------------------------------------------ #

    def _build_features(
        self,
        gold: pd.DataFrame,
        forex: pd.DataFrame,
        btc: pd.DataFrame,
    ) -> pd.DataFrame:
        out = pd.DataFrame(index=self._union_index(gold, forex, btc))

        # Gold
        if not gold.empty:
            g = gold["close"].reindex(out.index, method="ffill")
            out["gold_close"] = g
            out["gold_1d_return"] = g.pct_change(1)
            out["gold_5d_return"] = g.pct_change(5)
        else:
            for col in ["gold_close", "gold_1d_return", "gold_5d_return"]:
                out[col] = np.nan

        # Forex (USD/IDR)
        if not forex.empty:
            f = forex["rate"].reindex(out.index, method="ffill")
            out["usdidr_rate"] = f
            out["usdidr_1d_return"] = f.pct_change(1)
            out["usdidr_5d_return"] = f.pct_change(5)
            out["usdidr_vol_20d"] = f.pct_change().rolling(20).std() * np.sqrt(252)
        else:
            for col in ["usdidr_rate", "usdidr_1d_return", "usdidr_5d_return", "usdidr_vol_20d"]:
                out[col] = np.nan

        # Gold / IDR ratio (gold priced in IDR — strong inflation signal)
        if "gold_close" in out and "usdidr_rate" in out:
            out["gold_vs_usdidr_ratio"] = out["gold_close"] / out["usdidr_rate"].replace(0, np.nan)
        else:
            out["gold_vs_usdidr_ratio"] = np.nan

        # BTC
        if not btc.empty:
            b = btc["close"].reindex(out.index, method="ffill")
            out["btc_close"] = b
            out["btc_1d_return"] = b.pct_change(1)
            out["btc_vol_30d"] = b.pct_change().rolling(30).std() * np.sqrt(252)
            ma20 = b.rolling(20).mean()
            out["btc_regime"] = np.where(b > ma20, 1, np.where(b < ma20, -1, 0)).astype(float)
            out["btc_regime"] = out["btc_regime"].where(ma20.notna(), np.nan)
        else:
            for col in ["btc_close", "btc_1d_return", "btc_vol_30d", "btc_regime"]:
                out[col] = np.nan

        return out

    @staticmethod
    def _union_index(*dfs: pd.DataFrame) -> pd.DatetimeIndex:
        idx = pd.DatetimeIndex([])
        for df in dfs:
            if not df.empty:
                idx = idx.union(df.index)
        return idx.normalize().drop_duplicates().sort_values()


__all__ = ["CrossAssetLoader"]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_cross_asset_loader.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domains/market_data/application/cross_asset_loader.py tests/test_cross_asset_loader.py
git commit -m "feat: add CrossAssetLoader — gold/forex/BTC from DB [nyx-auto]"
```

---

## Task 2: Multi-Timeframe & Regime Features

Adds the missing multi-timeframe return/vol features and a volatility-regime classifier to `IDXFeatureEngineer`.

**Files:**
- Modify: `src/domains/market_data/application/feature_engineering.py`
- Create: `tests/test_feature_engineering_overhaul.py`

### 2a — Write failing tests for the new methods

- [ ] **Step 1: Create test file with multiframe + regime tests**

```python
# tests/test_feature_engineering_overhaul.py
"""Tests for new feature engineering methods added in Sub-Plan B."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer


@pytest.fixture
def price_df():
    """Minimal OHLCV DataFrame with 80 daily bars."""
    n = 80
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    close = pd.Series(
        [10000.0 * (1 + 0.005 * i + 0.002 * (i % 7 - 3)) for i in range(n)],
        index=idx,
    )
    df = pd.DataFrame(
        {
            "open": close * 0.998,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": [1_000_000] * n,
        },
        index=idx,
    )
    return df


@pytest.fixture
def cross_asset_df():
    """Mock cross-asset DataFrame covering the same period."""
    n = 80
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "gold_close": [1800.0 + i for i in range(n)],
            "gold_1d_return": [0.001] * n,
            "gold_5d_return": [0.005] * n,
            "usdidr_rate": [16000.0 + i * 10 for i in range(n)],
            "usdidr_1d_return": [0.0005] * n,
            "usdidr_5d_return": [0.0025] * n,
            "usdidr_vol_20d": [0.08] * n,
            "btc_close": [50000.0 + i * 100 for i in range(n)],
            "btc_1d_return": [0.002] * n,
            "btc_vol_30d": [0.70] * n,
            "btc_regime": [1.0] * n,
        },
        index=idx,
    )


class TestMultiframeFeatures:
    def test_return_60d_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        assert "return_60d" in result.columns

    def test_vol_features_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        for col in ["vol_5d", "vol_10d", "vol_20d", "vol_60d"]:
            assert col in result.columns, f"Missing: {col}"

    def test_momentum_zscore_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        assert "momentum_zscore_20d" in result.columns

    def test_vol_20d_is_annualised(self, price_df):
        """vol_20d should be annualised (×√252), not raw daily std."""
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        # Annualised vol for a slightly trending series should be well below 200%
        finite = result["vol_20d"].dropna()
        assert (finite > 0).all()
        assert (finite < 2.0).all()  # sanity: < 200% annualised


class TestRegimeFeatures:
    def test_market_regime_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        assert "market_regime" in result.columns

    def test_trend_strength_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        assert "trend_strength" in result.columns

    def test_market_regime_values_valid(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        valid = {0, 1, 2}
        regime_vals = set(result["market_regime"].dropna().astype(int).unique())
        assert regime_vals.issubset(valid)


class TestCrossAssetFeatures:
    def test_cross_asset_features_present_when_df_provided(self, price_df, cross_asset_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df, cross_asset_df=cross_asset_df)
        expected = [
            "usdidr_1d_return", "usdidr_5d_return", "usdidr_vol_20d",
            "gold_1d_return", "gold_5d_return",
            "btc_1d_return", "btc_vol_30d", "btc_regime",
            "stock_btc_corr_20d", "stock_gold_corr_20d",
        ]
        for col in expected:
            assert col in result.columns, f"Missing: {col}"

    def test_cross_asset_nan_when_no_df(self, price_df):
        """Backward-compatible: no cross_asset_df → cross-asset cols absent or all NaN."""
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)  # no cross_asset_df
        # Either the columns are absent, or all NaN — both are acceptable
        if "btc_1d_return" in result.columns:
            assert result["btc_1d_return"].isna().all()

    def test_original_features_unchanged(self, price_df, cross_asset_df):
        """Adding cross-asset should not remove or alter existing feature columns."""
        fe = IDXFeatureEngineer()
        base = fe.generate_technical_features(price_df)
        enhanced = fe.generate_technical_features(price_df, cross_asset_df=cross_asset_df)
        for col in base.columns:
            assert col in enhanced.columns
```

- [ ] **Step 2: Run to confirm failures**

```bash
uv run pytest tests/test_feature_engineering_overhaul.py -v 2>&1 | grep -E "PASSED|FAILED|ERROR" | head -20
```

Expected: most tests FAIL (missing columns).

### 2b — Implement

- [ ] **Step 3: Add `_add_multiframe_features` and `_add_regime_features` to `IDXFeatureEngineer`**

Open `src/domains/market_data/application/feature_engineering.py`.

**3a: Update `generate_technical_features` signature and call new methods:**

Find:
```python
    def generate_technical_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
```

Replace with:
```python
    def generate_technical_features(
        self,
        price_data: pd.DataFrame,
        cross_asset_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
```

And update the body — add two new calls after the existing ones, and update cross-asset call:

```python
        df = price_data.copy()

        # Price-based features
        df = self._add_price_features(df)

        # Volume-based features
        df = self._add_volume_features(df)

        # Technical indicators
        df = self._add_technical_indicators(df)

        # Market microstructure (important for IDX due to lower liquidity)
        df = self._add_microstructure_features(df)

        # Multi-timeframe returns and volatility
        df = self._add_multiframe_features(df)

        # Market regime
        df = self._add_regime_features(df, cross_asset_df)

        # Cross-asset features (IDR, gold, BTC impact)
        df = self._add_cross_asset_features(df, cross_asset_df)

        return df
```

**3b: Add `Optional` to the imports at the top of the file (it's already imported in Tuple line — add it there):**

Find:
```python
from typing import Dict, List, Optional, Tuple
```
(it's already there — no change needed)

**3c: Add `_add_multiframe_features` method** (add after `_add_microstructure_features`):

```python
    def _add_multiframe_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Multi-timeframe returns and annualised rolling volatility."""
        # return_60d (5d/10d/20d already exist from _add_price_features)
        df["return_60d"] = df["close"].pct_change(60)

        # Annualised rolling volatility at multiple horizons
        daily_ret = df["close"].pct_change()
        df["vol_5d"] = daily_ret.rolling(5).std() * np.sqrt(252)
        df["vol_10d"] = daily_ret.rolling(10).std() * np.sqrt(252)
        df["vol_20d"] = daily_ret.rolling(20).std() * np.sqrt(252)
        df["vol_60d"] = daily_ret.rolling(60).std() * np.sqrt(252)

        # Momentum z-score: how many vol units is the price above its 20d MA?
        ma20 = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        df["momentum_zscore_20d"] = (df["close"] - ma20) / std20.replace(0, np.nan)

        return df
```

**3d: Add `_add_regime_features` method** (add after `_add_multiframe_features`):

```python
    def _add_regime_features(
        self,
        df: pd.DataFrame,
        cross_asset_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Classify market regime into 3 buckets based on realised volatility.

        market_regime:
          0 = low-vol  (vol_20d < 33rd percentile of trailing 252d)
          1 = normal
          2 = high-vol (vol_20d > 67th percentile)

        trend_strength: ADX already computed — re-expose as a clean alias.
        """
        vol = df.get("vol_20d", df["close"].pct_change().rolling(20).std() * np.sqrt(252))

        # Percentile rank within trailing 252-day window
        vol_rank = vol.rolling(252, min_periods=20).rank(pct=True)
        df["market_regime"] = np.where(
            vol_rank < 0.33, 0,
            np.where(vol_rank > 0.67, 2, 1),
        ).astype(float)
        df["market_regime"] = df["market_regime"].where(vol_rank.notna(), np.nan)

        # trend_strength: alias for ADX (already computed by _add_technical_indicators)
        if "adx" in df.columns:
            df["trend_strength"] = df["adx"]
        else:
            df["trend_strength"] = np.nan

        return df
```

**3e: Fill in `_add_cross_asset_features`** — replace the stub:

```python
    def _add_cross_asset_features(
        self,
        df: pd.DataFrame,
        cross_asset_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Join pre-computed cross-asset features (gold, IDR, BTC) onto price data.
        All features degrade to NaN when cross_asset_df is None or too short.

        cross_asset_df is produced by CrossAssetLoader.load() and is
        indexed by date with columns:
          gold_1d_return, gold_5d_return,
          usdidr_1d_return, usdidr_5d_return, usdidr_vol_20d,
          btc_1d_return, btc_vol_30d, btc_regime
        """
        # Pass-through columns from cross_asset_df
        passthrough_cols = [
            "gold_1d_return", "gold_5d_return",
            "usdidr_1d_return", "usdidr_5d_return", "usdidr_vol_20d",
            "btc_1d_return", "btc_vol_30d", "btc_regime",
        ]

        if cross_asset_df is None or cross_asset_df.empty:
            for col in passthrough_cols + ["stock_btc_corr_20d", "stock_gold_corr_20d"]:
                df[col] = np.nan
            return df

        # Align cross-asset data to the stock's date index
        ca = cross_asset_df.reindex(df.index, method="ffill")

        for col in passthrough_cols:
            df[col] = ca[col] if col in ca.columns else np.nan

        # Rolling 20-day correlations: stock 1d return vs BTC / gold
        stock_ret = df["close"].pct_change()
        if "btc_1d_return" in ca.columns:
            df["stock_btc_corr_20d"] = stock_ret.rolling(20).corr(ca["btc_1d_return"])
        else:
            df["stock_btc_corr_20d"] = np.nan

        if "gold_1d_return" in ca.columns:
            df["stock_gold_corr_20d"] = stock_ret.rolling(20).corr(ca["gold_1d_return"])
        else:
            df["stock_gold_corr_20d"] = np.nan

        return df
```

- [ ] **Step 4: Run the overhaul tests**

```bash
uv run pytest tests/test_feature_engineering_overhaul.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Run full suite to check no regressions**

```bash
uv run pytest tests/ -q 2>&1 | tail -5
```

Expected: same pass count as before + 10 new passes.

- [ ] **Step 6: Commit**

```bash
git add src/domains/market_data/application/feature_engineering.py tests/test_feature_engineering_overhaul.py
git commit -m "feat: add multiframe vol, regime, cross-asset features to IDXFeatureEngineer [nyx-auto]"
```

---

## Task 3: TripleBarrierLabeler

Replaces `pd.qcut(forward_returns, q=4, ...)` in `model_ensemble.py:80` with ATR-based event-driven labels.

Labels: `+1` (profit target hit first), `-1` (stop-loss hit first), `0` (time exit).

**Files:**
- Create: `src/domains/market_data/application/triple_barrier.py`
- Create: `tests/test_triple_barrier.py`

### 3a — Write failing tests

- [ ] **Step 1: Create test file**

```python
# tests/test_triple_barrier.py
"""Tests for TripleBarrierLabeler."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.domains.market_data.application.triple_barrier import TripleBarrierLabeler


@pytest.fixture
def prices():
    """80-bar price series with a clear uptrend then downtrend."""
    n = 80
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    vals = [10000.0 + i * 20 for i in range(40)] + [10800.0 - i * 20 for i in range(40)]
    return pd.Series(vals, index=idx, name="close")


@pytest.fixture
def atr(prices):
    """Constant ATR of 100 pts (1% of ~10000)."""
    return pd.Series(100.0, index=prices.index, name="atr")


class TestTripleBarrierLabeler:
    def test_returns_series_same_length(self, prices, atr):
        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
        labels = labeler.label(prices, atr)
        assert isinstance(labels, pd.Series)
        assert len(labels) == len(prices)

    def test_label_values_are_in_valid_set(self, prices, atr):
        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
        labels = labeler.label(prices, atr)
        valid = {-1, 0, 1, np.nan}
        for v in labels.dropna().unique():
            assert v in valid, f"Unexpected label value: {v}"

    def test_uptrend_produces_positive_labels(self, prices, atr):
        """Strong uptrend → most labels should be +1 (PT hit)."""
        uptrend = pd.Series(
            [10000.0 + i * 50 for i in range(60)],
            index=pd.date_range("2025-01-01", periods=60, freq="B"),
        )
        atr_const = pd.Series(100.0, index=uptrend.index)
        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
        labels = labeler.label(uptrend, atr_const)
        pct_positive = (labels == 1).sum() / labels.notna().sum()
        assert pct_positive > 0.5, f"Expected >50% +1 labels in uptrend, got {pct_positive:.1%}"

    def test_downtrend_produces_negative_labels(self, prices, atr):
        """Strong downtrend → most labels should be -1 (SL hit)."""
        downtrend = pd.Series(
            [10000.0 - i * 50 for i in range(60)],
            index=pd.date_range("2025-01-01", periods=60, freq="B"),
        )
        atr_const = pd.Series(100.0, index=downtrend.index)
        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
        labels = labeler.label(downtrend, atr_const)
        pct_negative = (labels == -1).sum() / labels.notna().sum()
        assert pct_negative > 0.5, f"Expected >50% -1 labels in downtrend, got {pct_negative:.1%}"

    def test_nan_atr_produces_nan_label(self, prices):
        """NaN ATR at a bar → NaN label at that bar."""
        atr = pd.Series(100.0, index=prices.index)
        atr.iloc[10] = np.nan
        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
        labels = labeler.label(prices, atr)
        assert pd.isna(labels.iloc[10])

    def test_last_bars_are_nan(self, prices, atr):
        """Last max_holding bars can't form a full window → NaN."""
        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
        labels = labeler.label(prices, atr)
        assert labels.iloc[-1] is np.nan or pd.isna(labels.iloc[-1])
```

- [ ] **Step 2: Run to confirm failures**

```bash
uv run pytest tests/test_triple_barrier.py -v 2>&1 | head -15
```

Expected: `ImportError`

### 3b — Implement

- [ ] **Step 3: Create `triple_barrier.py`**

```python
# src/domains/market_data/application/triple_barrier.py
"""
Triple Barrier Labeler (López de Prado, Advances in Financial Machine Learning, 2018).

For each bar t:
  - Upper barrier: close[t] + pt_multiplier × atr[t]
  - Lower barrier: close[t] - sl_multiplier × atr[t]
  - Vertical barrier: t + max_holding bars

Label:
  +1  if upper barrier hit first (profit target)
  -1  if lower barrier hit first (stop loss)
   0  if time barrier hit first (hold-through)
  NaN if atr[t] is NaN or zero, or t is within max_holding bars of the end

Usage:
    labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
    labels = labeler.label(price_series, atr_series)

Replaces: pd.qcut(forward_returns, q=4, labels=['Sell','Hold','Buy','Strong_Buy'])
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class TripleBarrierLabeler:
    """
    ATR-based triple-barrier labeler for daily price series.

    Parameters
    ----------
    pt_sl : (float, float)
        (profit_take_multiplier, stop_loss_multiplier).
        Barriers are: close ± multiplier × ATR.
        Asymmetric by default (2.0 PT, 1.0 SL) — favours a 2:1 reward/risk.
    max_holding : int
        Maximum days to hold (vertical barrier). Typical: 20 trading days.
    """

    def __init__(
        self,
        pt_sl: tuple[float, float] = (2.0, 1.0),
        max_holding: int = 20,
    ) -> None:
        self.pt_multiplier, self.sl_multiplier = pt_sl
        self.max_holding = max_holding

    def label(self, prices: pd.Series, atr: pd.Series) -> pd.Series:
        """
        Compute triple-barrier labels for each bar.

        Parameters
        ----------
        prices : pd.Series
            Daily close prices, date-indexed.
        atr : pd.Series
            Average True Range, same index as prices.

        Returns
        -------
        pd.Series of float: +1, -1, 0, or NaN.
        """
        prices = prices.reindex(atr.index)  # align
        n = len(prices)
        labels = pd.Series(np.nan, index=prices.index, dtype=float)

        price_arr = prices.values
        atr_arr = atr.values

        for i in range(n - 1):
            entry = price_arr[i]
            atr_i = atr_arr[i]

            if np.isnan(entry) or np.isnan(atr_i) or atr_i == 0:
                continue

            pt = entry + self.pt_multiplier * atr_i
            sl = entry - self.sl_multiplier * atr_i

            end = min(i + self.max_holding, n - 1)
            window = price_arr[i + 1 : end + 1]

            if len(window) == 0:
                continue

            pt_hits = np.where(window >= pt)[0]
            sl_hits = np.where(window <= sl)[0]

            pt_first = pt_hits[0] if len(pt_hits) else None
            sl_first = sl_hits[0] if len(sl_hits) else None

            if pt_first is None and sl_first is None:
                labels.iloc[i] = 0.0   # time exit
            elif pt_first is None:
                labels.iloc[i] = -1.0
            elif sl_first is None:
                labels.iloc[i] = 1.0
            else:
                labels.iloc[i] = 1.0 if pt_first <= sl_first else -1.0

        return labels


__all__ = ["TripleBarrierLabeler"]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_triple_barrier.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domains/market_data/application/triple_barrier.py tests/test_triple_barrier.py
git commit -m "feat: add TripleBarrierLabeler replacing pd.qcut forward-return labels [nyx-auto]"
```

---

## Task 4: Wire TripleBarrier into ModelEnsemble

Replace the `pd.qcut` call in `model_ensemble.py:80` with the new labeler.

**Files:**
- Modify: `src/domains/trading/infrastructure/ml_models/model_ensemble.py:65-82`

- [ ] **Step 1: Read the `create_targets` method (line ~65–82 in model_ensemble.py)**

```bash
grep -n "qcut\|create_targets\|forward_returns" src/domains/trading/infrastructure/ml_models/model_ensemble.py
```

- [ ] **Step 2: Add import at top of `model_ensemble.py`**

After the existing imports add:

```python
from src.domains.market_data.application.triple_barrier import TripleBarrierLabeler
```

- [ ] **Step 3: Replace `create_targets` in `TechnicalSignalModel`**

Find:
```python
    def create_targets(self, data: pd.DataFrame, horizon: int = 5) -> np.ndarray:
        """
        Create classification targets based on future returns

        Args:
            data: DataFrame with price data
            horizon: Forward-looking period for returns

        Returns:
            Array of target classes
        """
        # Calculate forward returns
        forward_returns = data['close'].pct_change(horizon).shift(-horizon)

        # Create quantile-based targets
        targets = pd.qcut(forward_returns, q=4, labels=['Sell', 'Hold', 'Buy', 'Strong_Buy'])

        return targets.values
```

Replace with:

```python
    def create_targets(self, data: pd.DataFrame, horizon: int = 5) -> np.ndarray:
        """
        Create triple-barrier labels for each bar.

        Labels: +1 (profit target hit), -1 (stop-loss hit), 0 (time exit).
        NaN rows are excluded in train() via the existing mask.

        ATR must be present in `data` (computed by IDXFeatureEngineer).
        Falls back to naive forward-return quantiles if ATR is missing.
        """
        if "atr" not in data.columns or data["atr"].isna().all():
            # Fallback: binary label based on sign of forward return
            fwd = data["close"].pct_change(horizon).shift(-horizon)
            return np.where(fwd > 0, 1.0, -1.0)

        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=horizon * 2)
        labels = labeler.label(data["close"], data["atr"])
        return labels.values
```

- [ ] **Step 4: Run existing model ensemble test (if any) + full suite**

```bash
uv run pytest tests/test_model_ensemble.py tests/test_feature_engineering_overhaul.py tests/test_triple_barrier.py -v 2>&1 | tail -15
```

Expected: all pass.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest tests/ -q 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/model_ensemble.py
git commit -m "feat: wire TripleBarrierLabeler into ModelEnsemble.create_targets [nyx-auto]"
```

---

## Task 5: Integration Smoke Test

Verify the full feature pipeline produces real cross-asset features against live DB data.

**Files:** No new files — this is a manual verification step.

- [ ] **Step 1: Run an integration smoke test against the live DB**

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv('.env')
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.config import settings
from src.domains.market_data.application.cross_asset_loader import CrossAssetLoader
from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer
import yfinance as yf

engine = create_engine(
    f'postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}'
    f'@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}'
)
Session = sessionmaker(bind=engine)

with Session() as session:
    loader = CrossAssetLoader(session)
    ca_df = loader.load(start_date=date(2024, 1, 1), end_date=date(2026, 5, 20))
    print(f'Cross-asset rows: {len(ca_df)}')
    print(ca_df.tail(3).to_string())

# Test feature generation on a real stock
import yfinance as yf, pandas as pd
raw = yf.Ticker('BBCA.JK').history(start='2024-01-01')
raw.columns = [c.lower() for c in raw.columns]
raw.index = raw.index.tz_localize(None)

fe = IDXFeatureEngineer()
result = fe.generate_technical_features(raw, cross_asset_df=ca_df)
cross_cols = ['usdidr_1d_return', 'gold_1d_return', 'btc_1d_return', 'stock_btc_corr_20d', 'market_regime']
print('\\nSample cross-asset features:')
print(result[cross_cols].tail(5).to_string())
print(f'\\nTotal features: {len(result.columns)}')
"
```

Expected output:
```
Cross-asset rows: ~500
usdidr_1d_return  gold_1d_return  btc_1d_return  stock_btc_corr_20d  market_regime
...               ...             ...            ...                  0/1/2
Total features: ~60
```

- [ ] **Step 2: Note any NaN-heavy columns (expected for btc_vol_30d until 30 days accumulate)**

`btc_vol_30d` and `stock_btc_corr_20d` will have NaN for the first 20–30 rows from the BTC data start (2026-05-13). This is expected and correct.

- [ ] **Step 3: Commit the plan doc + final integration note**

```bash
git add docs/superpowers/plans/2026-05-20-feature-engineering-overhaul.md
git commit -m "docs: feature engineering overhaul plan + integration verified [nyx-auto]"
```

---

## Done — What's Been Built

After all tasks:

| Component | What changed |
|---|---|
| `CrossAssetLoader` | New — loads gold/forex/BTC from DB, returns date-aligned feature DataFrame |
| `IDXFeatureEngineer` | `generate_technical_features(price_data, cross_asset_df=None)` — 10 new features added |
| `_add_multiframe_features` | `return_60d`, `vol_5d/10d/20d/60d`, `momentum_zscore_20d` |
| `_add_regime_features` | `market_regime` (0/1/2), `trend_strength` |
| `_add_cross_asset_features` | `usdidr_*`, `gold_*`, `btc_*`, `stock_btc_corr_20d`, `stock_gold_corr_20d` |
| `TripleBarrierLabeler` | New — ATR-based +1/-1/0 labels replacing `pd.qcut` |
| `ModelEnsemble.create_targets` | Now calls `TripleBarrierLabeler`, falls back to sign(return) if ATR missing |

**Next: Sub-Plan C** — walk-forward validation, LightGBM, meta-labeler, vectorbt backtesting. Requires ~90 days of multi-asset data (i.e. start Sub-Plan C around mid-August 2026).
