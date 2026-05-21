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
