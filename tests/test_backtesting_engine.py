"""Tests for BacktestingEngine."""
import numpy as np
import pandas as pd
import pytest
from src.domains.analytics.application.backtesting_engine import BacktestingEngine, BacktestResult


@pytest.fixture
def market_data():
    np.random.seed(7)
    dates = pd.date_range("2022-01-01", periods=200, freq="B")
    close = 5000 * np.exp(np.cumsum(np.random.normal(0.0003, 0.015, 200)))
    return pd.DataFrame({
        "open": close * 0.999,
        "high": close * 1.01,
        "low":  close * 0.99,
        "close": close,
        "volume": np.random.lognormal(15, 0.5, 200),
    }, index=dates)


@pytest.fixture
def signals(market_data):
    sig = pd.Series(0.0, index=market_data.index)
    for i in range(0, len(sig) - 10, 20):
        sig.iloc[i] = 1.0
        sig.iloc[i + 10] = -1.0
    return sig


def test_run_returns_result(market_data, signals):
    result = BacktestingEngine().run(market_data, signals)
    assert isinstance(result, BacktestResult)


def test_equity_curve_populated(market_data, signals):
    result = BacktestingEngine().run(market_data, signals)
    assert len(result.equity_curve) > 0


def test_to_api_dict_keys(market_data, signals):
    engine = BacktestingEngine()
    d = engine.to_api_dict(engine.run(market_data, signals))
    assert "overview" in d
    assert "monthly_performance" in d
    for key in ["total_return_pct", "sharpe_ratio", "max_drawdown_pct", "win_rate_pct", "total_trades"]:
        assert key in d["overview"]


def test_confidence_filter_suppresses_trades(market_data, signals):
    engine = BacktestingEngine()
    low_conf = pd.Series(0.3, index=market_data.index)
    r_filtered = engine.run(market_data, signals, confidence=low_conf, confidence_threshold=0.6)
    r_unfiltered = engine.run(market_data, signals)
    assert r_filtered.total_trades <= r_unfiltered.total_trades


def test_max_drawdown_positive(market_data, signals):
    result = BacktestingEngine().run(market_data, signals)
    assert result.max_drawdown_pct >= 0.0
