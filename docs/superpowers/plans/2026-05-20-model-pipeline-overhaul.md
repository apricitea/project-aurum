# Model Pipeline Overhaul & Backtesting (Sub-Plan C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the naive sklearn ensemble with LightGBM + walk-forward validation + meta-labeler + vectorbt backtesting, producing auditable out-of-sample performance metrics for IDX swing trading signals.

**Architecture:** Four new modules are added alongside the existing `model_ensemble.py` (which is only lightly modified at the end): `walk_forward.py` provides rolling train/test fold generation with embargo; `lightgbm_model.py` is a drop-in replacement for `TechnicalSignalModel`; `meta_labeler.py` trains a secondary LightGBM to predict whether the primary signal will be correct; `backtest_engine.py` wraps vectorbt with IDX-specific transaction costs. The existing `EnsembleMetaModel`, `FundamentalValueModel`, and `SentimentMomentumModel` are untouched.

**Tech Stack:** LightGBM 4+, SHAP 0.44+, vectorbt 0.26+, scikit-learn (existing), pandas, numpy

---

## File Map

| Status | Path | Responsibility |
|---|---|---|
| Create | `src/domains/trading/infrastructure/ml_models/walk_forward.py` | Rolling fold generation with purging + embargo |
| Create | `src/domains/trading/infrastructure/ml_models/lightgbm_model.py` | LightGBM signal model (drop-in for TechnicalSignalModel) |
| Create | `src/domains/trading/infrastructure/ml_models/meta_labeler.py` | Secondary LightGBM predicting signal reliability |
| Create | `src/domains/trading/infrastructure/backtesting/__init__.py` | Package init |
| Create | `src/domains/trading/infrastructure/backtesting/backtest_engine.py` | vectorbt wrapper with IDX costs |
| Modify | `pyproject.toml` | Add lightgbm, shap, vectorbt |
| Modify | `src/domains/trading/infrastructure/ml_models/model_ensemble.py` | Wire LightGBMSignalModel as primary technical model |
| Create | `tests/test_walk_forward_validator.py` | WalkForwardValidator tests |
| Create | `tests/test_lightgbm_model.py` | LightGBMSignalModel tests |
| Create | `tests/test_meta_labeler.py` | MetaLabeler tests |
| Create | `tests/test_backtest_engine.py` | BacktestEngine tests |

---

## Task 1: Install Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependencies**

```bash
cd /home/vlain/workspaces/personal/project-aurum
uv add "lightgbm>=4.0" "shap>=0.44" "vectorbt>=0.26"
```

Expected: uv resolves and installs all three packages without conflict.

- [ ] **Step 2: Verify imports work**

```bash
uv run python -c "import lightgbm; import shap; import vectorbt; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add lightgbm, shap, vectorbt dependencies [nyx-auto]"
```

---

## Task 2: WalkForwardValidator

**Files:**
- Create: `src/domains/trading/infrastructure/ml_models/walk_forward.py`
- Create: `tests/test_walk_forward_validator.py`

Background: standard `TimeSeriesSplit` has no embargo gap between train and test. Consecutive observations are autocorrelated, so samples within 5 days of the train/test boundary leak information. The embargo forces a minimum gap.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_walk_forward_validator.py`:

```python
"""Tests for WalkForwardValidator."""
from __future__ import annotations

import pandas as pd
import pytest

from src.domains.trading.infrastructure.ml_models.walk_forward import (
    WalkForwardValidator,
    WalkForwardFold,
)


@pytest.fixture
def daily_index():
    """3-year business-day index — enough for several folds."""
    return pd.date_range("2022-01-03", periods=756, freq="B")


class TestWalkForwardFolds:
    def test_returns_at_least_one_fold(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        folds = wfv.get_folds(daily_index)
        assert len(folds) >= 1

    def test_fold_is_dataclass(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        folds = wfv.get_folds(daily_index)
        fold = folds[0]
        assert hasattr(fold, "train_start")
        assert hasattr(fold, "train_end")
        assert hasattr(fold, "test_start")
        assert hasattr(fold, "test_end")
        assert hasattr(fold, "fold_id")

    def test_train_comes_before_test(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        for fold in wfv.get_folds(daily_index):
            assert fold.train_end < fold.test_start

    def test_embargo_gap_respected(self, daily_index):
        embargo = 5
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=embargo)
        for fold in wfv.get_folds(daily_index):
            gap_days = (fold.test_start - fold.train_end).days
            assert gap_days >= embargo

    def test_folds_are_non_overlapping_in_test(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        folds = wfv.get_folds(daily_index)
        for i in range(1, len(folds)):
            assert folds[i].test_start > folds[i - 1].test_end

    def test_train_size_approximately_correct(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        folds = wfv.get_folds(daily_index)
        fold = folds[0]
        train_slice = daily_index[
            (daily_index >= fold.train_start) & (daily_index <= fold.train_end)
        ]
        assert 240 <= len(train_slice) <= 270  # allow for calendar variation
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_walk_forward_validator.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement WalkForwardValidator**

Create `src/domains/trading/infrastructure/ml_models/walk_forward.py`:

```python
"""
Walk-Forward Validator with embargo for time-series model evaluation.

Methodology: López de Prado "Advances in Financial Machine Learning" Ch. 7.
  - Rolling training window (fixed size)
  - Non-overlapping test windows
  - Embargo gap between train end and test start to prevent leakage
    from autocorrelated observations
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class WalkForwardFold:
    fold_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


class WalkForwardValidator:
    """
    Generates rolling train/test folds with an embargo gap.

    Parameters
    ----------
    train_days : int
        Number of calendar days in each training window (default 252 ≈ 1 year).
    test_days : int
        Number of calendar days in each test window (default 63 ≈ 1 quarter).
    embargo_days : int
        Minimum calendar-day gap between train_end and test_start (default 5).
    """

    def __init__(
        self,
        train_days: int = 252,
        test_days: int = 63,
        embargo_days: int = 5,
    ) -> None:
        self.train_days = train_days
        self.test_days = test_days
        self.embargo_days = embargo_days

    def get_folds(self, index: pd.DatetimeIndex) -> List[WalkForwardFold]:
        """
        Generate walk-forward folds for the given date index.

        Returns an empty list if the index is too short for even one fold.
        """
        index = index.sort_values()
        total_days = (index[-1] - index[0]).days
        min_required = self.train_days + self.embargo_days + self.test_days
        if total_days < min_required:
            return []

        folds: List[WalkForwardFold] = []
        fold_id = 0
        train_start = index[0]

        while True:
            train_end_target = train_start + pd.Timedelta(days=self.train_days)
            # Find the last index date on or before the target
            train_mask = index <= train_end_target
            if not train_mask.any():
                break
            train_end = index[train_mask][-1]

            test_start_target = train_end + pd.Timedelta(days=self.embargo_days + 1)
            test_mask = index >= test_start_target
            if not test_mask.any():
                break
            test_start = index[test_mask][0]

            test_end_target = test_start + pd.Timedelta(days=self.test_days)
            test_slice_mask = (index >= test_start) & (index <= test_end_target)
            if not test_slice_mask.any():
                break
            test_end = index[test_slice_mask][-1]

            folds.append(
                WalkForwardFold(
                    fold_id=fold_id,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                )
            )
            fold_id += 1
            # Advance train window to start at next test_end
            next_start_mask = index > test_end
            if not next_start_mask.any():
                break
            train_start = index[next_start_mask][0]

        return folds
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_walk_forward_validator.py -v
```

Expected: 6 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/walk_forward.py \
        tests/test_walk_forward_validator.py
git commit -m "feat: add WalkForwardValidator with embargo [nyx-auto]"
```

---

## Task 3: LightGBMSignalModel

**Files:**
- Create: `src/domains/trading/infrastructure/ml_models/lightgbm_model.py`
- Create: `tests/test_lightgbm_model.py`

This is a drop-in replacement for `TechnicalSignalModel` with the same `prepare_features` / `train` / `predict` interface. It adds walk-forward CV and SHAP feature importance.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_lightgbm_model.py`:

```python
"""Tests for LightGBMSignalModel."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.domains.trading.infrastructure.ml_models.lightgbm_model import LightGBMSignalModel


@pytest.fixture
def price_df():
    """200-bar synthetic OHLCV + basic technical features."""
    n = 200
    idx = pd.date_range("2024-01-02", periods=n, freq="B")
    close = pd.Series(
        [10000.0 * (1 + 0.003 * i + 0.002 * (i % 7 - 3)) for i in range(n)],
        index=idx,
    )
    df = pd.DataFrame(index=idx)
    df["close"] = close
    df["open"] = close * 0.999
    df["high"] = close * 1.004
    df["low"] = close * 0.996
    df["volume"] = 1_000_000
    # minimal technical cols so prepare_features() has something to select
    df["return_1d"] = df["close"].pct_change()
    df["return_5d"] = df["close"].pct_change(5)
    df["rsi_14"] = 50.0  # constant placeholder
    df["atr"] = 100.0
    df["macd"] = 0.0
    df["volume_ratio"] = 1.0
    return df


class TestLightGBMSignalModel:
    def test_train_returns_metrics_dict(self, price_df):
        model = LightGBMSignalModel()
        metrics = model.train(price_df)
        assert isinstance(metrics, dict)
        assert "n_folds" in metrics
        assert "oos_accuracy_mean" in metrics

    def test_model_is_trained_after_train(self, price_df):
        model = LightGBMSignalModel()
        model.train(price_df)
        assert model.is_trained

    def test_predict_returns_labels_and_probs(self, price_df):
        model = LightGBMSignalModel()
        model.train(price_df)
        labels, probs = model.predict(price_df)
        assert labels.shape[0] == len(price_df)
        assert probs.ndim == 2

    def test_predict_labels_in_valid_set(self, price_df):
        model = LightGBMSignalModel()
        model.train(price_df)
        labels, _ = model.predict(price_df)
        unique = set(labels)
        assert unique.issubset({-1.0, 0.0, 1.0})

    def test_feature_importance_set_after_train(self, price_df):
        model = LightGBMSignalModel()
        model.train(price_df)
        assert model.feature_importance is not None
        assert "feature" in model.feature_importance.columns
        assert "importance" in model.feature_importance.columns

    def test_predict_raises_before_train(self, price_df):
        model = LightGBMSignalModel()
        with pytest.raises(ValueError, match="trained"):
            model.predict(price_df)
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_lightgbm_model.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Implement LightGBMSignalModel**

Create `src/domains/trading/infrastructure/ml_models/lightgbm_model.py`:

```python
"""
LightGBM-based signal model for IDX technical features.

Replaces TechnicalSignalModel (RandomForest) with:
  - LightGBM classifier (faster, often better on tabular data)
  - Walk-forward OOS accuracy rather than naive TimeSeriesSplit
  - SHAP feature importance via TreeExplainer

Interface is intentionally identical to TechnicalSignalModel so model_ensemble.py
can swap it in with a one-line change.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.preprocessing import RobustScaler

from src.domains.market_data.application.triple_barrier import TripleBarrierLabeler
from .walk_forward import WalkForwardValidator

logger = logging.getLogger(__name__)

# Feature column keywords — matches TechnicalSignalModel.prepare_features()
_TECHNICAL_KEYWORDS = [
    "return_", "ma_", "price_to_ma", "momentum_", "rsi_", "macd",
    "stoch_", "williams_r", "bb_", "volume_", "vwap", "obv",
    "atr", "adx", "gap",
    # Sub-Plan B additions
    "vol_5d", "vol_10d", "vol_20d", "vol_60d",
    "market_regime", "trend_strength",
    "usdidr_", "gold_", "btc_", "stock_btc_corr", "stock_gold_corr",
]


class LightGBMSignalModel:
    """
    LightGBM classifier for directional signals on IDX stocks.

    Labels come from TripleBarrierLabeler: +1.0 (PT hit), -1.0 (SL hit), 0.0 (time exit).
    Training uses walk-forward CV (252d train / 63d test / 5d embargo).
    Feature importance uses SHAP TreeExplainer.
    """

    def __init__(self, config: Optional[Dict] = None) -> None:
        self.config = config or {
            "n_estimators": 500,
            "learning_rate": 0.05,
            "max_depth": 6,
            "num_leaves": 63,
            "min_child_samples": 20,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }
        self.model = lgb.LGBMClassifier(**self.config)
        self.scaler = RobustScaler()
        self.feature_importance: Optional[pd.DataFrame] = None
        self.feature_names: List[str] = []
        self.classes_: Optional[np.ndarray] = None
        self.is_trained: bool = False

    # ------------------------------------------------------------------ #
    # Public interface (mirrors TechnicalSignalModel)
    # ------------------------------------------------------------------ #

    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        cols = [
            col for col in data.columns
            if any(kw in col for kw in _TECHNICAL_KEYWORDS)
        ]
        if not cols:
            raise ValueError(
                "No technical feature columns found in DataFrame. "
                "Run IDXFeatureEngineer.generate_technical_features() first."
            )
        X = data[cols].fillna(0.0)
        return X.values, cols

    def create_targets(self, data: pd.DataFrame, horizon: int = 5) -> np.ndarray:
        if "atr" not in data.columns or data["atr"].isna().all():
            fwd = data["close"].pct_change(horizon).shift(-horizon)
            return np.where(fwd > 0, 1.0, -1.0)
        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=horizon * 2)
        return labeler.label(data["close"], data["atr"]).values

    def train(
        self,
        data: pd.DataFrame,
        target_horizon: int = 5,
        walk_forward: bool = True,
    ) -> Dict:
        """
        Train the model and return performance metrics.

        If walk_forward=True (default), runs walk-forward CV and reports
        OOS accuracy per fold. Always trains a final model on the full dataset.

        Returns
        -------
        dict with keys:
          n_folds, oos_accuracy_mean, oos_accuracy_std,
          training_accuracy, n_features, n_samples
        """
        X_all, self.feature_names = self.prepare_features(data)
        y_all = self.create_targets(data, target_horizon)

        mask = ~pd.isna(y_all)
        X_all, y_all = X_all[mask], y_all[mask]
        valid_index = data.index[mask]

        X_scaled_all = self.scaler.fit_transform(X_all)

        oos_scores: List[float] = []

        if walk_forward:
            wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
            folds = wfv.get_folds(valid_index)

            for fold in folds:
                train_mask = (valid_index >= fold.train_start) & (valid_index <= fold.train_end)
                test_mask = (valid_index >= fold.test_start) & (valid_index <= fold.test_end)
                if train_mask.sum() < 20 or test_mask.sum() < 5:
                    continue

                X_tr, y_tr = X_scaled_all[train_mask], y_all[train_mask]
                X_te, y_te = X_scaled_all[test_mask], y_all[test_mask]

                fold_model = lgb.LGBMClassifier(**self.config)
                fold_model.fit(
                    X_tr, y_tr,
                    eval_set=[(X_te, y_te)],
                    callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(-1)],
                )
                oos_scores.append(fold_model.score(X_te, y_te))
                logger.debug("Fold %s OOS accuracy: %.4f", fold.fold_id, oos_scores[-1])

        # Final model on all data
        self.model.fit(X_scaled_all, y_all)
        self.classes_ = self.model.classes_
        self.is_trained = True

        self._compute_shap_importance(X_scaled_all)

        return {
            "n_folds": len(oos_scores),
            "oos_accuracy_mean": float(np.mean(oos_scores)) if oos_scores else float("nan"),
            "oos_accuracy_std": float(np.std(oos_scores)) if oos_scores else float("nan"),
            "training_accuracy": float(self.model.score(X_scaled_all, y_all)),
            "n_features": len(self.feature_names),
            "n_samples": int(mask.sum()),
        }

    def predict(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        X, _ = self.prepare_features(data)
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        return predictions, probabilities

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _compute_shap_importance(self, X_scaled: np.ndarray) -> None:
        try:
            explainer = shap.TreeExplainer(self.model)
            # Use a sample to keep it fast (max 500 rows)
            sample = X_scaled[:500] if len(X_scaled) > 500 else X_scaled
            shap_values = explainer.shap_values(sample)
            # shap_values is a list (one array per class) or a single array
            if isinstance(shap_values, list):
                mean_abs = np.abs(np.array(shap_values)).mean(axis=0).mean(axis=0)
            else:
                mean_abs = np.abs(shap_values).mean(axis=0)
            self.feature_importance = pd.DataFrame(
                {"feature": self.feature_names, "importance": mean_abs}
            ).sort_values("importance", ascending=False)
        except Exception as exc:
            logger.warning("SHAP computation failed (%s), using LightGBM gain instead", exc)
            self.feature_importance = pd.DataFrame(
                {
                    "feature": self.feature_names,
                    "importance": self.model.feature_importances_,
                }
            ).sort_values("importance", ascending=False)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_lightgbm_model.py -v
```

Expected: 6 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/lightgbm_model.py \
        tests/test_lightgbm_model.py
git commit -m "feat: add LightGBMSignalModel with walk-forward CV and SHAP [nyx-auto]"
```

---

## Task 4: MetaLabeler

**Files:**
- Create: `src/domains/trading/infrastructure/ml_models/meta_labeler.py`
- Create: `tests/test_meta_labeler.py`

Background: The meta-labeler is a secondary classifier trained to predict "will the primary signal be correct on this bar?" (López de Prado, AFML Ch. 10). At inference it outputs a bet-size scalar (0–1). We only take positions above a confidence threshold.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_meta_labeler.py`:

```python
"""Tests for MetaLabeler."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.domains.trading.infrastructure.ml_models.meta_labeler import MetaLabeler


@pytest.fixture
def synthetic_data():
    """200-bar features + primary labels + actual labels."""
    n = 200
    rng = np.random.default_rng(42)
    X = pd.DataFrame(
        rng.standard_normal((n, 5)),
        columns=["f0", "f1", "f2", "f3", "f4"],
        index=pd.date_range("2024-01-02", periods=n, freq="B"),
    )
    primary = np.where(rng.random(n) > 0.5, 1.0, -1.0)
    # actual labels agree with primary ~65% of the time
    actual = np.where(rng.random(n) > 0.35, primary, -primary)
    return X, primary, actual


class TestMetaLabeler:
    def test_fit_trains_model(self, synthetic_data):
        X, primary, actual = synthetic_data
        ml = MetaLabeler()
        ml.fit(X, primary, actual)
        assert ml.is_trained

    def test_predict_proba_shape(self, synthetic_data):
        X, primary, actual = synthetic_data
        ml = MetaLabeler()
        ml.fit(X, primary, actual)
        bet_sizes = ml.predict_bet_size(X)
        assert bet_sizes.shape == (len(X),)

    def test_predict_proba_range(self, synthetic_data):
        X, primary, actual = synthetic_data
        ml = MetaLabeler()
        ml.fit(X, primary, actual)
        bet_sizes = ml.predict_bet_size(X)
        assert (bet_sizes >= 0.0).all()
        assert (bet_sizes <= 1.0).all()

    def test_predict_raises_before_fit(self, synthetic_data):
        X, _, _ = synthetic_data
        ml = MetaLabeler()
        with pytest.raises(ValueError, match="trained"):
            ml.predict_bet_size(X)

    def test_fit_returns_metrics(self, synthetic_data):
        X, primary, actual = synthetic_data
        ml = MetaLabeler()
        metrics = ml.fit(X, primary, actual)
        assert "training_accuracy" in metrics
        assert "positive_rate" in metrics
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_meta_labeler.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Implement MetaLabeler**

Create `src/domains/trading/infrastructure/ml_models/meta_labeler.py`:

```python
"""
Meta-Labeler: secondary LightGBM that predicts whether the primary signal is correct.

Usage pattern:
  1. Train primary model and collect OOS predictions on a holdout set.
  2. Build binary labels: meta_y[i] = 1 if primary_pred[i] == actual_label[i] else 0.
  3. Train MetaLabeler on the same features used by the primary model.
  4. At inference: multiply position size by meta_labeler.predict_bet_size(X).
  5. Skip positions with bet_size < threshold (e.g. 0.6).

This prevents signal generation in noisy market conditions.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

logger = logging.getLogger(__name__)


class MetaLabeler:
    """
    Secondary LightGBM classifier predicting signal reliability.

    Parameters
    ----------
    config : dict, optional
        LightGBM hyperparameters. Defaults to a lightweight config
        (fewer estimators than primary model — meta-task is simpler).
    """

    def __init__(self, config: Optional[Dict] = None) -> None:
        self.config = config or {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 4,
            "num_leaves": 31,
            "min_child_samples": 10,
            "subsample": 0.8,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }
        self.model = lgb.LGBMClassifier(**self.config)
        self.scaler = RobustScaler()
        self.is_trained: bool = False

    def fit(
        self,
        X: pd.DataFrame,
        primary_labels: np.ndarray,
        actual_labels: np.ndarray,
    ) -> Dict:
        """
        Train the meta-labeler.

        Parameters
        ----------
        X : DataFrame
            Feature matrix (same features as primary model).
        primary_labels : array of float
            Predictions from the primary model (+1.0, -1.0, 0.0).
        actual_labels : array of float
            Ground-truth triple-barrier labels (+1.0, -1.0, 0.0).

        Returns
        -------
        dict with training_accuracy and positive_rate.
        """
        meta_y = (primary_labels == actual_labels).astype(int)
        mask = ~pd.isna(actual_labels) & ~pd.isna(primary_labels)
        X_vals = X.values[mask] if isinstance(X, pd.DataFrame) else X[mask]
        meta_y = meta_y[mask]

        X_scaled = self.scaler.fit_transform(X_vals)
        self.model.fit(X_scaled, meta_y)
        self.is_trained = True

        return {
            "training_accuracy": float(self.model.score(X_scaled, meta_y)),
            "positive_rate": float(meta_y.mean()),
        }

    def predict_bet_size(self, X: pd.DataFrame) -> np.ndarray:
        """
        Return bet-size scalars in [0, 1] for each row.

        This is P(primary signal is correct | features), i.e. the probability
        of the positive class from the meta-labeler. Use as a multiplicative
        filter: skip positions where bet_size < threshold.
        """
        if not self.is_trained:
            raise ValueError("MetaLabeler must be trained before prediction")
        X_vals = X.values if isinstance(X, pd.DataFrame) else X
        X_scaled = self.scaler.transform(X_vals)
        proba = self.model.predict_proba(X_scaled)
        # Column 1 = P(correct)
        return proba[:, 1]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_meta_labeler.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/meta_labeler.py \
        tests/test_meta_labeler.py
git commit -m "feat: add MetaLabeler (secondary signal reliability filter) [nyx-auto]"
```

---

## Task 5: BacktestEngine

**Files:**
- Create: `src/domains/trading/infrastructure/backtesting/__init__.py`
- Create: `src/domains/trading/infrastructure/backtesting/backtest_engine.py`
- Create: `tests/test_backtest_engine.py`

IDX transaction costs:
- Buy commission: ~0.15% (varies by broker, 0.15% is common)
- Sell commission: ~0.25% (includes 0.1% VAT portion)
- Slippage: 0.1–0.2% for liquid stocks

vectorbt `Portfolio.from_signals` accepts `fees` as a scalar applied to each trade. We set it to the one-way average (0.002) — this slightly underestimates total round-trip cost but is reasonable for single-direction fee tracking.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_backtest_engine.py`:

```python
"""Tests for BacktestEngine."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.domains.trading.infrastructure.backtesting.backtest_engine import BacktestEngine


@pytest.fixture
def prices():
    """100-bar synthetic close prices for 2 stocks."""
    idx = pd.date_range("2025-01-02", periods=100, freq="B")
    return pd.DataFrame(
        {
            "BBCA": [10000.0 + i * 20 for i in range(100)],
            "TLKM": [4000.0 + i * 5 for i in range(100)],
        },
        index=idx,
    )


@pytest.fixture
def signals(prices):
    """Simple alternating buy/sell signals."""
    sig = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    sig.iloc[5:10] = 1.0   # buy
    sig.iloc[10:15] = -1.0  # sell
    sig.iloc[20:25] = 1.0
    sig.iloc[25:30] = -1.0
    return sig


class TestBacktestEngine:
    def test_run_returns_dict(self, prices, signals):
        engine = BacktestEngine()
        result = engine.run(prices, signals)
        assert isinstance(result, dict)

    def test_result_has_required_keys(self, prices, signals):
        engine = BacktestEngine()
        result = engine.run(prices, signals)
        required = {"total_return", "sharpe_ratio", "max_drawdown", "win_rate", "profit_factor", "n_trades"}
        assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"

    def test_no_trades_when_all_signals_zero(self, prices):
        signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        engine = BacktestEngine()
        result = engine.run(prices, signals)
        assert result["n_trades"] == 0

    def test_meta_filter_reduces_trades(self, prices, signals):
        """High meta threshold → fewer or equal trades than no filter."""
        engine = BacktestEngine()
        result_no_filter = engine.run(prices, signals)
        # meta_probs all 0.3 → below default threshold of 0.6 → no trades
        meta_probs = pd.DataFrame(0.3, index=prices.index, columns=prices.columns)
        result_filtered = engine.run(prices, signals, meta_probs=meta_probs, min_meta_prob=0.6)
        assert result_filtered["n_trades"] <= result_no_filter["n_trades"]

    def test_max_drawdown_is_non_positive(self, prices, signals):
        engine = BacktestEngine()
        result = engine.run(prices, signals)
        assert result["max_drawdown"] <= 0.0
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_backtest_engine.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Create package init**

Create `src/domains/trading/infrastructure/backtesting/__init__.py`:

```python
"""Backtesting engine for IDX trading signals."""
```

- [ ] **Step 4: Implement BacktestEngine**

Create `src/domains/trading/infrastructure/backtesting/backtest_engine.py`:

```python
"""
Backtesting engine for IDX swing trading signals using vectorbt.

Transaction costs (realistic for Indonesian retail brokerage):
  buy_fee:   0.15% (commission to broker)
  sell_fee:  0.25% (commission + 0.1% government levy)
  slippage:  0.20% per trade (market impact for liquid IDX stocks)

Note: vectorbt Portfolio.from_signals applies `fees` to each trade's value.
We use the average one-way cost (0.002) so fees are applied correctly on
both entry and exit legs.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd
import vectorbt as vbt

logger = logging.getLogger(__name__)

# IDX realistic costs
_BUY_FEE = 0.0015
_SELL_FEE = 0.0025
_SLIPPAGE = 0.002


class BacktestEngine:
    """
    Runs vectorbt backtests with IDX-appropriate transaction costs.

    Parameters
    ----------
    buy_fee : float
        Buy-side commission fraction (default 0.0015 = 0.15%).
    sell_fee : float
        Sell-side commission fraction (default 0.0025 = 0.25%).
    slippage : float
        One-way slippage fraction (default 0.002 = 0.2%).
    init_cash : float
        Starting portfolio value in IDR (default 100_000_000 = 100M IDR).
    """

    def __init__(
        self,
        buy_fee: float = _BUY_FEE,
        sell_fee: float = _SELL_FEE,
        slippage: float = _SLIPPAGE,
        init_cash: float = 100_000_000.0,
    ) -> None:
        self.buy_fee = buy_fee
        self.sell_fee = sell_fee
        self.slippage = slippage
        self.init_cash = init_cash

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        meta_probs: Optional[pd.DataFrame] = None,
        min_meta_prob: float = 0.6,
    ) -> Dict:
        """
        Run a vectorised backtest.

        Parameters
        ----------
        prices : DataFrame
            Close prices indexed by date, one column per stock.
        signals : DataFrame
            Signal values: +1 = enter long, -1 = exit long, 0 = hold.
            Same index and columns as prices.
        meta_probs : DataFrame, optional
            MetaLabeler bet-size output (0–1 per bar per stock).
            If provided, entry signals where meta_prob < min_meta_prob are suppressed.
        min_meta_prob : float
            Minimum meta-probability to allow an entry (default 0.6).

        Returns
        -------
        dict with: total_return, sharpe_ratio, max_drawdown, win_rate,
                   profit_factor, n_trades, equity_curve (pd.Series)
        """
        entries = signals == 1.0
        exits = signals == -1.0

        # Apply meta-labeler filter to entries only
        if meta_probs is not None:
            entries = entries & (meta_probs >= min_meta_prob)

        n_entries = int(entries.values.sum())
        if n_entries == 0:
            return self._empty_result()

        # Average fee (applied to both sides by vectorbt)
        avg_fee = (self.buy_fee + self.sell_fee) / 2

        try:
            portfolio = vbt.Portfolio.from_signals(
                close=prices,
                entries=entries,
                exits=exits,
                fees=avg_fee,
                slippage=self.slippage,
                init_cash=self.init_cash,
                freq="1D",
            )
        except Exception as exc:
            logger.error("vectorbt portfolio construction failed: %s", exc)
            return self._empty_result()

        return self._extract_metrics(portfolio)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _extract_metrics(self, portfolio) -> Dict:
        try:
            stats = portfolio.stats()
            equity = portfolio.value()
            if isinstance(equity, pd.DataFrame):
                equity = equity.sum(axis=1)

            # Safely extract stats — key names differ between vectorbt versions
            def _get(key: str, default=float("nan")):
                if hasattr(stats, "get"):
                    return stats.get(key, default)
                if hasattr(stats, key):
                    return getattr(stats, key)
                return default

            total_return = float(_get("Total Return [%]", 0.0)) / 100
            sharpe = float(_get("Sharpe Ratio", float("nan")))
            max_dd = float(_get("Max Drawdown [%]", 0.0)) / -100
            n_trades = int(_get("Total Trades", 0))
            win_rate = float(_get("Win Rate [%]", float("nan"))) / 100

            # Profit factor: gross profit / gross loss
            profit_factor = float("nan")
            try:
                trades = portfolio.trades.records_readable
                if len(trades) > 0:
                    pos_pnl = trades.loc[trades["PnL"] > 0, "PnL"].sum()
                    neg_pnl = abs(trades.loc[trades["PnL"] < 0, "PnL"].sum())
                    profit_factor = pos_pnl / neg_pnl if neg_pnl > 0 else float("inf")
            except Exception:
                pass

            return {
                "total_return": total_return,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "n_trades": n_trades,
                "equity_curve": equity,
            }

        except Exception as exc:
            logger.error("Failed to extract backtest metrics: %s", exc)
            return self._empty_result()

    @staticmethod
    def _empty_result() -> Dict:
        return {
            "total_return": 0.0,
            "sharpe_ratio": float("nan"),
            "max_drawdown": 0.0,
            "win_rate": float("nan"),
            "profit_factor": float("nan"),
            "n_trades": 0,
            "equity_curve": pd.Series(dtype=float),
        }
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_backtest_engine.py -v
```

Expected: 5 tests PASSED. If `vectorbt` API differs slightly (e.g. stats key names), adjust `_get` lookups in `_extract_metrics`.

- [ ] **Step 6: Commit**

```bash
git add src/domains/trading/infrastructure/backtesting/ \
        tests/test_backtest_engine.py
git commit -m "feat: add BacktestEngine with IDX transaction costs (vectorbt) [nyx-auto]"
```

---

## Task 6: Wire LightGBMSignalModel into model_ensemble.py

**Files:**
- Modify: `src/domains/trading/infrastructure/ml_models/model_ensemble.py` (lines 1–21)

This is a minimal change — swap the import and the model instantiation in `IDXQuantitativeModel.__init__`. All other models (`FundamentalValueModel`, `SentimentMomentumModel`, `EnsembleMetaModel`) are unchanged.

- [ ] **Step 1: Read the current import block**

Lines 1–21 of `model_ensemble.py` currently import `RandomForestClassifier` etc. and reference `TechnicalSignalModel`.

- [ ] **Step 2: Update the import in model_ensemble.py**

In `model_ensemble.py`, add the import after line 20 (`from src.domains.market_data.application.triple_barrier import TripleBarrierLabeler`):

```python
from .lightgbm_model import LightGBMSignalModel
```

- [ ] **Step 3: Swap TechnicalSignalModel usage in IDXQuantitativeModel.__init__**

In `IDXQuantitativeModel.__init__` (line 582), change:

```python
# OLD
self.technical_model = TechnicalSignalModel(
    self.config.get('technical', {})
)
```

to:

```python
# NEW — LightGBM replaces RandomForest for the primary signal
self.technical_model = LightGBMSignalModel(
    self.config.get('technical', None)
)
```

- [ ] **Step 4: Run the full test suite**

```bash
uv run pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All previously passing tests still pass. The new model tests also pass.

- [ ] **Step 5: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/model_ensemble.py
git commit -m "feat: swap TechnicalSignalModel → LightGBMSignalModel in ensemble [nyx-auto]"
```

---

## Task 7: Full test suite + final verification

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v 2>&1 | tail -40
```

Expected: All tests pass. Count should be 122 (previous) + 6 + 6 + 5 + 5 = 144 tests.

- [ ] **Step 2: Smoke-test the model pipeline end-to-end**

```bash
uv run python -c "
import pandas as pd
import numpy as np

# Minimal synthetic data
n = 300
idx = pd.date_range('2023-01-02', periods=n, freq='B')
close = pd.Series([10000.0 + i*20 + np.random.randn()*100 for i in range(n)], index=idx)
df = pd.DataFrame({'close': close, 'open': close*0.999, 'high': close*1.004, 'low': close*0.996, 'volume': 1e6, 'return_1d': close.pct_change(), 'return_5d': close.pct_change(5), 'rsi_14': 50.0, 'atr': 100.0, 'macd': 0.0, 'volume_ratio': 1.0}, index=idx)

from src.domains.trading.infrastructure.ml_models.lightgbm_model import LightGBMSignalModel
model = LightGBMSignalModel()
metrics = model.train(df)
print('WF folds:', metrics['n_folds'], '| OOS acc:', round(metrics['oos_accuracy_mean'], 3))

labels, probs = model.predict(df)
signals = pd.DataFrame({'CLOSE': labels}, index=idx).astype(float)
prices = pd.DataFrame({'CLOSE': close}, index=idx)

from src.domains.trading.infrastructure.backtesting.backtest_engine import BacktestEngine
bt = BacktestEngine()
result = bt.run(prices, signals)
print('Backtest — trades:', result['n_trades'], '| Sharpe:', round(result['sharpe_ratio'], 2) if not pd.isna(result['sharpe_ratio']) else 'nan')
print('Done')
"
```

Expected: prints fold count, OOS accuracy, trade count, and Sharpe without error.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: sub-plan C complete — LightGBM + walk-forward + meta-labeler + backtesting [nyx-auto]"
```
