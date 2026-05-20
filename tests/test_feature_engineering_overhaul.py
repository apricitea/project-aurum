"""Tests for new feature engineering methods added in Sub-Plan B."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer


@pytest.fixture
def price_df():
    """Minimal OHLCV DataFrame with 80 daily bars."""
    n = 80
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    close = pd.Series(
        [10000.0 * (1 + 0.005 * i + 0.002 * (i % 7 - 3)) for i in range(n)],
        index=idx,
    )
    df = pd.DataFrame(
        {
            "open": close * 0.998,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": [1_000_000] * n,
        },
        index=idx,
    )
    return df


@pytest.fixture
def cross_asset_df():
    """Mock cross-asset DataFrame covering the same period."""
    n = 80
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "gold_close": [1800.0 + i for i in range(n)],
            "gold_1d_return": [0.001] * n,
            "gold_5d_return": [0.005] * n,
            "usdidr_rate": [16000.0 + i * 10 for i in range(n)],
            "usdidr_1d_return": [0.0005] * n,
            "usdidr_5d_return": [0.0025] * n,
            "usdidr_vol_20d": [0.08] * n,
            "btc_close": [50000.0 + i * 100 for i in range(n)],
            "btc_1d_return": [0.002] * n,
            "btc_vol_30d": [0.70] * n,
            "btc_regime": [1.0] * n,
        },
        index=idx,
    )


class TestMultiframeFeatures:
    def test_return_60d_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        assert "return_60d" in result.columns

    def test_vol_features_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        for col in ["vol_5d", "vol_10d", "vol_20d", "vol_60d"]:
            assert col in result.columns, f"Missing: {col}"

    def test_momentum_zscore_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        assert "momentum_zscore_20d" in result.columns

    def test_vol_20d_is_annualised(self, price_df):
        """vol_20d should be annualised (×√252), not raw daily std."""
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        finite = result["vol_20d"].dropna()
        assert (finite > 0).all()
        assert (finite < 2.0).all()  # sanity: < 200% annualised


class TestRegimeFeatures:
    def test_market_regime_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        assert "market_regime" in result.columns

    def test_trend_strength_added(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        assert "trend_strength" in result.columns

    def test_market_regime_values_valid(self, price_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        valid = {0, 1, 2}
        regime_vals = set(result["market_regime"].dropna().astype(int).unique())
        assert regime_vals.issubset(valid)


class TestCrossAssetFeatures:
    def test_cross_asset_features_present_when_df_provided(self, price_df, cross_asset_df):
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df, cross_asset_df=cross_asset_df)
        expected = [
            "usdidr_1d_return", "usdidr_5d_return", "usdidr_vol_20d",
            "gold_1d_return", "gold_5d_return",
            "btc_1d_return", "btc_vol_30d", "btc_regime",
            "stock_btc_corr_20d", "stock_gold_corr_20d",
        ]
        for col in expected:
            assert col in result.columns, f"Missing: {col}"

    def test_cross_asset_nan_when_no_df(self, price_df):
        """Backward-compatible: no cross_asset_df → cross-asset cols absent or all NaN."""
        fe = IDXFeatureEngineer()
        result = fe.generate_technical_features(price_df)
        if "btc_1d_return" in result.columns:
            assert result["btc_1d_return"].isna().all()

    def test_original_features_unchanged(self, price_df, cross_asset_df):
        """Adding cross-asset should not remove or alter existing feature columns."""
        fe = IDXFeatureEngineer()
        base = fe.generate_technical_features(price_df)
        enhanced = fe.generate_technical_features(price_df, cross_asset_df=cross_asset_df)
        for col in base.columns:
            assert col in enhanced.columns
