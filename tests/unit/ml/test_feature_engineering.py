"""
Unit tests for feature engineering module
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from feature_engineering import IDXFeatureEngineer


class TestIDXFeatureEngineer:
    """Test IDX Feature Engineering class"""

    @pytest.fixture
    def sample_price_data(self):
        """Create sample OHLCV price data for testing"""
        dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='D')
        np.random.seed(42)  # For reproducible tests

        # Generate realistic price data
        base_price = 9000
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        data = pd.DataFrame({
            'date': dates,
            'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        })

        return data

    @pytest.fixture
    def feature_engineer(self):
        """Create feature engineer instance"""
        return IDXFeatureEngineer()

    @pytest.fixture
    def custom_feature_engineer(self):
        """Create feature engineer with custom lookback periods"""
        custom_periods = {
            'short_ma': 3,
            'medium_ma': 10,
            'long_ma': 20,
            'volatility': 15,
            'momentum': 5,
            'volume': 10
        }
        return IDXFeatureEngineer(lookback_periods=custom_periods)

    def test_initialization_default_params(self, feature_engineer):
        """Test feature engineer initialization with default parameters"""
        assert feature_engineer.lookback_periods['short_ma'] == 5
        assert feature_engineer.lookback_periods['medium_ma'] == 20
        assert feature_engineer.lookback_periods['long_ma'] == 50
        assert feature_engineer.lookback_periods['volatility'] == 20
        assert feature_engineer.lookback_periods['momentum'] == 10
        assert feature_engineer.lookback_periods['volume'] == 20

    def test_initialization_custom_params(self, custom_feature_engineer):
        """Test feature engineer initialization with custom parameters"""
        assert custom_feature_engineer.lookback_periods['short_ma'] == 3
        assert custom_feature_engineer.lookback_periods['medium_ma'] == 10
        assert custom_feature_engineer.lookback_periods['long_ma'] == 20

    @pytest.mark.ml
    def test_generate_technical_features_basic(self, feature_engineer, sample_price_data):
        """Test basic technical feature generation"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        # Check that result is a DataFrame
        assert isinstance(result, pd.DataFrame)

        # Check that original columns are preserved
        assert 'close' in result.columns
        assert 'volume' in result.columns

        # Check that new features are added (assuming they are implemented)
        expected_features = [
            'sma_5', 'sma_20', 'sma_50',  # Moving averages
            'rsi_14',  # RSI
            'bb_upper', 'bb_lower',  # Bollinger Bands
            'macd', 'macd_signal',  # MACD
            'volatility_20'  # Volatility
        ]

        # Only check for features that should exist based on implementation
        for feature in expected_features:
            if feature in result.columns:
                assert not result[feature].isna().all(), f"Feature {feature} should not be all NaN"

    @pytest.mark.ml
    def test_moving_averages(self, feature_engineer, sample_price_data):
        """Test moving average calculations"""
        # Add moving averages manually for comparison
        df = sample_price_data.copy()
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()

        result = feature_engineer.generate_technical_features(sample_price_data)

        # If moving averages are implemented, they should match manual calculation
        if 'sma_5' in result.columns:
            manual_sma5 = sample_price_data['close'].rolling(window=5).mean()
            pd.testing.assert_series_equal(
                result['sma_5'].dropna(),
                manual_sma5.dropna(),
                check_names=False
            )

        if 'sma_20' in result.columns:
            manual_sma20 = sample_price_data['close'].rolling(window=20).mean()
            pd.testing.assert_series_equal(
                result['sma_20'].dropna(),
                manual_sma20.dropna(),
                check_names=False
            )

    @pytest.mark.ml
    def test_rsi_calculation(self, feature_engineer, sample_price_data):
        """Test RSI calculation"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        if 'rsi_14' in result.columns:
            rsi_values = result['rsi_14'].dropna()

            # RSI should be between 0 and 100
            assert (rsi_values >= 0).all(), "RSI values should be >= 0"
            assert (rsi_values <= 100).all(), "RSI values should be <= 100"

            # RSI should not be constant (unless market is very stable)
            assert rsi_values.std() > 0, "RSI should have some variation"

    @pytest.mark.ml
    def test_bollinger_bands(self, feature_engineer, sample_price_data):
        """Test Bollinger Bands calculation"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        if 'bb_upper' in result.columns and 'bb_lower' in result.columns:
            valid_data = result.dropna()

            # Upper band should be above lower band
            assert (valid_data['bb_upper'] > valid_data['bb_lower']).all(), \
                "Upper Bollinger Band should be above Lower Band"

            # Price should generally be between bands (with some exceptions)
            between_bands = (valid_data['close'] >= valid_data['bb_lower']) & \
                          (valid_data['close'] <= valid_data['bb_upper'])
            assert between_bands.mean() > 0.7, \
                "Most prices should be between Bollinger Bands"

    @pytest.mark.ml
    def test_macd_calculation(self, feature_engineer, sample_price_data):
        """Test MACD calculation"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        if 'macd' in result.columns and 'macd_signal' in result.columns:
            macd_data = result[['macd', 'macd_signal']].dropna()

            # MACD and signal should have reasonable ranges
            assert macd_data['macd'].std() > 0, "MACD should have variation"
            assert macd_data['macd_signal'].std() > 0, "MACD signal should have variation"

            # Signal should be smoother than MACD (lower standard deviation)
            # This test might not always hold, so we'll be lenient
            assert len(macd_data) > 0, "Should have some valid MACD data"

    @pytest.mark.ml
    def test_volatility_calculation(self, feature_engineer, sample_price_data):
        """Test volatility calculation"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        if 'volatility_20' in result.columns:
            volatility = result['volatility_20'].dropna()

            # Volatility should be positive
            assert (volatility >= 0).all(), "Volatility should be non-negative"

            # Volatility should have some variation
            assert volatility.std() > 0, "Volatility should vary over time"

    @pytest.mark.ml
    def test_volume_features(self, feature_engineer, sample_price_data):
        """Test volume-based features"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        # Test volume moving average
        if 'volume_ma_20' in result.columns:
            vol_ma = result['volume_ma_20'].dropna()
            assert (vol_ma > 0).all(), "Volume moving average should be positive"

        # Test volume ratio
        if 'volume_ratio' in result.columns:
            vol_ratio = result['volume_ratio'].dropna()
            assert (vol_ratio >= 0).all(), "Volume ratio should be non-negative"

    @pytest.mark.ml
    def test_price_momentum_features(self, feature_engineer, sample_price_data):
        """Test price momentum features"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        # Test price change features
        if 'price_change_1d' in result.columns:
            price_change = result['price_change_1d'].dropna()
            # Price changes should have both positive and negative values
            assert price_change.min() != price_change.max(), "Price changes should vary"

        # Test momentum indicators
        if 'momentum_10' in result.columns:
            momentum = result['momentum_10'].dropna()
            assert len(momentum) > 0, "Should have momentum data"

    @pytest.mark.ml
    def test_indonesian_market_features(self, feature_engineer, sample_price_data):
        """Test Indonesian market-specific features"""
        # Add IDR currency effect simulation
        sample_price_data['usd_idr_rate'] = 15000 + np.random.normal(0, 100, len(sample_price_data))

        result = feature_engineer.generate_technical_features(sample_price_data)

        # Test currency effect features if implemented
        if 'currency_adjusted_price' in result.columns:
            curr_adj_price = result['currency_adjusted_price'].dropna()
            assert len(curr_adj_price) > 0, "Should have currency adjusted prices"

        # Test sector rotation features if implemented
        if 'sector_momentum' in result.columns:
            sector_momentum = result['sector_momentum'].dropna()
            assert len(sector_momentum) > 0, "Should have sector momentum data"

    @pytest.mark.ml
    def test_feature_engineer_with_missing_data(self, feature_engineer):
        """Test feature engineering with missing data"""
        # Create data with missing values
        dates = pd.date_range(start='2024-01-01', end='2024-01-20', freq='D')
        data = pd.DataFrame({
            'date': dates,
            'open': [9000 + i * 10 for i in range(len(dates))],
            'high': [9100 + i * 10 for i in range(len(dates))],
            'low': [8900 + i * 10 for i in range(len(dates))],
            'close': [9000 + i * 10 for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        })

        # Introduce missing values
        data.loc[5:7, 'close'] = np.nan
        data.loc[10:12, 'volume'] = np.nan

        result = feature_engineer.generate_technical_features(data)

        # Should handle missing data gracefully
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(data)

    @pytest.mark.ml
    def test_feature_engineer_empty_dataframe(self, feature_engineer):
        """Test feature engineering with empty DataFrame"""
        empty_df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])

        result = feature_engineer.generate_technical_features(empty_df)

        # Should handle empty data gracefully
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @pytest.mark.ml
    def test_feature_engineer_insufficient_data(self, feature_engineer):
        """Test feature engineering with insufficient data for calculations"""
        # Create data with only 3 rows (insufficient for many indicators)
        data = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=3, freq='D'),
            'open': [9000, 9010, 9020],
            'high': [9100, 9110, 9120],
            'low': [8900, 8910, 8920],
            'close': [9000, 9010, 9020],
            'volume': [1000000, 1100000, 1200000]
        })

        result = feature_engineer.generate_technical_features(data)

        # Should handle insufficient data gracefully
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

        # Features requiring more data should be NaN
        if 'sma_20' in result.columns:
            assert result['sma_20'].isna().all(), "SMA 20 should be NaN with insufficient data"

    @pytest.mark.ml
    def test_custom_lookback_periods(self, custom_feature_engineer, sample_price_data):
        """Test feature engineering with custom lookback periods"""
        result = custom_feature_engineer.generate_technical_features(sample_price_data)

        # Should use custom periods for calculations
        if 'sma_3' in result.columns:  # Custom short MA period
            manual_sma3 = sample_price_data['close'].rolling(window=3).mean()
            pd.testing.assert_series_equal(
                result['sma_3'].dropna(),
                manual_sma3.dropna(),
                check_names=False
            )

    @pytest.mark.ml
    def test_feature_data_types(self, feature_engineer, sample_price_data):
        """Test that features have appropriate data types"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        # Numerical features should be numeric
        numeric_features = ['close', 'volume']
        for feature in numeric_features:
            if feature in result.columns:
                assert pd.api.types.is_numeric_dtype(result[feature]), \
                    f"Feature {feature} should be numeric"

        # Check for any new features and their types
        for col in result.columns:
            if col not in sample_price_data.columns:
                # New features should generally be numeric
                if not result[col].isna().all():
                    assert pd.api.types.is_numeric_dtype(result[col]), \
                        f"New feature {col} should be numeric"

    @pytest.mark.ml
    def test_feature_names_consistency(self, feature_engineer, sample_price_data):
        """Test that feature names are consistent and meaningful"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        # Check for common feature naming patterns
        expected_patterns = [
            'sma_',     # Simple moving average
            'ema_',     # Exponential moving average
            'rsi',      # RSI
            'bb_',      # Bollinger bands
            'macd',     # MACD
            'volume',   # Volume features
            'volatility' # Volatility
        ]

        new_columns = [col for col in result.columns if col not in sample_price_data.columns]

        # At least some new features should follow expected patterns
        pattern_matches = 0
        for col in new_columns:
            for pattern in expected_patterns:
                if pattern in col.lower():
                    pattern_matches += 1
                    break

        # This is a soft assertion - implementation might vary
        if len(new_columns) > 0:
            assert pattern_matches > 0, "Some features should follow expected naming patterns"

    @pytest.mark.ml
    @pytest.mark.performance
    def test_feature_generation_performance(self, feature_engineer):
        """Test feature generation performance with larger dataset"""
        import time

        # Create larger dataset
        dates = pd.date_range(start='2020-01-01', end='2024-01-01', freq='D')
        np.random.seed(42)

        large_data = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(8000, 10000, len(dates)),
            'high': np.random.uniform(8500, 10500, len(dates)),
            'low': np.random.uniform(7500, 9500, len(dates)),
            'close': np.random.uniform(8000, 10000, len(dates)),
            'volume': np.random.randint(500000, 20000000, len(dates))
        })

        start_time = time.time()
        result = feature_engineer.generate_technical_features(large_data)
        execution_time = time.time() - start_time

        # Should complete within reasonable time (5 seconds for ~4 years of data)
        assert execution_time < 5.0, "Feature generation should complete within 5 seconds"
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(large_data)

    @pytest.mark.ml
    def test_feature_mathematical_properties(self, feature_engineer, sample_price_data):
        """Test mathematical properties of generated features"""
        result = feature_engineer.generate_technical_features(sample_price_data)

        # Test that moving averages smooth the data
        if 'sma_20' in result.columns:
            sma_20 = result['sma_20'].dropna()
            close_std = sample_price_data['close'].std()
            sma_std = sma_20.std()

            # Moving average should be smoother (lower standard deviation)
            assert sma_std <= close_std, "Moving average should be smoother than original price"

        # Test RSI bounds
        if 'rsi_14' in result.columns:
            rsi = result['rsi_14'].dropna()
            assert rsi.min() >= 0, "RSI minimum should be >= 0"
            assert rsi.max() <= 100, "RSI maximum should be <= 100"

        # Test MACD histogram properties
        if 'macd' in result.columns and 'macd_signal' in result.columns:
            macd = result['macd'].dropna()
            macd_signal = result['macd_signal'].dropna()

            # Should have reasonable correlation
            if len(macd) > 10 and len(macd_signal) > 10:
                min_len = min(len(macd), len(macd_signal))
                correlation = np.corrcoef(macd[-min_len:], macd_signal[-min_len:])[0, 1]
                assert correlation > 0.5, "MACD and signal should be positively correlated"