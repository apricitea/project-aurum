"""Tests for IDXFeatureEngineer."""
import numpy as np
import pandas as pd
import pytest
from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer


@pytest.fixture
def ohlcv():
    np.random.seed(0)
    dates = pd.date_range("2022-01-01", periods=120, freq="B")
    close = 5000 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 120)))
    return pd.DataFrame({
        "open":   close * np.random.uniform(0.99, 1.0, 120),
        "high":   close * np.random.uniform(1.0, 1.02, 120),
        "low":    close * np.random.uniform(0.98, 1.0, 120),
        "close":  close,
        "volume": np.random.lognormal(15, 0.5, 120),
    }, index=dates)


def test_returns_dataframe(ohlcv):
    result = IDXFeatureEngineer().generate_technical_features(ohlcv)
    assert isinstance(result, pd.DataFrame)


def test_return_columns_present(ohlcv):
    result = IDXFeatureEngineer().generate_technical_features(ohlcv)
    for p in [1, 3, 5, 10, 20, 60]:
        assert f"return_{p}d" in result.columns


def test_rsi_in_valid_range(ohlcv):
    result = IDXFeatureEngineer().generate_technical_features(ohlcv)
    rsi_cols = [c for c in result.columns if c.startswith("rsi_")]
    assert rsi_cols
    for col in rsi_cols:
        valid = result[col].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()


def test_atr_non_negative(ohlcv):
    result = IDXFeatureEngineer().generate_technical_features(ohlcv)
    assert "atr" in result.columns
    assert (result["atr"].dropna() >= 0).all()


def test_no_infinite_values(ohlcv):
    result = IDXFeatureEngineer().generate_technical_features(ohlcv)
    numeric = result.select_dtypes(include=[np.number])
    assert not np.isinf(numeric.values).any()


def test_cross_asset_columns_nan_without_data(ohlcv):
    result = IDXFeatureEngineer().generate_technical_features(ohlcv, cross_asset_df=None)
    cross_cols = [c for c in result.columns if any(kw in c for kw in ["gold_", "usdidr_", "btc_"])]
    for col in cross_cols:
        assert result[col].isna().all(), f"{col} should be NaN without cross-asset data"
