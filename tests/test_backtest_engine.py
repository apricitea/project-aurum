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
        """Low meta probs → fewer or equal trades than no filter."""
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
