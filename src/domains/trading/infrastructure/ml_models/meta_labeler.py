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
