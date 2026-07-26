"""Tests for LightGBMSignalModel."""
import numpy as np
import pandas as pd
import pytest
from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer
from src.domains.trading.infrastructure.ml_models.lightgbm_model import LightGBMSignalModel


@pytest.fixture(scope="module")
def feature_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    close = 5000 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 400)))
    raw = pd.DataFrame({
        "open":   close * np.random.uniform(0.99, 1.0, 400),
        "high":   close * np.random.uniform(1.0, 1.02, 400),
        "low":    close * np.random.uniform(0.98, 1.0, 400),
        "close":  close,
        "volume": np.random.lognormal(15, 0.5, 400),
    }, index=dates)
    return IDXFeatureEngineer().generate_technical_features(raw)


def test_train_returns_metrics(feature_data):
    model = LightGBMSignalModel()
    metrics = model.train(feature_data, walk_forward=False)
    assert "training_accuracy" in metrics
    assert 0.0 <= metrics["training_accuracy"] <= 1.0


def test_train_sets_is_trained(feature_data):
    model = LightGBMSignalModel()
    model.train(feature_data, walk_forward=False)
    assert model.is_trained


def test_predict_correct_shapes(feature_data):
    model = LightGBMSignalModel()
    model.train(feature_data, walk_forward=False)
    preds, probs = model.predict(feature_data)
    assert len(preds) == len(feature_data)
    assert probs.shape[0] == len(feature_data)


def test_predict_raises_before_train(feature_data):
    with pytest.raises(ValueError, match="must be trained"):
        LightGBMSignalModel().predict(feature_data)


def test_feature_importance_computed(feature_data):
    model = LightGBMSignalModel()
    model.train(feature_data, walk_forward=False)
    assert model.feature_importance is not None
    assert len(model.feature_importance) == len(model.feature_names)
