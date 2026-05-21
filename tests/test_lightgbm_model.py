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
