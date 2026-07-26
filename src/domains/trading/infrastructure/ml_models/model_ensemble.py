"""
Ensemble ML Models for Indonesian Quantitative Trading System
Implements specialized models for technical, fundamental, and sentiment analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import xgboost as xgb
import joblib
import warnings
warnings.filterwarnings('ignore')

from src.domains.market_data.application.triple_barrier import TripleBarrierLabeler
from .lightgbm_model import LightGBMSignalModel


class TechnicalSignalModel:
    """
    Random Forest model optimized for technical analysis signals
    Handles high-frequency price and volume patterns
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'n_estimators': 200,
            'max_depth': 10,
            'min_samples_split': 20,
            'min_samples_leaf': 10,
            'random_state': 42,
            'n_jobs': -1
        }

        self.model = RandomForestClassifier(**self.config)
        self.scaler = RobustScaler()
        self.feature_importance = None
        self.is_trained = False

    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Prepare technical features for model training

        Args:
            data: DataFrame with technical indicators

        Returns:
            Tuple of (feature_matrix, feature_names)
        """
        # Select technical features
        technical_cols = [
            col for col in data.columns
            if any(keyword in col for keyword in [
                'return_', 'ma_', 'price_to_ma', 'momentum_', 'rsi_', 'macd',
                'stoch_', 'williams_r', 'bb_', 'volume_', 'vwap', 'obv',
                'atr', 'adx', 'gap'
            ])
        ]

        feature_matrix = data[technical_cols].fillna(0)
        return feature_matrix.values, technical_cols

    def create_targets(self, data: pd.DataFrame, horizon: int = 5) -> np.ndarray:
        """
        Create triple-barrier labels for each bar.

        Labels: +1.0 (profit target hit), -1.0 (stop-loss hit), 0.0 (time exit).
        NaN rows are excluded in train() via the existing mask.

        ATR must be present in `data` (computed by IDXFeatureEngineer).
        Falls back to binary sign-of-return labels if ATR is missing.
        """
        if "atr" not in data.columns or data["atr"].isna().all():
            # Fallback: binary label based on sign of forward return
            fwd = data["close"].pct_change(horizon).shift(-horizon)
            return np.where(fwd > 0, 1.0, -1.0)

        labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=horizon * 2)
        labels = labeler.label(data["close"], data["atr"])
        return labels.values

    def train(self, data: pd.DataFrame, target_horizon: int = 5) -> Dict[str, float]:
        """
        Train the technical signal model

        Args:
            data: Training data with technical features
            target_horizon: Days ahead to predict

        Returns:
            Dictionary with training metrics
        """
        # Prepare features and targets
        X, feature_names = self.prepare_features(data)
        y = self.create_targets(data, target_horizon)

        # Remove rows with NaN targets
        mask = ~pd.isna(y)
        X, y = X[mask], y[mask]

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=tscv, scoring='accuracy')

        # Train final model
        self.model.fit(X_scaled, y)

        # Store feature importance
        self.feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        self.is_trained = True

        return {
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'training_accuracy': self.model.score(X_scaled, y),
            'n_features': len(feature_names),
            'n_samples': len(X_scaled)
        }

    def predict(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate predictions and probabilities

        Args:
            data: DataFrame with technical features

        Returns:
            Tuple of (predictions, probabilities)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        X, _ = self.prepare_features(data)
        X_scaled = self.scaler.transform(X)

        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)

        return predictions, probabilities


class FundamentalValueModel:
    """
    Gradient Boosting model for fundamental analysis
    Focuses on valuation and financial health metrics
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'n_estimators': 150,
            'learning_rate': 0.1,
            'max_depth': 6,
            'subsample': 0.8,
            'random_state': 42
        }

        self.model = GradientBoostingRegressor(**self.config)
        self.scaler = StandardScaler()
        self.feature_importance = None
        self.is_trained = False

    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Prepare fundamental features for model training

        Args:
            data: DataFrame with fundamental ratios

        Returns:
            Tuple of (feature_matrix, feature_names)
        """
        # Select fundamental features
        fundamental_cols = [
            col for col in data.columns
            if any(keyword in col for keyword in [
                'pe_ratio', 'pb_ratio', 'ps_ratio', 'ev_', 'roe', 'roa', 'roic',
                'debt_to_', 'current_ratio', 'quick_ratio', 'interest_coverage',
                'asset_turnover', 'growth_', 'earnings_quality', 'policy_',
                'commodity_', 'export_'
            ])
        ]

        # Handle missing values with forward fill and median
        feature_matrix = data[fundamental_cols].ffill().fillna(0)

        # Remove extreme outliers (beyond 3 standard deviations)
        for col in fundamental_cols:
            q99 = feature_matrix[col].quantile(0.99)
            q01 = feature_matrix[col].quantile(0.01)
            feature_matrix[col] = feature_matrix[col].clip(q01, q99)

        return feature_matrix.values, fundamental_cols

    def create_targets(self, data: pd.DataFrame, horizon: int = 20) -> np.ndarray:
        """
        Create regression targets based on risk-adjusted returns

        Args:
            data: DataFrame with price data
            horizon: Forward-looking period for returns

        Returns:
            Array of target values (risk-adjusted returns)
        """
        # Calculate forward returns
        forward_returns = data['close'].pct_change(horizon).shift(-horizon)

        # Calculate volatility for risk adjustment
        volatility = data['close'].pct_change().rolling(20).std()

        # Risk-adjusted returns (Sharpe-like ratio)
        risk_adjusted_returns = forward_returns / (volatility.shift(-horizon) + 1e-6)

        return risk_adjusted_returns.values

    def train(self, data: pd.DataFrame, target_horizon: int = 20) -> Dict[str, float]:
        """
        Train the fundamental value model

        Args:
            data: Training data with fundamental features
            target_horizon: Days ahead to predict

        Returns:
            Dictionary with training metrics
        """
        # Prepare features and targets
        X, feature_names = self.prepare_features(data)
        y = self.create_targets(data, target_horizon)

        # Remove rows with NaN targets
        mask = ~pd.isna(y)
        X, y = X[mask], y[mask]

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=tscv, scoring='r2')

        # Train final model
        self.model.fit(X_scaled, y)

        # Store feature importance
        self.feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        self.is_trained = True

        return {
            'cv_r2_mean': cv_scores.mean(),
            'cv_r2_std': cv_scores.std(),
            'training_r2': self.model.score(X_scaled, y),
            'n_features': len(feature_names),
            'n_samples': len(X_scaled)
        }

    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """
        Generate predictions

        Args:
            data: DataFrame with fundamental features

        Returns:
            Array of predicted risk-adjusted returns
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        X, _ = self.prepare_features(data)
        X_scaled = self.scaler.transform(X)

        predictions = self.model.predict(X_scaled)
        return predictions


class SentimentMomentumModel:
    """
    XGBoost model for sentiment and momentum analysis
    Captures market dynamics and behavioral factors
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'n_estimators': 200,
            'learning_rate': 0.1,
            'max_depth': 6,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1
        }

        self.model = xgb.XGBClassifier(**self.config)
        self.scaler = RobustScaler()
        self.feature_importance = None
        self.is_trained = False

    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Prepare sentiment and momentum features

        Args:
            data: DataFrame with sentiment and momentum indicators

        Returns:
            Tuple of (feature_matrix, feature_names)
        """
        # Select sentiment and momentum features
        sentiment_cols = [
            col for col in data.columns
            if any(keyword in col for keyword in [
                'momentum_', 'relative_strength', 'volume_momentum',
                'sentiment_', 'news_count', 'vol_percentile',
                'momentum_consistency'
            ])
        ]

        feature_matrix = data[sentiment_cols].fillna(0)
        return feature_matrix.values, sentiment_cols

    def create_targets(self, data: pd.DataFrame, horizon: int = 10) -> np.ndarray:
        """
        Create momentum-based targets

        Args:
            data: DataFrame with price data
            horizon: Forward-looking period for momentum

        Returns:
            Array of target classes
        """
        # Calculate forward momentum
        forward_momentum = (data['close'].shift(-horizon) / data['close'] - 1)

        # Create momentum-based targets
        bins = pd.cut(forward_momentum, bins=3, labels=[0, 1, 2])

        return bins.to_numpy(dtype=float)

    def train(self, data: pd.DataFrame, target_horizon: int = 10) -> Dict[str, float]:
        """
        Train the sentiment momentum model

        Args:
            data: Training data with sentiment features
            target_horizon: Days ahead to predict

        Returns:
            Dictionary with training metrics
        """
        # Prepare features and targets
        X, feature_names = self.prepare_features(data)
        y = self.create_targets(data, target_horizon)

        # Remove rows with NaN targets
        mask = ~pd.isna(y)
        X, y = X[mask], y[mask]

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=tscv, scoring='accuracy')

        # Train final model
        self.model.fit(X_scaled, y)

        # Store feature importance
        self.feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        self.is_trained = True

        return {
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'training_accuracy': self.model.score(X_scaled, y),
            'n_features': len(feature_names),
            'n_samples': len(X_scaled)
        }

    def predict(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate predictions and probabilities

        Args:
            data: DataFrame with sentiment features

        Returns:
            Tuple of (predictions, probabilities)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        X, _ = self.prepare_features(data)
        X_scaled = self.scaler.transform(X)

        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)

        return predictions, probabilities


class EnsembleMetaModel:
    """
    Meta-learning layer that combines outputs from specialized models
    Uses linear regression for interpretability and transparency
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'alpha': 1.0,  # Regularization strength
            'fit_intercept': True,
        }

        self.model = Ridge(**self.config)
        self.scaler = StandardScaler()
        self.is_trained = False

    def prepare_ensemble_features(self, technical_pred: np.ndarray,
                                fundamental_pred: np.ndarray,
                                sentiment_pred: np.ndarray,
                                market_features: pd.DataFrame = None) -> np.ndarray:
        """
        Combine predictions from specialized models into ensemble features

        Args:
            technical_pred: Technical model predictions
            fundamental_pred: Fundamental model predictions
            sentiment_pred: Sentiment model predictions
            market_features: Additional market-wide features

        Returns:
            Combined feature matrix for meta-model
        """
        # Base ensemble features from model predictions
        ensemble_features = []

        # Technical model features (probabilities)
        if technical_pred.ndim > 1:  # Probabilities
            ensemble_features.extend([
                technical_pred[:, -1],  # Strong buy probability
                technical_pred[:, -2],  # Buy probability
                np.max(technical_pred, axis=1)  # Max confidence
            ])
        else:  # Simple predictions
            ensemble_features.append(technical_pred)

        # Fundamental model features
        ensemble_features.append(fundamental_pred)

        # Sentiment model features
        if sentiment_pred.ndim > 1:  # Probabilities
            ensemble_features.extend([
                sentiment_pred[:, -1],  # Strong momentum probability
                np.max(sentiment_pred, axis=1)  # Max confidence
            ])
        else:  # Simple predictions
            ensemble_features.append(sentiment_pred)

        # Model agreement features
        if technical_pred.ndim > 1 and sentiment_pred.ndim > 1:
            # Agreement: both models predict the same highest-confidence class
            tech_class = np.argmax(technical_pred, axis=1)
            sent_class = np.argmax(sentiment_pred, axis=1)
            ensemble_features.append((tech_class == sent_class).astype(float))

        # Additional market features if provided
        if market_features is not None:
            market_cols = ['vol_percentile', 'market_return_20d', 'volume_ratio']
            for col in market_cols:
                if col in market_features.columns:
                    ensemble_features.append(market_features[col].values)

        return np.column_stack(ensemble_features)

    def create_targets(self, data: pd.DataFrame, horizon: int = 5) -> np.ndarray:
        """
        Create final targets for meta-model (risk-adjusted returns)

        Args:
            data: DataFrame with price data
            horizon: Forward-looking period

        Returns:
            Array of target values
        """
        # Calculate forward returns
        forward_returns = data['close'].pct_change(horizon).shift(-horizon)

        # Calculate risk adjustment
        volatility = data['close'].pct_change().rolling(20).std().shift(-horizon)

        # Risk-adjusted returns
        risk_adjusted_returns = forward_returns / (volatility + 1e-6)

        return risk_adjusted_returns.values

    def train(self, ensemble_features: np.ndarray, targets: np.ndarray) -> Dict[str, float]:
        """
        Train the meta-model

        Args:
            ensemble_features: Combined features from specialized models
            targets: Target values

        Returns:
            Dictionary with training metrics
        """
        # Remove rows with NaN targets
        mask = ~pd.isna(targets)
        X, y = ensemble_features[mask], targets[mask]

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=tscv, scoring='r2')

        # Train final model
        self.model.fit(X_scaled, y)

        self.is_trained = True

        return {
            'cv_r2_mean': cv_scores.mean(),
            'cv_r2_std': cv_scores.std(),
            'training_r2': self.model.score(X_scaled, y),
            'coefficients': self.model.coef_.tolist(),
            'intercept': self.model.intercept_
        }

    def predict(self, ensemble_features: np.ndarray) -> np.ndarray:
        """
        Generate final ensemble predictions

        Args:
            ensemble_features: Combined features from specialized models

        Returns:
            Array of predicted risk-adjusted returns
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        X_scaled = self.scaler.transform(ensemble_features)
        predictions = self.model.predict(X_scaled)

        return predictions


class IDXQuantitativeModel:
    """
    Main ensemble model that orchestrates all specialized models
    Provides unified interface for training and prediction
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # Initialize specialized models — LightGBM replaces RandomForest for primary signal
        self.technical_model = LightGBMSignalModel(
            self.config.get('technical', None)
        )
        self.fundamental_model = FundamentalValueModel(
            self.config.get('fundamental', {})
        )
        self.sentiment_model = SentimentMomentumModel(
            self.config.get('sentiment', {})
        )
        self.meta_model = EnsembleMetaModel(
            self.config.get('meta', {})
        )

        self.is_trained = False
        self.training_metrics = {}

    def train(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Train the complete ensemble model

        Args:
            data: Training data with all features

        Returns:
            Dictionary with comprehensive training metrics
        """
        print("Training technical signal model...")
        tech_metrics = self.technical_model.train(data)

        print("Training fundamental value model...")
        fund_metrics = self.fundamental_model.train(data)

        print("Training sentiment momentum model...")
        sent_metrics = self.sentiment_model.train(data)

        print("Training ensemble meta-model...")
        # Generate predictions from specialized models for meta-training
        tech_pred, tech_prob = self.technical_model.predict(data)
        fund_pred = self.fundamental_model.predict(data)
        sent_pred, sent_prob = self.sentiment_model.predict(data)

        # Combine for meta-model training
        ensemble_features = self.meta_model.prepare_ensemble_features(
            tech_prob, fund_pred, sent_prob, data
        )
        meta_targets = self.meta_model.create_targets(data)

        meta_metrics = self.meta_model.train(ensemble_features, meta_targets)

        self.is_trained = True
        self.training_metrics = {
            'technical': tech_metrics,
            'fundamental': fund_metrics,
            'sentiment': sent_metrics,
            'meta': meta_metrics
        }

        return self.training_metrics

    def predict(self, data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Generate predictions from the ensemble model

        Args:
            data: Data for prediction

        Returns:
            Dictionary with predictions from all models
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        # Generate predictions from specialized models
        tech_pred, tech_prob = self.technical_model.predict(data)
        fund_pred = self.fundamental_model.predict(data)
        sent_pred, sent_prob = self.sentiment_model.predict(data)

        # Generate ensemble prediction
        ensemble_features = self.meta_model.prepare_ensemble_features(
            tech_prob, fund_pred, sent_prob, data
        )
        ensemble_pred = self.meta_model.predict(ensemble_features)

        return {
            'technical_class': tech_pred,
            'technical_prob': tech_prob,
            'fundamental_score': fund_pred,
            'sentiment_class': sent_pred,
            'sentiment_prob': sent_prob,
            'ensemble_score': ensemble_pred
        }

    def get_feature_importance(self) -> Dict[str, pd.DataFrame]:
        """
        Get feature importance from all trained models

        Returns:
            Dictionary with feature importance DataFrames
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before getting feature importance")

        return {
            'technical': self.technical_model.feature_importance,
            'fundamental': self.fundamental_model.feature_importance,
            'sentiment': self.sentiment_model.feature_importance
        }

    def save_models(self, filepath: str):
        """Save all trained models to disk"""
        model_dict = {
            'technical': self.technical_model,
            'fundamental': self.fundamental_model,
            'sentiment': self.sentiment_model,
            'meta': self.meta_model,
            'config': self.config,
            'training_metrics': self.training_metrics
        }
        joblib.dump(model_dict, filepath)

    @classmethod
    def load_models(cls, filepath: str):
        """Load trained models from disk"""
        model_dict = joblib.load(filepath)

        instance = cls(model_dict['config'])
        instance.technical_model = model_dict['technical']
        instance.fundamental_model = model_dict['fundamental']
        instance.sentiment_model = model_dict['sentiment']
        instance.meta_model = model_dict['meta']
        instance.training_metrics = model_dict['training_metrics']
        instance.is_trained = True

        return instance


if __name__ == "__main__":
    # Example usage
    import pandas as pd
    from feature_engineering import IDXFeatureEngineer

    # Generate sample data (in practice, this would come from your data pipeline)
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
    n_samples = len(dates)

    sample_data = pd.DataFrame({
        'date': dates,
        'close': 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, n_samples))),
        'volume': np.random.lognormal(15, 0.5, n_samples),
        'high': lambda x: x['close'] * (1 + np.abs(np.random.normal(0, 0.01, n_samples))),
        'low': lambda x: x['close'] * (1 - np.abs(np.random.normal(0, 0.01, n_samples))),
        'open': lambda x: x['close'].shift(1) * (1 + np.random.normal(0, 0.005, n_samples))
    })

    # Generate features
    feature_engineer = IDXFeatureEngineer()
    enhanced_data = feature_engineer.generate_technical_features(sample_data)

    # Initialize and train ensemble model
    model = IDXQuantitativeModel()

    print("Training ensemble model...")
    training_metrics = model.train(enhanced_data)

    print("\nTraining completed!")
    print("Technical model CV accuracy:", training_metrics['technical']['cv_accuracy_mean'])
    print("Fundamental model CV R²:", training_metrics['fundamental']['cv_r2_mean'])
    print("Sentiment model CV accuracy:", training_metrics['sentiment']['cv_accuracy_mean'])
    print("Meta model CV R²:", training_metrics['meta']['cv_r2_mean'])

    # Generate predictions
    predictions = model.predict(enhanced_data.tail(100))
    print(f"\nGenerated predictions for {len(predictions['ensemble_score'])} samples")
    print("Ensemble scores range:", predictions['ensemble_score'].min(), "to", predictions['ensemble_score'].max())