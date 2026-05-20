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
        for v in labels.dropna().unique():
            assert v in {-1.0, 0.0, 1.0}, f"Unexpected label value: {v}"

    def test_uptrend_produces_positive_labels(self):
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

    def test_downtrend_produces_negative_labels(self):
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

    def test_last_bar_is_nan(self, prices, atr):
        """Last bar can't form a forward window → NaN."""
        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
        labels = labeler.label(prices, atr)
        assert pd.isna(labels.iloc[-1])
