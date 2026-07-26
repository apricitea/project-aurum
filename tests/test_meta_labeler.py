"""Tests for MetaLabeler."""
import numpy as np
import pandas as pd
import pytest
from src.domains.trading.infrastructure.ml_models.meta_labeler import MetaLabeler


@pytest.fixture
def training_data():
    np.random.seed(1)
    n = 200
    X = pd.DataFrame(np.random.randn(n, 10), columns=[f"f{i}" for i in range(10)])
    primary = np.random.choice([-1.0, 0.0, 1.0], size=n)
    actual = np.random.choice([-1.0, 0.0, 1.0], size=n)
    return X, primary, actual


def test_fit_returns_metrics(training_data):
    X, primary, actual = training_data
    ml = MetaLabeler()
    metrics = ml.fit(X, primary, actual)
    assert "training_accuracy" in metrics
    assert "positive_rate" in metrics


def test_fit_sets_is_trained(training_data):
    X, primary, actual = training_data
    ml = MetaLabeler()
    ml.fit(X, primary, actual)
    assert ml.is_trained


def test_predict_bet_size_in_range(training_data):
    X, primary, actual = training_data
    ml = MetaLabeler()
    ml.fit(X, primary, actual)
    bet = ml.predict_bet_size(X)
    assert ((bet >= 0.0) & (bet <= 1.0)).all()


def test_predict_raises_before_fit():
    ml = MetaLabeler()
    X = pd.DataFrame(np.random.randn(10, 5), columns=[f"f{i}" for i in range(5)])
    with pytest.raises(ValueError, match="must be trained"):
        ml.predict_bet_size(X)
