"""
Feature Engineering Module for Indonesian Quantitative Trading System
Focuses on practical, proven features optimized for IDX market conditions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class IDXFeatureEngineer:
    """
    Feature engineering specifically designed for Indonesian stock market (IDX)
    Handles market microstructure, currency effects, and local factors
    """

    def __init__(self, lookback_periods: Dict[str, int] = None):
        """
        Initialize feature engineer with configurable lookback periods

        Args:
            lookback_periods: Dictionary of feature types and their lookback periods
        """
        self.lookback_periods = lookback_periods or {
            'short_ma': 5,
            'medium_ma': 20,
            'long_ma': 50,
            'volatility': 20,
            'momentum': 10,
            'volume': 20
        }

        self.technical_features = []
        self.fundamental_features = []
        self.sentiment_features = []

    def generate_technical_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate technical analysis features optimized for IDX market

        Args:
            price_data: DataFrame with OHLCV data

        Returns:
            DataFrame with technical features
        """
        df = price_data.copy()

        # Price-based features
        df = self._add_price_features(df)

        # Volume-based features
        df = self._add_volume_features(df)

        # Technical indicators
        df = self._add_technical_indicators(df)

        # Market microstructure (important for IDX due to lower liquidity)
        df = self._add_microstructure_features(df)

        # Cross-asset features (IDR, commodities impact)
        df = self._add_cross_asset_features(df)

        return df

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based technical features"""

        # Returns at multiple horizons
        for period in [1, 3, 5, 10, 20]:
            df[f'return_{period}d'] = df['close'].pct_change(period)

        # Moving averages and deviations
        for ma_type, period in self.lookback_periods.items():
            if 'ma' in ma_type:
                df[f'ma_{period}'] = df['close'].rolling(period).mean()
                df[f'price_to_ma_{period}'] = df['close'] / df[f'ma_{period}'] - 1

        # Price momentum and mean reversion signals
        df['price_momentum_5d'] = (df['close'] / df['close'].shift(5) - 1)
        df['price_momentum_20d'] = (df['close'] / df['close'].shift(20) - 1)

        # Bollinger Bands (adjusted for IDX volatility)
        bb_period = 20
        bb_std = 2.5  # Wider bands for emerging market volatility
        df['bb_middle'] = df['close'].rolling(bb_period).mean()
        df['bb_std'] = df['close'].rolling(bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * df['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (bb_std * df['bb_std'])
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # Price gaps (common in IDX due to news overnight)
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        df['gap_filled'] = np.where(
            (df['gap'] > 0) & (df['low'] <= df['close'].shift(1)), 1,
            np.where((df['gap'] < 0) & (df['high'] >= df['close'].shift(1)), -1, 0)
        )

        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features (critical for IDX liquidity assessment)"""

        # Volume trends and ratios
        vol_period = self.lookback_periods['volume']
        df['volume_ma'] = df['volume'].rolling(vol_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Volume-weighted average price
        df['vwap'] = (df['close'] * df['volume']).rolling(vol_period).sum() / df['volume'].rolling(vol_period).sum()
        df['price_to_vwap'] = df['close'] / df['vwap'] - 1

        # On-Balance Volume (OBV)
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        df['obv_ma'] = df['obv'].rolling(vol_period).mean()
        df['obv_trend'] = df['obv'] / df['obv_ma'] - 1

        # Volume-price trend
        df['vpt'] = ((df['close'].diff() / df['close'].shift(1)) * df['volume']).cumsum()
        df['vpt_trend'] = df['vpt'].pct_change(10)

        # Accumulation/Distribution Line
        df['ad_line'] = (((df['close'] - df['low']) - (df['high'] - df['close'])) /
                        (df['high'] - df['low']) * df['volume']).cumsum()
        df['ad_trend'] = df['ad_line'].pct_change(10)

        return df

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add standard technical indicators optimized for IDX"""

        # RSI (adjusted periods for IDX volatility)
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        df['rsi_30'] = self._calculate_rsi(df['close'], 30)  # Longer period for trend

        # MACD
        df['macd'], df['macd_signal'], df['macd_histogram'] = self._calculate_macd(df['close'])

        # Stochastic Oscillator
        df['stoch_k'], df['stoch_d'] = self._calculate_stochastic(df, 14, 3)

        # Williams %R
        df['williams_r'] = self._calculate_williams_r(df, 14)

        # Average Directional Index (ADX) - trend strength
        df['adx'] = self._calculate_adx(df, 14)

        return df

    def _add_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market microstructure features (important for IDX)"""

        # Intraday range and volatility
        df['daily_range'] = (df['high'] - df['low']) / df['close']
        df['true_range'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )

        # Average True Range (ATR)
        atr_period = 14
        df['atr'] = df['true_range'].rolling(atr_period).mean()
        df['atr_ratio'] = df['true_range'] / df['atr']

        # Opening price behavior (gap analysis)
        df['open_to_close'] = (df['close'] - df['open']) / df['open']
        df['overnight_return'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)

        # Close position within daily range
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])

        return df

    def _add_cross_asset_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add cross-asset features relevant to Indonesian market"""

        # Placeholder for currency and commodity features
        # In practice, these would be joined from external data sources

        # IDR volatility impact (would be calculated from USD/IDR data)
        # df['idr_volatility'] = ... (from currency data)

        # Commodity price sensitivity (for commodity-exposed stocks)
        # df['palm_oil_correlation'] = ... (for AALI, LSIP, etc.)
        # df['coal_price_correlation'] = ... (for ADRO, PTBA, etc.)

        # Regional market correlation
        # df['idx_correlation'] = ... (correlation with IDX Composite)

        return df

    def generate_fundamental_features(self, fundamental_data: pd.DataFrame,
                                    price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate fundamental analysis features for IDX stocks

        Args:
            fundamental_data: DataFrame with financial statement data
            price_data: DataFrame with price data for market cap calculations

        Returns:
            DataFrame with fundamental features
        """
        df = fundamental_data.copy()

        # Valuation ratios
        df = self._add_valuation_ratios(df, price_data)

        # Financial health metrics
        df = self._add_financial_health_metrics(df)

        # Growth metrics
        df = self._add_growth_metrics(df)

        # Indonesian specific metrics
        df = self._add_idx_specific_metrics(df)

        return df

    def _add_valuation_ratios(self, df: pd.DataFrame, price_data: pd.DataFrame) -> pd.DataFrame:
        """Add valuation ratio features"""

        # Basic valuation ratios
        df['pe_ratio'] = price_data['market_cap'] / df['net_income']
        df['pb_ratio'] = price_data['market_cap'] / df['book_value']
        df['ps_ratio'] = price_data['market_cap'] / df['revenue']

        # Relative valuations (vs sector median)
        for ratio in ['pe_ratio', 'pb_ratio', 'ps_ratio']:
            df[f'{ratio}_vs_sector'] = df.groupby('sector')[ratio].transform(
                lambda x: (x - x.median()) / x.median()
            )

        # EV ratios
        df['ev'] = price_data['market_cap'] + df['total_debt'] - df['cash']
        df['ev_revenue'] = df['ev'] / df['revenue']
        df['ev_ebitda'] = df['ev'] / df['ebitda']

        return df

    def _add_financial_health_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add financial health and quality metrics"""

        # Profitability metrics
        df['roe'] = df['net_income'] / df['shareholders_equity']
        df['roa'] = df['net_income'] / df['total_assets']
        df['roic'] = df['ebit'] / (df['total_assets'] - df['current_liabilities'])

        # Leverage metrics
        df['debt_to_equity'] = df['total_debt'] / df['shareholders_equity']
        df['debt_to_assets'] = df['total_debt'] / df['total_assets']
        df['interest_coverage'] = df['ebit'] / df['interest_expense']

        # Liquidity metrics
        df['current_ratio'] = df['current_assets'] / df['current_liabilities']
        df['quick_ratio'] = (df['current_assets'] - df['inventory']) / df['current_liabilities']
        df['cash_ratio'] = df['cash'] / df['current_liabilities']

        # Efficiency metrics
        df['asset_turnover'] = df['revenue'] / df['total_assets']
        df['inventory_turnover'] = df['cogs'] / df['inventory']
        df['receivables_turnover'] = df['revenue'] / df['accounts_receivable']

        return df

    def _add_growth_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add growth and trend metrics"""

        # Year-over-year growth rates
        for metric in ['revenue', 'net_income', 'ebitda', 'book_value']:
            df[f'{metric}_growth_yoy'] = df[metric].pct_change(4)  # Quarterly data
            df[f'{metric}_growth_3y_cagr'] = (df[metric] / df[metric].shift(12)) ** (1/3) - 1

        # Growth consistency (lower volatility = higher quality)
        for metric in ['revenue', 'net_income']:
            df[f'{metric}_growth_volatility'] = df[f'{metric}_growth_yoy'].rolling(8).std()

        # Earnings quality
        df['earnings_quality'] = df['operating_cash_flow'] / df['net_income']
        df['accruals_ratio'] = (df['net_income'] - df['operating_cash_flow']) / df['total_assets']

        return df

    def _add_idx_specific_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Indonesian market specific fundamental metrics"""

        # Foreign ownership impact (if available)
        # df['foreign_ownership_pct'] = ... (from ownership data)

        # Government policy exposure
        # Simple scoring based on sector and business model
        policy_sensitive_sectors = ['BANKING', 'TELECOM', 'UTILITIES', 'MINING']
        df['policy_sensitivity'] = df['sector'].isin(policy_sensitive_sectors).astype(int)

        # Commodity exposure (for Indonesian economy)
        commodity_sectors = ['MINING', 'PLANTATION', 'ENERGY']
        df['commodity_exposure'] = df['sector'].isin(commodity_sectors).astype(int)

        # Export orientation (approximation based on sector)
        export_oriented_sectors = ['MINING', 'PLANTATION', 'MANUFACTURING']
        df['export_orientation'] = df['sector'].isin(export_oriented_sectors).astype(int)

        return df

    def generate_sentiment_features(self, news_data: pd.DataFrame,
                                  market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate sentiment and momentum features

        Args:
            news_data: DataFrame with news sentiment scores
            market_data: DataFrame with market-wide data

        Returns:
            DataFrame with sentiment features
        """
        df = market_data.copy()

        # Technical momentum features
        df = self._add_momentum_features(df)

        # Market sentiment proxies
        df = self._add_market_sentiment_features(df)

        # News sentiment (simplified for practicality)
        if not news_data.empty:
            df = self._add_news_sentiment_features(df, news_data)

        return df

    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum-based features"""

        # Price momentum at multiple horizons
        for period in [5, 10, 20, 60]:
            df[f'momentum_{period}d'] = (df['close'] / df['close'].shift(period) - 1)

        # Momentum quality (consistency)
        df['momentum_consistency'] = (
            np.sign(df['momentum_5d']) == np.sign(df['momentum_20d'])
        ).astype(int)

        # Relative strength vs market
        df['relative_strength'] = df['momentum_20d'] - df['market_return_20d']

        # Volume-adjusted momentum
        df['volume_momentum'] = df['momentum_10d'] * df['volume_ratio']

        return df

    def _add_market_sentiment_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market-wide sentiment proxies"""

        # Volatility-based sentiment
        df['vol_20d'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252)
        df['vol_percentile'] = df['vol_20d'].rolling(252).rank(pct=True)

        # Put-call ratio proxy (if options data available)
        # df['put_call_ratio'] = ... (from options data)

        # Foreign flow sentiment (approximation)
        # df['foreign_flow_sentiment'] = ... (from flow data)

        return df

    def _add_news_sentiment_features(self, df: pd.DataFrame,
                                   news_data: pd.DataFrame) -> pd.DataFrame:
        """Add news sentiment features (simplified approach)"""

        # Simple keyword-based sentiment scoring
        # In practice, this would use more sophisticated NLP

        # Aggregate news sentiment by stock and date
        if 'sentiment_score' in news_data.columns:
            daily_sentiment = news_data.groupby(['stock_code', 'date'])['sentiment_score'].agg([
                'mean', 'std', 'count'
            ]).reset_index()

            df = df.merge(daily_sentiment, on=['stock_code', 'date'], how='left')

            # Fill missing sentiment with neutral
            df['sentiment_mean'] = df['sentiment_mean'].fillna(0)
            df['sentiment_std'] = df['sentiment_std'].fillna(0)
            df['news_count'] = df['count'].fillna(0)

        return df

    # Helper methods for technical indicators
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, prices: pd.Series, fast: int = 12,
                       slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        return macd, macd_signal, macd_histogram

    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14,
                            d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        k_percent = 100 * ((df['close'] - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent

    def _calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        return -100 * ((high_max - df['close']) / (high_max - low_min))

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (simplified)"""
        high_diff = df['high'].diff()
        low_diff = df['low'].diff()

        pos_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        neg_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        tr = np.maximum(df['high'] - df['low'],
                       np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))

        pos_di = 100 * pd.Series(pos_dm).rolling(period).mean() / pd.Series(tr).rolling(period).mean()
        neg_di = 100 * pd.Series(neg_dm).rolling(period).mean() / pd.Series(tr).rolling(period).mean()

        dx = 100 * abs(pos_di - neg_di) / (pos_di + neg_di)
        adx = dx.rolling(period).mean()

        return adx


def create_feature_pipeline(config: Dict) -> IDXFeatureEngineer:
    """
    Factory function to create feature engineering pipeline

    Args:
        config: Configuration dictionary with feature parameters

    Returns:
        Configured IDXFeatureEngineer instance
    """
    return IDXFeatureEngineer(
        lookback_periods=config.get('lookback_periods', {
            'short_ma': 5,
            'medium_ma': 20,
            'long_ma': 50,
            'volatility': 20,
            'momentum': 10,
            'volume': 20
        })
    )


if __name__ == "__main__":
    # Example usage
    import yfinance as yf

    # Download sample IDX stock data
    ticker = "BBCA.JK"  # Bank Central Asia
    data = yf.download(ticker, start="2020-01-01", end="2024-01-01")
    data.columns = [col.lower() for col in data.columns]
    data = data.reset_index()

    # Initialize feature engineer
    feature_engineer = IDXFeatureEngineer()

    # Generate technical features
    technical_features = feature_engineer.generate_technical_features(data)

    print("Generated technical features:")
    print(technical_features.columns.tolist())
    print(f"Feature matrix shape: {technical_features.shape}")
    print(technical_features.tail())