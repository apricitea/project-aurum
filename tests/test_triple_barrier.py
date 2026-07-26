"""Tests for TripleBarrierLabeler."""
import numpy as np
import pandas as pd
import pytest
from src.domains.market_data.application.triple_barrier import TripleBarrierLabeler


@pytest.fixture
def price_atr():
    dates = pd.date_range("2020-01-01", periods=100, freq="B")
    prices = pd.Series(100.0 + np.arange(100) * 0.5, index=dates)
    atr = pd.Series(2.0, index=dates)
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
    non_nan = labels.dropna()
    assert set(non_nan.unique()).issubset({-1.0, 0.0, 1.0})


def test_rising_prices_hit_profit_target(price_atr):
    prices, atr = price_atr
    labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
    labels = labeler.label(prices, atr)
    non_nan = labels.dropna()
    assert (non_nan == 1.0).mean() > 0.5


def test_nan_atr_produces_nan_label():
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    prices = pd.Series(100.0, index=dates)
    atr = pd.Series(np.nan, index=dates)
    labels = TripleBarrierLabeler().label(prices, atr)
    assert labels.isna().all()


def test_zero_atr_produces_nan_label():
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    prices = pd.Series(100.0, index=dates)
    atr = pd.Series(0.0, index=dates)
    labels = TripleBarrierLabeler().label(prices, atr)
    assert labels.isna().all()


def test_last_bar_is_nan(price_atr):
    prices, atr = price_atr
    labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=10)
    labels = labeler.label(prices, atr)
    assert np.isnan(labels.iloc[-1])
