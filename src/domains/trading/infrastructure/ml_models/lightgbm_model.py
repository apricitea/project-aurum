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
            # shap 0.44+ returns an Explanation object; older returns array/list
            raw = explainer(sample)
            if hasattr(raw, "values"):
                sv = raw.values  # Explanation object → ndarray (n_samples, n_features[, n_classes])
            else:
                sv = raw  # legacy: array or list of arrays

            sv_arr = np.array(sv)
            # Normalise shape to (n_samples, n_features) by averaging over classes
            if sv_arr.ndim == 3:
                sv_arr = sv_arr.mean(axis=-1)   # (n_samples, n_features, n_classes) → (n_samples, n_features)
            elif sv_arr.ndim == 2 and sv_arr.shape[1] != len(self.feature_names):
                # list-of-arrays case stacked as (n_classes, n_samples, n_features)
                sv_arr = np.abs(sv_arr).mean(axis=0)

            mean_abs = np.abs(sv_arr).mean(axis=0)
            if mean_abs.ndim > 1:
                mean_abs = mean_abs.mean(axis=-1)

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
