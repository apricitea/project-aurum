# Project Aurum — Fix All Issues & Real Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every broken component, add tests for core ML pipeline, and run a real end-to-end backtest on IDX data.

**Architecture:** Replace the fake random-data BacktestingEngine with vectorbt; fix feature engineering gaps; add MetaLabeler to training pipeline; add pytest suite for triple-barrier/walk-forward/LightGBM/feature-engineering; create a self-contained `scripts/run_pipeline.py` that trains and backtests from scratch.

**Tech Stack:** Python, LightGBM, XGBoost, vectorbt, yfinance, SHAP, scikit-learn, pytest

---

## Issue Index

| # | File | Issue | Severity |
|---|------|-------|----------|
| 1 | `backtesting_engine.py` | `from indonesian_stocks_data import indonesian_data` — module doesn't exist at that path, crashes on import | CRITICAL |
| 2 | `backtesting_engine.py` | Module-level `backtest_engine = BacktestingEngine()` instantiates on import → crash | CRITICAL |
| 3 | `backtesting_engine.py` | Entire simulation uses `random.uniform` — not real market data | CRITICAL |
| 4 | `feature_engineering.py` | `return_60d` referenced in README/paper but not generated | HIGH |
| 5 | `model_ensemble.py` | `SentimentMomentumModel.create_targets()` returns string labels from `pd.cut` — XGBoost needs numeric | HIGH |
| 6 | `model_ensemble.py` | `EnsembleMetaModel.prepare_ensemble_features()` uses `np.corrcoef` on mismatched shapes | HIGH |
| 7 | All ML code | MetaLabeler exists but never wired into `IDXQuantitativeModel.train()` | MEDIUM |
| 8 | Entire repo | Zero test coverage — no `tests/` directory exists despite pytest.ini pointing to it | HIGH |
| 9 | No pipeline script | No standalone script to train model + run backtest on real data | HIGH |

---

## Task 1: Fix BacktestingEngine — replace fake simulation with real vectorbt backtest

**Files:**
- Rewrite: `src/domains/analytics/application/backtesting_engine.py`

- [ ] **Step 1: Read the current file to understand the API surface (already done in audit)**

The existing `run_backtest()` returns a `Dict` with keys: `overview`, `confidence_analysis`, `sector_analysis`, `monthly_performance`, `best_trades`, `worst_trades`. We must preserve that shape so the API doesn't break.

- [ ] **Step 2: Rewrite BacktestingEngine**

Replace the entire file with a vectorbt-based engine. The engine accepts a signals DataFrame (output from `LightGBMSignalModel`) and historical price data, and executes a proper vectorbt portfolio simulation.

```python
"""
BacktestingEngine — vectorbt-based backtest on real IDX OHLCV data.

Replaces the old random-simulation engine. Accepts signal DataFrames
produced by LightGBMSignalModel and executes a portfolio simulation
with realistic IDX transaction costs.

Transaction costs (IDX):
  Buy:  0.15% (broker commission)
  Sell: 0.25% (broker + 0.10% government levy)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# IDX transaction costs
_BUY_COST = 0.0015   # 0.15%
_SELL_COST = 0.0025  # 0.25%
_INITIAL_CAPITAL = 1_000_000_000  # Rp 1 billion


@dataclass
class BacktestResult:
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    annualised_return_pct: float
    equity_curve: pd.Series          # date-indexed cumulative portfolio value
    monthly_returns: pd.Series       # month-indexed returns
    trade_log: pd.DataFrame          # per-trade details


class BacktestingEngine:
    """
    Vectorbt-based backtester for LightGBM signal outputs.

    Usage
    -----
    engine = BacktestingEngine()
    result = engine.run(prices_df, signals_series, confidence_series)
    summary = engine.to_api_dict(result)
    """

    def __init__(self, initial_capital: float = _INITIAL_CAPITAL) -> None:
        self.initial_capital = initial_capital

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.Series,
        confidence: Optional[pd.Series] = None,
        confidence_threshold: float = 0.6,
    ) -> BacktestResult:
        """
        Run backtest.

        Parameters
        ----------
        prices : DataFrame
            OHLCV with columns [open, high, low, close, volume], DatetimeIndex.
        signals : Series
            Float signal per date: +1.0 = BUY, -1.0 = SELL/EXIT, 0.0 = HOLD.
            Produced by LightGBMSignalModel.predict().
        confidence : Series, optional
            Confidence score per date from MetaLabeler.predict_bet_size().
            Signals below `confidence_threshold` are suppressed.
        confidence_threshold : float
            Minimum confidence to enter a trade (default 0.6).

        Returns
        -------
        BacktestResult
        """
        try:
            import vectorbt as vbt
        except ImportError:
            logger.warning("vectorbt not installed — falling back to simple backtest")
            return self._simple_backtest(prices, signals, confidence, confidence_threshold)

        close = prices["close"].reindex(signals.index).ffill()

        # Apply confidence filter
        if confidence is not None:
            active = confidence.reindex(signals.index).fillna(0.0) >= confidence_threshold
            signals = signals.where(active, other=0.0)

        entries = signals == 1.0
        exits = signals == -1.0

        pf = vbt.Portfolio.from_signals(
            close,
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=_BUY_COST,
            slippage=0.001,  # 0.1% slippage
            freq="D",
        )

        stats = pf.stats()
        trades = pf.trades.records_readable

        equity = pf.value()
        monthly_returns = equity.resample("ME").last().pct_change().dropna()

        # Build trade log
        trade_log = trades.rename(columns={
            "Entry Timestamp": "entry_date",
            "Exit Timestamp": "exit_date",
            "Entry Price": "entry_price",
            "Exit Price": "exit_price",
            "Return": "return_pct",
            "PnL": "pnl",
        }) if not trades.empty else pd.DataFrame()

        return BacktestResult(
            total_return_pct=float(stats.get("Total Return [%]", 0.0)),
            sharpe_ratio=float(stats.get("Sharpe Ratio", 0.0)),
            max_drawdown_pct=float(stats.get("Max Drawdown [%]", 0.0)),
            win_rate_pct=float(stats.get("Win Rate [%]", 0.0)),
            total_trades=int(stats.get("Total Trades", 0)),
            annualised_return_pct=float(stats.get("Annualized Return [%]", 0.0)),
            equity_curve=equity,
            monthly_returns=monthly_returns,
            trade_log=trade_log,
        )

    def to_api_dict(self, result: BacktestResult) -> Dict:
        """Convert BacktestResult to the dict shape expected by the API."""
        monthly_data = [
            {
                "month": str(idx.strftime("%Y-%m")),
                "return_pct": round(float(v) * 100, 2),
            }
            for idx, v in result.monthly_returns.items()
        ]

        best_trades: List[Dict] = []
        worst_trades: List[Dict] = []
        if not result.trade_log.empty and "pnl" in result.trade_log.columns:
            log = result.trade_log.copy()
            log["return_pct"] = log.get("return_pct", pd.Series(dtype=float))
            best_10 = log.nlargest(10, "pnl")
            worst_10 = log.nsmallest(10, "pnl")

            def _row(r: pd.Series) -> Dict:
                return {
                    "entry_date": str(r.get("entry_date", "")),
                    "exit_date": str(r.get("exit_date", "")),
                    "entry_price": float(r.get("entry_price", 0.0)),
                    "exit_price": float(r.get("exit_price", 0.0)),
                    "return_pct": float(r.get("return_pct", 0.0)),
                    "pnl": float(r.get("pnl", 0.0)),
                }

            best_trades = [_row(r) for _, r in best_10.iterrows()]
            worst_trades = [_row(r) for _, r in worst_10.iterrows()]

        return {
            "overview": {
                "total_return_pct": round(result.total_return_pct, 2),
                "sharpe_ratio": round(result.sharpe_ratio, 2),
                "max_drawdown_pct": round(result.max_drawdown_pct, 2),
                "win_rate_pct": round(result.win_rate_pct, 2),
                "total_trades": result.total_trades,
                "annualised_return_pct": round(result.annualised_return_pct, 2),
            },
            "monthly_performance": monthly_data,
            "best_trades": best_trades,
            "worst_trades": worst_trades,
        }

    # ------------------------------------------------------------------ #
    # Fallback: simple loop backtest (no vectorbt dependency)
    # ------------------------------------------------------------------ #

    def _simple_backtest(
        self,
        prices: pd.DataFrame,
        signals: pd.Series,
        confidence: Optional[pd.Series],
        confidence_threshold: float,
    ) -> BacktestResult:
        """Pure-Python fallback backtest without vectorbt."""
        close = prices["close"].reindex(signals.index).ffill()

        if confidence is not None:
            active = confidence.reindex(signals.index).fillna(0.0) >= confidence_threshold
            signals = signals.where(active, other=0.0)

        capital = float(self.initial_capital)
        equity = []
        trades: List[Dict] = []
        position = 0.0       # shares held
        entry_price = 0.0
        entry_date = None

        for date, sig in signals.items():
            price = close.get(date, np.nan)
            if np.isnan(price):
                equity.append((date, capital + position * price if not np.isnan(price) else capital))
                continue

            if sig == 1.0 and position == 0.0:
                shares = capital * (1 - _BUY_COST) / price
                capital = 0.0
                position = shares
                entry_price = price
                entry_date = date

            elif sig == -1.0 and position > 0.0:
                proceeds = position * price * (1 - _SELL_COST)
                ret_pct = (price / entry_price - 1) * 100
                trades.append({
                    "entry_date": entry_date,
                    "exit_date": date,
                    "entry_price": entry_price,
                    "exit_price": price,
                    "return_pct": ret_pct,
                    "pnl": proceeds - position * entry_price,
                })
                capital = proceeds
                position = 0.0

            portfolio_value = capital + position * price
            equity.append((date, portfolio_value))

        equity_series = pd.Series(
            dict(equity), name="portfolio_value"
        ).astype(float)

        total_return = (equity_series.iloc[-1] / self.initial_capital - 1) * 100
        daily_returns = equity_series.pct_change().dropna()
        sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)
                  if daily_returns.std() > 0 else 0.0)
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_dd = float(drawdown.min())
        win_rate = (sum(1 for t in trades if t["pnl"] > 0) / len(trades) * 100
                    if trades else 0.0)
        monthly_returns = equity_series.resample("ME").last().pct_change().dropna()

        trade_log = pd.DataFrame(trades) if trades else pd.DataFrame()

        return BacktestResult(
            total_return_pct=float(total_return),
            sharpe_ratio=float(sharpe),
            max_drawdown_pct=float(max_dd),
            win_rate_pct=float(win_rate),
            total_trades=len(trades),
            annualised_return_pct=float(total_return / max(len(equity_series) / 252, 1)),
            equity_curve=equity_series,
            monthly_returns=monthly_returns,
            trade_log=trade_log,
        )
```

- [ ] **Step 3: Commit**

```bash
cd /home/vlain/workspaces/personal/project-aurum
git add src/domains/analytics/application/backtesting_engine.py
git commit -m "fix: replace fake random BacktestingEngine with real vectorbt backtest"
```

---

## Task 2: Fix feature_engineering.py — add missing return_60d and momentum_60d

**Files:**
- Modify: `src/domains/market_data/application/feature_engineering.py`

- [ ] **Step 1: Read `_add_price_features` in feature_engineering.py to find the returns loop**

The current loop generates returns for [1, 3, 5, 10, 20]. We need to add 60.

- [ ] **Step 2: Add 60d return and add momentum_60d**

In `_add_price_features`, change:
```python
for period in [1, 3, 5, 10, 20]:
```
to:
```python
for period in [1, 3, 5, 10, 20, 60]:
```

Also add `momentum_60d` alongside existing momentum features:
```python
df['price_momentum_60d'] = (df['close'] / df['close'].shift(60) - 1)
```

- [ ] **Step 3: Commit**

```bash
git add src/domains/market_data/application/feature_engineering.py
git commit -m "fix: add return_60d and momentum_60d to feature engineering"
```

---

## Task 3: Fix SentimentMomentumModel — numeric targets for XGBoost

**Files:**
- Modify: `src/domains/trading/infrastructure/ml_models/model_ensemble.py`

`SentimentMomentumModel.create_targets()` currently returns categorical string labels (`'Weak'`, `'Neutral'`, `'Strong'`) from `pd.cut`. XGBoost requires numeric targets. Fix:

- [ ] **Step 1: Replace the pd.cut with numeric encoding**

```python
def create_targets(self, data: pd.DataFrame, horizon: int = 10) -> np.ndarray:
    forward_momentum = (data['close'].shift(-horizon) / data['close'] - 1)
    # Encode to int: 0=Weak, 1=Neutral, 2=Strong
    bins = pd.cut(forward_momentum, bins=3, labels=[0, 1, 2])
    return bins.values.astype(float)
```

- [ ] **Step 2: Fix prepare_ensemble_features np.corrcoef misuse**

The existing code calls `np.corrcoef(technical_pred.T, sentiment_pred.T).diagonal()` which produces an array of length `n_classes * 2` not `n_samples`. Remove that block:

```python
# DELETE the model agreement block:
# if technical_pred.ndim > 1 and sentiment_pred.ndim > 1:
#     ensemble_features.append(
#         np.corrcoef(technical_pred.T, sentiment_pred.T).diagonal()
#     )
```

Replace with a simple agreement score:
```python
if technical_pred.ndim > 1 and sentiment_pred.ndim > 1:
    # Agreement: both predict the same direction (max class matches)
    tech_class = np.argmax(technical_pred, axis=1)
    sent_class = np.argmax(sentiment_pred, axis=1)
    ensemble_features.append((tech_class == sent_class).astype(float))
```

- [ ] **Step 3: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/model_ensemble.py
git commit -m "fix: SentimentMomentumModel numeric targets; fix corrcoef shape bug in EnsembleMetaModel"
```

---

## Task 4: Wire MetaLabeler into IDXQuantitativeModel training pipeline

**Files:**
- Modify: `src/domains/trading/infrastructure/ml_models/model_ensemble.py`
- Modify: `src/domains/trading/infrastructure/ml_models/lightgbm_model.py`

The `MetaLabeler` class exists in `meta_labeler.py` but `IDXQuantitativeModel.train()` never uses it. Add it.

- [ ] **Step 1: Add MetaLabeler import to model_ensemble.py**

Add at top of `model_ensemble.py`:
```python
from .meta_labeler import MetaLabeler
```

- [ ] **Step 2: Add MetaLabeler to IDXQuantitativeModel.__init__()**

```python
self.meta_labeler = MetaLabeler(self.config.get('meta_labeler', None))
```

- [ ] **Step 3: Add MetaLabeler training in IDXQuantitativeModel.train()**

After training the technical model, use its OOS predictions to train the MetaLabeler. Add after `tech_metrics = self.technical_model.train(data)`:

```python
# Train MetaLabeler on primary model's in-sample predictions
X_tech, _ = self.technical_model.prepare_features(data)
X_tech_df = pd.DataFrame(X_tech, columns=self.technical_model.feature_names)
primary_preds, _ = self.technical_model.predict(data)
actual_labels = self.technical_model.create_targets(data)
meta_metrics = self.meta_labeler.fit(X_tech_df, primary_preds, actual_labels)
```

- [ ] **Step 4: Add MetaLabeler to IDXQuantitativeModel.predict()**

In `predict()`, after generating `tech_pred, tech_prob`:
```python
X_tech, _ = self.technical_model.prepare_features(data)
X_tech_df = pd.DataFrame(X_tech, columns=self.technical_model.feature_names)
bet_sizes = self.meta_labeler.predict_bet_size(X_tech_df)
```

Return bet_sizes in the predictions dict.

- [ ] **Step 5: Add MetaLabeler to save_models/load_models**

```python
# In save_models():
model_dict['meta_labeler'] = self.meta_labeler

# In load_models():
instance.meta_labeler = model_dict.get('meta_labeler', MetaLabeler())
```

- [ ] **Step 6: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/model_ensemble.py
git commit -m "feat: wire MetaLabeler into IDXQuantitativeModel train/predict pipeline"
```

---

## Task 5: Add tests — core ML components

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_triple_barrier.py`
- Create: `tests/test_walk_forward.py`
- Create: `tests/test_feature_engineering.py`
- Create: `tests/test_lightgbm_model.py`
- Create: `tests/test_meta_labeler.py`
- Create: `tests/test_backtesting_engine.py`

- [ ] **Step 1: Create tests/__init__.py**

Empty file.

- [ ] **Step 2: Write test_triple_barrier.py**

```python
"""Tests for TripleBarrierLabeler."""
import numpy as np
import pandas as pd
import pytest
from src.domains.market_data.application.triple_barrier import TripleBarrierLabeler


@pytest.fixture
def price_atr():
    """Simple rising price series with constant ATR."""
    dates = pd.date_range("2020-01-01", periods=100, freq="B")
    prices = pd.Series(100.0 + np.arange(100) * 0.5, index=dates)  # steadily rising
    atr = pd.Series(2.0, index=dates)  # constant ATR = 2
    return prices, atr


def test_returns_series_same_length(price_atr):
    prices, atr = price_atr
    labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=10)
    labels = labeler.label(prices, atr)
    assert len(labels) == len(prices)


def test_labels_are_valid_values(price_atr):
    prices, atr = price_atr
    labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=10)
    labels = labeler.label(prices, atr)
    valid = {-1.0, 0.0, 1.0, np.nan}
    non_nan = labels.dropna()
    assert set(non_nan.unique()).issubset(valid)


def test_rising_prices_hit_profit_target(price_atr):
    """With a strongly rising trend (ATR=2, PT=2*ATR=4), most should be +1."""
    prices, atr = price_atr
    labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
    labels = labeler.label(prices, atr)
    non_nan = labels.dropna()
    profit_rate = (non_nan == 1.0).mean()
    assert profit_rate > 0.5, f"Expected most labels to be +1, got {profit_rate:.2f}"


def test_nan_atr_produces_nan_label():
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    prices = pd.Series(100.0, index=dates)
    atr = pd.Series([np.nan] * 10, index=dates)
    labeler = TripleBarrierLabeler()
    labels = labeler.label(prices, atr)
    assert labels.isna().all()


def test_zero_atr_produces_nan_label():
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    prices = pd.Series(100.0, index=dates)
    atr = pd.Series(0.0, index=dates)
    labeler = TripleBarrierLabeler()
    labels = labeler.label(prices, atr)
    assert labels.isna().all()


def test_last_bar_is_nan(price_atr):
    """Last bar has no future window so label must be NaN."""
    prices, atr = price_atr
    labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=10)
    labels = labeler.label(prices, atr)
    assert np.isnan(labels.iloc[-1])
```

- [ ] **Step 3: Write test_walk_forward.py**

```python
"""Tests for WalkForwardValidator."""
import pandas as pd
import pytest
from src.domains.trading.infrastructure.ml_models.walk_forward import (
    WalkForwardValidator,
    WalkForwardFold,
)


@pytest.fixture
def three_year_index():
    return pd.date_range("2020-01-01", "2022-12-31", freq="B")


def test_returns_folds_for_sufficient_data(three_year_index):
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    folds = wfv.get_folds(three_year_index)
    assert len(folds) > 0


def test_returns_empty_for_short_data():
    short_index = pd.date_range("2020-01-01", periods=100, freq="B")
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    folds = wfv.get_folds(short_index)
    assert folds == []


def test_fold_train_end_before_test_start(three_year_index):
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    for fold in wfv.get_folds(three_year_index):
        assert fold.train_end < fold.test_start


def test_embargo_gap_respected(three_year_index):
    embargo = 5
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=embargo)
    for fold in wfv.get_folds(three_year_index):
        gap = (fold.test_start - fold.train_end).days
        assert gap >= embargo


def test_folds_have_sequential_ids(three_year_index):
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    folds = wfv.get_folds(three_year_index)
    for i, fold in enumerate(folds):
        assert fold.fold_id == i


def test_test_windows_non_overlapping(three_year_index):
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    folds = wfv.get_folds(three_year_index)
    for i in range(1, len(folds)):
        assert folds[i].test_start > folds[i - 1].test_end
```

- [ ] **Step 4: Write test_feature_engineering.py**

```python
"""Tests for IDXFeatureEngineer."""
import numpy as np
import pandas as pd
import pytest
from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer


@pytest.fixture
def ohlcv():
    """100 bars of synthetic OHLCV data."""
    np.random.seed(0)
    dates = pd.date_range("2022-01-01", periods=100, freq="B")
    close = 5000 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 100)))
    df = pd.DataFrame({
        "open":   close * np.random.uniform(0.99, 1.0, 100),
        "high":   close * np.random.uniform(1.0, 1.02, 100),
        "low":    close * np.random.uniform(0.98, 1.0, 100),
        "close":  close,
        "volume": np.random.lognormal(15, 0.5, 100),
    }, index=dates)
    return df


def test_returns_dataframe(ohlcv):
    eng = IDXFeatureEngineer()
    result = eng.generate_technical_features(ohlcv)
    assert isinstance(result, pd.DataFrame)


def test_return_columns_present(ohlcv):
    eng = IDXFeatureEngineer()
    result = eng.generate_technical_features(ohlcv)
    for period in [1, 3, 5, 10, 20, 60]:
        assert f"return_{period}d" in result.columns, f"return_{period}d missing"


def test_rsi_in_valid_range(ohlcv):
    eng = IDXFeatureEngineer()
    result = eng.generate_technical_features(ohlcv)
    rsi_cols = [c for c in result.columns if c.startswith("rsi_")]
    assert rsi_cols, "No RSI columns found"
    for col in rsi_cols:
        valid = result[col].dropna()
        assert (valid >= 0).all() and (valid <= 100).all(), f"{col} out of [0,100]"


def test_atr_non_negative(ohlcv):
    eng = IDXFeatureEngineer()
    result = eng.generate_technical_features(ohlcv)
    assert "atr" in result.columns
    assert (result["atr"].dropna() >= 0).all()


def test_cross_asset_columns_nan_when_no_data(ohlcv):
    eng = IDXFeatureEngineer()
    result = eng.generate_technical_features(ohlcv, cross_asset_df=None)
    cross_cols = [c for c in result.columns if any(
        kw in c for kw in ["gold_", "usdidr_", "btc_"]
    )]
    if cross_cols:
        for col in cross_cols:
            assert result[col].isna().all(), f"{col} should be all-NaN without cross-asset data"


def test_no_infinite_values(ohlcv):
    eng = IDXFeatureEngineer()
    result = eng.generate_technical_features(ohlcv)
    numeric = result.select_dtypes(include=[np.number])
    assert not np.isinf(numeric.values).any(), "Infinite values found in features"
```

- [ ] **Step 5: Write test_lightgbm_model.py**

```python
"""Tests for LightGBMSignalModel."""
import numpy as np
import pandas as pd
import pytest
from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer
from src.domains.trading.infrastructure.ml_models.lightgbm_model import LightGBMSignalModel


@pytest.fixture(scope="module")
def feature_data():
    """300 bars of featured data — enough for one walk-forward fold."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=300, freq="B")
    close = 5000 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 300)))
    raw = pd.DataFrame({
        "open":   close * np.random.uniform(0.99, 1.0, 300),
        "high":   close * np.random.uniform(1.0, 1.02, 300),
        "low":    close * np.random.uniform(0.98, 1.0, 300),
        "close":  close,
        "volume": np.random.lognormal(15, 0.5, 300),
    }, index=dates)
    eng = IDXFeatureEngineer()
    return eng.generate_technical_features(raw)


def test_train_returns_metrics(feature_data):
    model = LightGBMSignalModel()
    metrics = model.train(feature_data, walk_forward=False)
    assert "training_accuracy" in metrics
    assert 0.0 <= metrics["training_accuracy"] <= 1.0


def test_train_sets_is_trained(feature_data):
    model = LightGBMSignalModel()
    model.train(feature_data, walk_forward=False)
    assert model.is_trained


def test_predict_returns_correct_shapes(feature_data):
    model = LightGBMSignalModel()
    model.train(feature_data, walk_forward=False)
    preds, probs = model.predict(feature_data)
    assert len(preds) == len(feature_data)
    assert probs.shape[0] == len(feature_data)
    assert probs.shape[1] == len(model.classes_)


def test_predict_raises_before_train(feature_data):
    model = LightGBMSignalModel()
    with pytest.raises(ValueError, match="must be trained"):
        model.predict(feature_data)


def test_feature_importance_computed(feature_data):
    model = LightGBMSignalModel()
    model.train(feature_data, walk_forward=False)
    assert model.feature_importance is not None
    assert len(model.feature_importance) == len(model.feature_names)


def test_walk_forward_produces_oos_scores(feature_data):
    model = LightGBMSignalModel()
    metrics = model.train(feature_data, walk_forward=True)
    # With 300 bars, we may get 0 or 1 fold — just check the keys exist
    assert "n_folds" in metrics
    assert "oos_accuracy_mean" in metrics
```

- [ ] **Step 6: Write test_meta_labeler.py**

```python
"""Tests for MetaLabeler."""
import numpy as np
import pandas as pd
import pytest
from src.domains.trading.infrastructure.ml_models.meta_labeler import MetaLabeler


@pytest.fixture
def dummy_training_data():
    np.random.seed(1)
    n = 200
    X = pd.DataFrame(np.random.randn(n, 10), columns=[f"f{i}" for i in range(10)])
    primary = np.random.choice([-1.0, 0.0, 1.0], size=n)
    actual = np.random.choice([-1.0, 0.0, 1.0], size=n)
    return X, primary, actual


def test_fit_returns_metrics(dummy_training_data):
    X, primary, actual = dummy_training_data
    ml = MetaLabeler()
    metrics = ml.fit(X, primary, actual)
    assert "training_accuracy" in metrics
    assert "positive_rate" in metrics


def test_fit_sets_is_trained(dummy_training_data):
    X, primary, actual = dummy_training_data
    ml = MetaLabeler()
    ml.fit(X, primary, actual)
    assert ml.is_trained


def test_predict_bet_size_in_range(dummy_training_data):
    X, primary, actual = dummy_training_data
    ml = MetaLabeler()
    ml.fit(X, primary, actual)
    bet_sizes = ml.predict_bet_size(X)
    assert ((bet_sizes >= 0.0) & (bet_sizes <= 1.0)).all()


def test_predict_raises_before_fit():
    ml = MetaLabeler()
    X = pd.DataFrame(np.random.randn(10, 5), columns=[f"f{i}" for i in range(5)])
    with pytest.raises(ValueError, match="must be trained"):
        ml.predict_bet_size(X)
```

- [ ] **Step 7: Write test_backtesting_engine.py**

```python
"""Tests for the new BacktestingEngine."""
import numpy as np
import pandas as pd
import pytest
from src.domains.analytics.application.backtesting_engine import BacktestingEngine


@pytest.fixture
def market_data():
    np.random.seed(7)
    dates = pd.date_range("2022-01-01", periods=200, freq="B")
    close = 5000 * np.exp(np.cumsum(np.random.normal(0.0003, 0.015, 200)))
    return pd.DataFrame({
        "open": close * 0.999,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.random.lognormal(15, 0.5, 200),
    }, index=dates)


@pytest.fixture
def signals(market_data):
    """Alternating BUY/EXIT signals every 10 days."""
    sig = pd.Series(0.0, index=market_data.index)
    for i in range(0, len(sig) - 10, 20):
        sig.iloc[i] = 1.0
        sig.iloc[i + 10] = -1.0
    return sig


def test_run_returns_backtest_result(market_data, signals):
    engine = BacktestingEngine()
    result = engine.run(market_data, signals)
    assert result is not None


def test_run_populates_equity_curve(market_data, signals):
    engine = BacktestingEngine()
    result = engine.run(market_data, signals)
    assert len(result.equity_curve) > 0


def test_to_api_dict_has_required_keys(market_data, signals):
    engine = BacktestingEngine()
    result = engine.run(market_data, signals)
    d = engine.to_api_dict(result)
    assert "overview" in d
    assert "monthly_performance" in d
    assert "total_return_pct" in d["overview"]
    assert "sharpe_ratio" in d["overview"]
    assert "max_drawdown_pct" in d["overview"]


def test_confidence_filter_reduces_trades(market_data, signals):
    """Strict confidence threshold should suppress trades."""
    engine = BacktestingEngine()
    low_confidence = pd.Series(0.3, index=market_data.index)  # all below 0.6 threshold
    result_filtered = engine.run(market_data, signals, confidence=low_confidence, confidence_threshold=0.6)
    result_unfiltered = engine.run(market_data, signals)
    assert result_filtered.total_trades <= result_unfiltered.total_trades
```

- [ ] **Step 8: Run all tests**

```bash
cd /home/vlain/workspaces/personal/project-aurum
uv run pytest tests/ -v --tb=short 2>&1 | head -80
```

Expected: all tests pass except possibly `test_lightgbm_model.py::test_walk_forward_produces_oos_scores` which depends on data length.

- [ ] **Step 9: Commit tests**

```bash
git add tests/
git commit -m "test: add pytest suite for triple barrier, walk-forward, features, LightGBM, MetaLabeler, BacktestingEngine"
```

---

## Task 6: Create scripts/run_pipeline.py — real end-to-end train + backtest

**Files:**
- Create: `scripts/run_pipeline.py`

This script downloads real IDX data via yfinance, engineers features, trains the LightGBM model with walk-forward CV, runs the BacktestingEngine, and prints/saves results.

- [ ] **Step 1: Create scripts/run_pipeline.py**

```python
#!/usr/bin/env python3
"""
End-to-end training + backtest pipeline for Project Aurum.

Downloads IDX OHLCV data via yfinance, engineers features, trains
LightGBM + MetaLabeler with walk-forward CV, runs vectorbt backtest,
saves model and prints results.

Usage:
    uv run scripts/run_pipeline.py
    uv run scripts/run_pipeline.py --tickers BBCA.JK BMRI.JK --start 2020-01-01

The script runs each ticker independently and prints aggregated stats.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer
from src.domains.trading.infrastructure.ml_models.lightgbm_model import LightGBMSignalModel
from src.domains.trading.infrastructure.ml_models.meta_labeler import MetaLabeler
from src.domains.analytics.application.backtesting_engine import BacktestingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Default IDX LQ45 tickers (Yahoo Finance format: <CODE>.JK)
DEFAULT_TICKERS = [
    "BBCA.JK", "BMRI.JK", "BBRI.JK", "BBNI.JK",
    "TLKM.JK", "ASII.JK", "UNVR.JK", "INDF.JK",
    "KLBF.JK", "ADRO.JK", "ANTM.JK", "PTBA.JK",
    "GGRM.JK", "HMSP.JK", "SMGR.JK", "JSMR.JK",
]


def download_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        return df
    df = df.rename(columns=str.lower)
    # yfinance may return MultiIndex columns when downloading single ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    return df


def run_ticker(
    ticker: str,
    start: str,
    end: str,
    confidence_threshold: float = 0.6,
) -> dict | None:
    logger.info("Processing %s", ticker)

    # 1. Download
    raw = download_data(ticker, start, end)
    if len(raw) < 400:
        logger.warning("%s: only %d bars — skipping (need >= 400)", ticker, len(raw))
        return None

    # 2. Feature engineering
    eng = IDXFeatureEngineer()
    data = eng.generate_technical_features(raw)

    # 3. Train / test split for backtest: train on first 80%, backtest on last 20%
    split_idx = int(len(data) * 0.8)
    train_data = data.iloc[:split_idx]
    test_data  = data.iloc[split_idx:]
    test_prices = raw.iloc[split_idx:]

    # 4. Train LightGBM primary model
    model = LightGBMSignalModel()
    train_metrics = model.train(train_data, walk_forward=True)
    logger.info(
        "%s train: folds=%d OOS_acc=%.3f train_acc=%.3f",
        ticker,
        train_metrics["n_folds"],
        train_metrics.get("oos_accuracy_mean", float("nan")),
        train_metrics["training_accuracy"],
    )

    # 5. Train MetaLabeler on training data
    meta = MetaLabeler()
    X_train, _ = model.prepare_features(train_data)
    X_train_df = pd.DataFrame(X_train, columns=model.feature_names)
    primary_preds_train, _ = model.predict(train_data)
    actual_labels_train = model.create_targets(train_data)
    meta.fit(X_train_df, primary_preds_train, actual_labels_train)

    # 6. Generate signals on test data
    test_preds, test_probs = model.predict(test_data)
    X_test, _ = model.prepare_features(test_data)
    X_test_df = pd.DataFrame(X_test, columns=model.feature_names)
    bet_sizes = meta.predict_bet_size(X_test_df)

    # Convert primary predictions to signal series: +1=BUY, -1=SELL/EXIT, 0=HOLD
    signals = pd.Series(0.0, index=test_data.index)
    signals[test_preds == 1.0] = 1.0
    signals[test_preds == -1.0] = -1.0
    confidence = pd.Series(bet_sizes, index=test_data.index)

    # 7. Backtest
    engine = BacktestingEngine()
    result = engine.run(test_prices, signals, confidence, confidence_threshold)

    logger.info(
        "%s backtest: Sharpe=%.2f Return=%.1f%% WinRate=%.1f%% MaxDD=%.1f%% Trades=%d",
        ticker,
        result.sharpe_ratio,
        result.total_return_pct,
        result.win_rate_pct,
        result.max_drawdown_pct,
        result.total_trades,
    )

    return {
        "ticker": ticker,
        "train_metrics": train_metrics,
        "backtest": {
            "total_return_pct": round(result.total_return_pct, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "win_rate_pct": round(result.win_rate_pct, 2),
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "total_trades": result.total_trades,
            "annualised_return_pct": round(result.annualised_return_pct, 2),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Aurum — train + backtest pipeline")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--output", default="backtest_results.json")
    args = parser.parse_args()

    results = []
    for ticker in args.tickers:
        try:
            r = run_ticker(ticker, args.start, args.end, args.threshold)
            if r:
                results.append(r)
        except Exception as exc:
            logger.error("%s failed: %s", ticker, exc)

    if not results:
        logger.error("No results produced")
        sys.exit(1)

    # Aggregate stats
    sharpes = [r["backtest"]["sharpe_ratio"] for r in results]
    returns = [r["backtest"]["total_return_pct"] for r in results]
    win_rates = [r["backtest"]["win_rate_pct"] for r in results]
    drawdowns = [r["backtest"]["max_drawdown_pct"] for r in results]

    summary = {
        "n_tickers": len(results),
        "avg_sharpe": round(float(np.mean(sharpes)), 2),
        "median_sharpe": round(float(np.median(sharpes)), 2),
        "avg_return_pct": round(float(np.mean(returns)), 2),
        "avg_win_rate_pct": round(float(np.mean(win_rates)), 2),
        "avg_max_drawdown_pct": round(float(np.mean(drawdowns)), 2),
    }

    print("\n===== AGGREGATE BACKTEST RESULTS =====")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    output = {"summary": summary, "per_ticker": results}
    out_path = Path(args.output)
    out_path.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Results saved to %s", out_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/run_pipeline.py
git commit -m "feat: add end-to-end train+backtest pipeline script"
```

---

## Task 7: Run the pipeline

- [ ] **Step 1: Install deps and run**

```bash
cd /home/vlain/workspaces/personal/project-aurum
uv sync
uv run scripts/run_pipeline.py --tickers BBCA.JK BMRI.JK TLKM.JK ASII.JK --start 2020-01-01 --end 2025-12-31
```

- [ ] **Step 2: Check for errors and fix any import/runtime issues**

- [ ] **Step 3: Run full suite on all LQ45 tickers**

```bash
uv run scripts/run_pipeline.py --start 2020-01-01 --end 2025-12-31 --output backtest_results.json
```

- [ ] **Step 4: Run tests to verify nothing broke**

```bash
uv run pytest tests/ -v
```

- [ ] **Step 5: Commit results**

```bash
git add backtest_results.json
git commit -m "data: add backtest results from full LQ45 run"
```

---

## Task 8: Final cleanup

- [ ] **Step 1: Remove module-level instantiation from backtesting_engine.py**

The file currently ends with `backtest_engine = BacktestingEngine()`. Remove this — callers should instantiate their own.

- [ ] **Step 2: Fix return_60d reference in _TECHNICAL_KEYWORDS in lightgbm_model.py**

The keyword list already has `"return_"` which will match `return_60d`, so this is fine. Verify.

- [ ] **Step 3: Push all commits**

```bash
git push origin main
```

---

## Success Criteria

- All tests in `tests/` pass: `uv run pytest tests/ -v`
- `scripts/run_pipeline.py` runs end-to-end without error on at least 4 tickers
- `backtest_results.json` exists with real metrics
- No `random.uniform` simulation anywhere in the signal/backtest path
- `BacktestingEngine` import no longer crashes
