"""
Advanced drift detection algorithms specifically for Indonesian stock market data
Implements statistical and ML-based drift detection methods
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    from scipy import stats
    from scipy.spatial.distance import jensenshannon
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy/sklearn not available. Some drift detection methods will be limited.")

@dataclass
class DriftResult:
    """Result of drift detection analysis"""
    feature_name: str
    drift_detected: bool
    drift_score: float
    method: str
    threshold: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    timestamp: str

class AdvancedDriftDetector:
    """
    Advanced drift detection for Indonesian stock market models
    Implements multiple statistical and ML-based drift detection methods
    """

    def __init__(self):
        """Initialize drift detector with IDX-specific parameters"""

        # Indonesian market specific thresholds
        self.market_thresholds = {
            'volume': {'low': 0.1, 'medium': 0.2, 'high': 0.3},
            'price': {'low': 0.05, 'medium': 0.1, 'high': 0.15},
            'technical_indicators': {'low': 0.15, 'medium': 0.25, 'high': 0.35},
            'market_sentiment': {'low': 0.2, 'medium': 0.3, 'high': 0.4}
        }

        # Statistical test thresholds
        self.stat_thresholds = {
            'ks_test': 0.05,
            'mann_whitney': 0.05,
            'chi2_test': 0.05,
            'psi_threshold': 0.2,
            'jensen_shannon': 0.1,
            'wasserstein_distance': 0.3
        }

        self.scaler = StandardScaler() if SCIPY_AVAILABLE else None
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42) if SCIPY_AVAILABLE else None

    def detect_univariate_drift(self, reference_data: np.ndarray,
                               current_data: np.ndarray,
                               feature_name: str = "feature",
                               feature_type: str = "general") -> List[DriftResult]:
        """
        Detect drift in a single feature using multiple statistical tests
        """
        results = []
        timestamp = datetime.now().isoformat()

        if len(reference_data) == 0 or len(current_data) == 0:
            return results

        # Get appropriate thresholds based on feature type
        thresholds = self.market_thresholds.get(feature_type, self.market_thresholds['technical_indicators'])

        try:
            # 1. Kolmogorov-Smirnov Test
            if SCIPY_AVAILABLE:
                ks_stat, ks_pvalue = stats.ks_2samp(reference_data, current_data)
                drift_detected = ks_pvalue < self.stat_thresholds['ks_test']
                severity = self._determine_severity(ks_stat, thresholds)

                results.append(DriftResult(
                    feature_name=feature_name,
                    drift_detected=drift_detected,
                    drift_score=ks_stat,
                    method="Kolmogorov-Smirnov",
                    threshold=self.stat_thresholds['ks_test'],
                    severity=severity,
                    description=f"KS test: statistic={ks_stat:.4f}, p-value={ks_pvalue:.4f}",
                    timestamp=timestamp
                ))

            # 2. Population Stability Index (PSI)
            psi_score = self._calculate_psi_detailed(reference_data, current_data)
            drift_detected = psi_score > self.stat_thresholds['psi_threshold']
            severity = self._determine_severity(psi_score, {'low': 0.1, 'medium': 0.2, 'high': 0.25})

            results.append(DriftResult(
                feature_name=feature_name,
                drift_detected=drift_detected,
                drift_score=psi_score,
                method="PSI",
                threshold=self.stat_thresholds['psi_threshold'],
                severity=severity,
                description=f"PSI score: {psi_score:.4f}",
                timestamp=timestamp
            ))

            # 3. Jensen-Shannon Divergence
            if SCIPY_AVAILABLE:
                js_distance = self._calculate_jensen_shannon(reference_data, current_data)
                drift_detected = js_distance > self.stat_thresholds['jensen_shannon']
                severity = self._determine_severity(js_distance, {'low': 0.05, 'medium': 0.1, 'high': 0.15})

                results.append(DriftResult(
                    feature_name=feature_name,
                    drift_detected=drift_detected,
                    drift_score=js_distance,
                    method="Jensen-Shannon",
                    threshold=self.stat_thresholds['jensen_shannon'],
                    severity=severity,
                    description=f"JS divergence: {js_distance:.4f}",
                    timestamp=timestamp
                ))

            # 4. Wasserstein Distance (Earth Mover's Distance)
            if SCIPY_AVAILABLE:
                wasserstein_dist = stats.wasserstein_distance(reference_data, current_data)
                # Normalize by the range of reference data
                ref_range = np.max(reference_data) - np.min(reference_data)
                normalized_wasserstein = wasserstein_dist / (ref_range + 1e-8)

                drift_detected = normalized_wasserstein > self.stat_thresholds['wasserstein_distance']
                severity = self._determine_severity(normalized_wasserstein, thresholds)

                results.append(DriftResult(
                    feature_name=feature_name,
                    drift_detected=drift_detected,
                    drift_score=normalized_wasserstein,
                    method="Wasserstein",
                    threshold=self.stat_thresholds['wasserstein_distance'],
                    severity=severity,
                    description=f"Wasserstein distance (normalized): {normalized_wasserstein:.4f}",
                    timestamp=timestamp
                ))

            # 5. Statistical Moments Comparison
            moments_drift = self._compare_statistical_moments(reference_data, current_data)
            drift_detected = moments_drift['drift_score'] > 0.2

            results.append(DriftResult(
                feature_name=feature_name,
                drift_detected=drift_detected,
                drift_score=moments_drift['drift_score'],
                method="Statistical Moments",
                threshold=0.2,
                severity=moments_drift['severity'],
                description=f"Moments comparison: {moments_drift['description']}",
                timestamp=timestamp
            ))

        except Exception as e:
            # Fallback to simple statistical comparison
            simple_drift = self._simple_drift_detection(reference_data, current_data)
            results.append(DriftResult(
                feature_name=feature_name,
                drift_detected=simple_drift['drift_detected'],
                drift_score=simple_drift['score'],
                method="Simple Statistical",
                threshold=simple_drift['threshold'],
                severity=simple_drift['severity'],
                description=f"Fallback method: {simple_drift['description']}",
                timestamp=timestamp
            ))

        return results

    def detect_multivariate_drift(self, reference_df: pd.DataFrame,
                                 current_df: pd.DataFrame) -> List[DriftResult]:
        """
        Detect drift in multiple features simultaneously
        """
        results = []
        timestamp = datetime.now().isoformat()

        if reference_df.empty or current_df.empty:
            return results

        try:
            # Ensure same columns
            common_columns = set(reference_df.columns) & set(current_df.columns)
            if not common_columns:
                return results

            reference_subset = reference_df[list(common_columns)]
            current_subset = current_df[list(common_columns)]

            # 1. Multivariate Kolmogorov-Smirnov Test (Energy Test)
            if SCIPY_AVAILABLE:
                energy_stat = self._energy_test(reference_subset.values, current_subset.values)
                drift_detected = energy_stat > 0.15  # Threshold for multivariate drift
                severity = 'high' if energy_stat > 0.25 else 'medium' if energy_stat > 0.15 else 'low'

                results.append(DriftResult(
                    feature_name="multivariate",
                    drift_detected=drift_detected,
                    drift_score=energy_stat,
                    method="Energy Test",
                    threshold=0.15,
                    severity=severity,
                    description=f"Multivariate energy test statistic: {energy_stat:.4f}",
                    timestamp=timestamp
                ))

            # 2. PCA-based drift detection
            if SCIPY_AVAILABLE and len(common_columns) > 1:
                pca_drift = self._pca_drift_detection(reference_subset, current_subset)
                results.append(DriftResult(
                    feature_name="pca_space",
                    drift_detected=pca_drift['drift_detected'],
                    drift_score=pca_drift['drift_score'],
                    method="PCA Drift",
                    threshold=pca_drift['threshold'],
                    severity=pca_drift['severity'],
                    description=pca_drift['description'],
                    timestamp=timestamp
                ))

            # 3. Domain classifier approach
            domain_drift = self._domain_classifier_drift(reference_subset, current_subset)
            results.append(DriftResult(
                feature_name="domain_classifier",
                drift_detected=domain_drift['drift_detected'],
                drift_score=domain_drift['drift_score'],
                method="Domain Classifier",
                threshold=domain_drift['threshold'],
                severity=domain_drift['severity'],
                description=domain_drift['description'],
                timestamp=timestamp
            ))

        except Exception as e:
            # Fallback to individual feature analysis
            for column in common_columns:
                try:
                    ref_values = reference_df[column].dropna().values
                    cur_values = current_df[column].dropna().values

                    if len(ref_values) > 0 and len(cur_values) > 0:
                        feature_results = self.detect_univariate_drift(
                            ref_values, cur_values, column, "technical_indicators"
                        )
                        results.extend(feature_results)
                except:
                    continue

        return results

    def detect_time_series_drift(self, reference_ts: pd.Series,
                                current_ts: pd.Series,
                                window_size: int = 30) -> List[DriftResult]:
        """
        Detect drift in time series data using rolling windows
        """
        results = []
        timestamp = datetime.now().isoformat()

        if len(reference_ts) < window_size or len(current_ts) < window_size:
            return results

        try:
            # 1. Rolling statistics drift
            ref_rolling_mean = reference_ts.rolling(window=window_size).mean().dropna()
            cur_rolling_mean = current_ts.rolling(window=window_size).mean().dropna()

            if len(ref_rolling_mean) > 0 and len(cur_rolling_mean) > 0:
                mean_drift = self.detect_univariate_drift(
                    ref_rolling_mean.values, cur_rolling_mean.values,
                    "rolling_mean", "technical_indicators"
                )
                results.extend(mean_drift)

            # 2. Volatility drift
            ref_volatility = reference_ts.rolling(window=window_size).std().dropna()
            cur_volatility = current_ts.rolling(window=window_size).std().dropna()

            if len(ref_volatility) > 0 and len(cur_volatility) > 0:
                vol_drift = self.detect_univariate_drift(
                    ref_volatility.values, cur_volatility.values,
                    "rolling_volatility", "technical_indicators"
                )
                results.extend(vol_drift)

            # 3. Autocorrelation drift
            ref_autocorr = self._calculate_autocorrelation(reference_ts, max_lag=10)
            cur_autocorr = self._calculate_autocorrelation(current_ts, max_lag=10)

            if len(ref_autocorr) > 0 and len(cur_autocorr) > 0:
                autocorr_distance = np.linalg.norm(ref_autocorr - cur_autocorr)
                drift_detected = autocorr_distance > 0.3
                severity = 'high' if autocorr_distance > 0.5 else 'medium' if autocorr_distance > 0.3 else 'low'

                results.append(DriftResult(
                    feature_name="autocorrelation",
                    drift_detected=drift_detected,
                    drift_score=autocorr_distance,
                    method="Autocorrelation",
                    threshold=0.3,
                    severity=severity,
                    description=f"Autocorrelation distance: {autocorr_distance:.4f}",
                    timestamp=timestamp
                ))

        except Exception as e:
            pass

        return results

    def detect_indonesian_market_drift(self, reference_data: Dict[str, np.ndarray],
                                     current_data: Dict[str, np.ndarray]) -> List[DriftResult]:
        """
        Detect drift specific to Indonesian market characteristics
        """
        results = []
        timestamp = datetime.now().isoformat()

        # Indonesian market specific features
        market_features = {
            'lq45_composition': 'market_sentiment',
            'rupiah_strength': 'price',
            'jakarta_volume': 'volume',
            'foreign_flow': 'market_sentiment',
            'commodity_correlation': 'technical_indicators'
        }

        for feature_name, feature_type in market_features.items():
            if feature_name in reference_data and feature_name in current_data:
                ref_values = reference_data[feature_name]
                cur_values = current_data[feature_name]

                if len(ref_values) > 0 and len(cur_values) > 0:
                    feature_results = self.detect_univariate_drift(
                        ref_values, cur_values, feature_name, feature_type
                    )
                    results.extend(feature_results)

        # Market regime change detection
        if 'market_regime' in reference_data and 'market_regime' in current_data:
            regime_drift = self._detect_regime_change(
                reference_data['market_regime'],
                current_data['market_regime']
            )
            results.append(regime_drift)

        return results

    def _calculate_psi_detailed(self, reference: np.ndarray, current: np.ndarray,
                               buckets: int = 10) -> float:
        """Calculate Population Stability Index with detailed bucketing"""
        try:
            # Create buckets based on reference distribution
            ref_percentiles = np.percentile(reference, np.linspace(0, 100, buckets + 1))
            ref_percentiles[0] = -np.inf
            ref_percentiles[-1] = np.inf

            # Calculate distributions
            ref_counts, _ = np.histogram(reference, bins=ref_percentiles)
            cur_counts, _ = np.histogram(current, bins=ref_percentiles)

            # Convert to proportions
            ref_props = ref_counts / len(reference)
            cur_props = cur_counts / len(current)

            # Add small epsilon to avoid log(0)
            epsilon = 1e-8
            ref_props = np.maximum(ref_props, epsilon)
            cur_props = np.maximum(cur_props, epsilon)

            # Calculate PSI
            psi = np.sum((cur_props - ref_props) * np.log(cur_props / ref_props))
            return float(psi)

        except Exception as e:
            return 0.0

    def _calculate_jensen_shannon(self, reference: np.ndarray, current: np.ndarray,
                                 bins: int = 20) -> float:
        """Calculate Jensen-Shannon divergence"""
        try:
            # Create common bins
            combined = np.concatenate([reference, current])
            min_val, max_val = np.min(combined), np.max(combined)
            bin_edges = np.linspace(min_val, max_val, bins + 1)

            # Calculate histograms
            ref_hist, _ = np.histogram(reference, bins=bin_edges, density=True)
            cur_hist, _ = np.histogram(current, bins=bin_edges, density=True)

            # Normalize to probabilities
            ref_prob = ref_hist / np.sum(ref_hist)
            cur_prob = cur_hist / np.sum(cur_hist)

            return float(jensenshannon(ref_prob, cur_prob))

        except Exception as e:
            return 0.0

    def _compare_statistical_moments(self, reference: np.ndarray,
                                   current: np.ndarray) -> Dict[str, Any]:
        """Compare statistical moments between distributions"""
        try:
            # Calculate moments
            ref_mean, ref_std = np.mean(reference), np.std(reference)
            cur_mean, cur_std = np.mean(current), np.std(current)

            ref_skew = stats.skew(reference) if SCIPY_AVAILABLE else 0
            cur_skew = stats.skew(current) if SCIPY_AVAILABLE else 0

            ref_kurt = stats.kurtosis(reference) if SCIPY_AVAILABLE else 0
            cur_kurt = stats.kurtosis(current) if SCIPY_AVAILABLE else 0

            # Calculate relative differences
            mean_diff = abs(cur_mean - ref_mean) / (abs(ref_mean) + 1e-8)
            std_diff = abs(cur_std - ref_std) / (ref_std + 1e-8)
            skew_diff = abs(cur_skew - ref_skew) / (abs(ref_skew) + 1e-8)
            kurt_diff = abs(cur_kurt - ref_kurt) / (abs(ref_kurt) + 1e-8)

            # Combined drift score
            drift_score = (mean_diff + std_diff + skew_diff * 0.5 + kurt_diff * 0.5) / 3

            severity = 'high' if drift_score > 0.3 else 'medium' if drift_score > 0.2 else 'low'

            return {
                'drift_score': drift_score,
                'severity': severity,
                'description': f"Mean Δ: {mean_diff:.3f}, Std Δ: {std_diff:.3f}, Skew Δ: {skew_diff:.3f}, Kurt Δ: {kurt_diff:.3f}"
            }

        except Exception as e:
            return {'drift_score': 0.0, 'severity': 'low', 'description': 'Error in calculation'}

    def _simple_drift_detection(self, reference: np.ndarray,
                               current: np.ndarray) -> Dict[str, Any]:
        """Simple fallback drift detection using basic statistics"""
        try:
            ref_mean, ref_std = np.mean(reference), np.std(reference)
            cur_mean, cur_std = np.mean(current), np.std(current)

            # Z-score based comparison
            mean_z = abs(cur_mean - ref_mean) / (ref_std + 1e-8)
            std_ratio = cur_std / (ref_std + 1e-8)

            # Simple drift score
            score = mean_z + abs(np.log(std_ratio))
            threshold = 2.0

            drift_detected = score > threshold
            severity = 'high' if score > 3.0 else 'medium' if score > 2.0 else 'low'

            return {
                'drift_detected': drift_detected,
                'score': score,
                'threshold': threshold,
                'severity': severity,
                'description': f"Mean Z-score: {mean_z:.3f}, Std ratio: {std_ratio:.3f}"
            }

        except Exception as e:
            return {
                'drift_detected': False,
                'score': 0.0,
                'threshold': 2.0,
                'severity': 'low',
                'description': 'Error in simple detection'
            }

    def _energy_test(self, X: np.ndarray, Y: np.ndarray) -> float:
        """Simplified energy test for multivariate drift detection"""
        try:
            # Calculate pairwise distances
            n, m = len(X), len(Y)

            # Sample if datasets are too large
            if n > 1000:
                X = X[np.random.choice(n, 1000, replace=False)]
                n = 1000
            if m > 1000:
                Y = Y[np.random.choice(m, 1000, replace=False)]
                m = 1000

            # Energy statistic approximation
            XX_dist = np.mean([np.linalg.norm(X[i] - X[j]) for i in range(min(n, 50)) for j in range(i+1, min(n, 50))])
            YY_dist = np.mean([np.linalg.norm(Y[i] - Y[j]) for i in range(min(m, 50)) for j in range(i+1, min(m, 50))])
            XY_dist = np.mean([np.linalg.norm(X[i] - Y[j]) for i in range(min(n, 50)) for j in range(min(m, 50))])

            energy_stat = 2 * XY_dist - XX_dist - YY_dist
            return float(energy_stat)

        except Exception as e:
            return 0.0

    def _pca_drift_detection(self, reference_df: pd.DataFrame,
                           current_df: pd.DataFrame) -> Dict[str, Any]:
        """PCA-based drift detection"""
        try:
            if not SCIPY_AVAILABLE:
                return {'drift_detected': False, 'drift_score': 0.0, 'threshold': 0.0, 'severity': 'low', 'description': 'PCA not available'}

            # Fit PCA on reference data
            pca = PCA(n_components=min(3, reference_df.shape[1]))
            reference_scaled = self.scaler.fit_transform(reference_df)
            reference_pca = pca.fit_transform(reference_scaled)

            # Transform current data
            current_scaled = self.scaler.transform(current_df)
            current_pca = pca.transform(current_scaled)

            # Compare PCA distributions
            drift_scores = []
            for i in range(pca.n_components_):
                ref_comp = reference_pca[:, i]
                cur_comp = current_pca[:, i]

                if SCIPY_AVAILABLE:
                    ks_stat, _ = stats.ks_2samp(ref_comp, cur_comp)
                    drift_scores.append(ks_stat)

            avg_drift_score = np.mean(drift_scores) if drift_scores else 0.0
            threshold = 0.2
            drift_detected = avg_drift_score > threshold
            severity = 'high' if avg_drift_score > 0.3 else 'medium' if avg_drift_score > 0.2 else 'low'

            return {
                'drift_detected': drift_detected,
                'drift_score': avg_drift_score,
                'threshold': threshold,
                'severity': severity,
                'description': f"PCA component drift scores: {drift_scores}"
            }

        except Exception as e:
            return {'drift_detected': False, 'drift_score': 0.0, 'threshold': 0.0, 'severity': 'low', 'description': f'PCA error: {str(e)}'}

    def _domain_classifier_drift(self, reference_df: pd.DataFrame,
                               current_df: pd.DataFrame) -> Dict[str, Any]:
        """Domain classifier approach to drift detection"""
        try:
            # Create labels (0 for reference, 1 for current)
            ref_labels = np.zeros(len(reference_df))
            cur_labels = np.ones(len(current_df))

            # Combine data
            combined_data = pd.concat([reference_df, current_df], ignore_index=True)
            combined_labels = np.concatenate([ref_labels, cur_labels])

            # Simple domain classifier using statistical separation
            feature_scores = []
            for column in combined_data.columns:
                ref_values = reference_df[column].values
                cur_values = current_df[column].values

                # Use t-test as simple classifier
                if SCIPY_AVAILABLE:
                    t_stat, p_value = stats.ttest_ind(ref_values, cur_values)
                    feature_scores.append(abs(t_stat))
                else:
                    # Fallback to mean difference
                    mean_diff = abs(np.mean(cur_values) - np.mean(ref_values))
                    feature_scores.append(mean_diff)

            # Aggregate score
            if feature_scores:
                domain_score = np.mean(feature_scores)
                # Normalize (rough approximation)
                domain_score = min(domain_score / 10.0, 1.0)
            else:
                domain_score = 0.0

            threshold = 0.3
            drift_detected = domain_score > threshold
            severity = 'high' if domain_score > 0.5 else 'medium' if domain_score > 0.3 else 'low'

            return {
                'drift_detected': drift_detected,
                'drift_score': domain_score,
                'threshold': threshold,
                'severity': severity,
                'description': f"Domain classifier score: {domain_score:.4f}"
            }

        except Exception as e:
            return {'drift_detected': False, 'drift_score': 0.0, 'threshold': 0.0, 'severity': 'low', 'description': f'Domain classifier error: {str(e)}'}

    def _calculate_autocorrelation(self, ts: pd.Series, max_lag: int = 10) -> np.ndarray:
        """Calculate autocorrelation function"""
        try:
            autocorr = []
            for lag in range(1, max_lag + 1):
                if len(ts) > lag:
                    corr = ts.autocorr(lag=lag)
                    autocorr.append(corr if not np.isnan(corr) else 0.0)
            return np.array(autocorr)
        except Exception as e:
            return np.zeros(max_lag)

    def _detect_regime_change(self, reference_regime: np.ndarray,
                            current_regime: np.ndarray) -> DriftResult:
        """Detect market regime changes"""
        try:
            # Simple regime change detection using mode comparison
            ref_mode = stats.mode(reference_regime)[0] if SCIPY_AVAILABLE else np.bincount(reference_regime.astype(int)).argmax()
            cur_mode = stats.mode(current_regime)[0] if SCIPY_AVAILABLE else np.bincount(current_regime.astype(int)).argmax()

            regime_changed = ref_mode != cur_mode

            # Calculate regime distribution distance
            ref_unique, ref_counts = np.unique(reference_regime, return_counts=True)
            cur_unique, cur_counts = np.unique(current_regime, return_counts=True)

            # Create common regime space
            all_regimes = np.union1d(ref_unique, cur_unique)
            ref_dist = np.array([ref_counts[ref_unique == r][0] if r in ref_unique else 0 for r in all_regimes])
            cur_dist = np.array([cur_counts[cur_unique == r][0] if r in cur_unique else 0 for r in all_regimes])

            # Normalize
            ref_dist = ref_dist / ref_dist.sum()
            cur_dist = cur_dist / cur_dist.sum()

            # Calculate distance
            regime_distance = np.sum(np.abs(ref_dist - cur_dist)) / 2  # Total variation distance

            severity = 'critical' if regime_changed else 'high' if regime_distance > 0.3 else 'medium' if regime_distance > 0.2 else 'low'

            return DriftResult(
                feature_name="market_regime",
                drift_detected=regime_changed or regime_distance > 0.3,
                drift_score=regime_distance,
                method="Regime Change",
                threshold=0.3,
                severity=severity,
                description=f"Regime change: {regime_changed}, Distance: {regime_distance:.4f}",
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            return DriftResult(
                feature_name="market_regime",
                drift_detected=False,
                drift_score=0.0,
                method="Regime Change",
                threshold=0.3,
                severity='low',
                description=f"Error in regime detection: {str(e)}",
                timestamp=datetime.now().isoformat()
            )

    def _determine_severity(self, score: float, thresholds: Dict[str, float]) -> str:
        """Determine severity level based on score and thresholds"""
        if score > thresholds.get('high', 0.3):
            return 'critical'
        elif score > thresholds.get('medium', 0.2):
            return 'high'
        elif score > thresholds.get('low', 0.1):
            return 'medium'
        else:
            return 'low'

# Example usage
if __name__ == "__main__":
    # Create sample Indonesian market data
    np.random.seed(42)

    # Reference data (normal market conditions)
    reference_data = {
        'lq45_return': np.random.normal(0.001, 0.02, 1000),
        'rupiah_strength': np.random.normal(14500, 100, 1000),
        'jakarta_volume': np.random.exponential(1e9, 1000),
        'foreign_flow': np.random.normal(0, 1e8, 1000)
    }

    # Current data (with some drift)
    current_data = {
        'lq45_return': np.random.normal(0.003, 0.025, 500),  # Mean shift
        'rupiah_strength': np.random.normal(14600, 120, 500),  # Mean and variance shift
        'jakarta_volume': np.random.exponential(1.2e9, 500),  # Distribution shift
        'foreign_flow': np.random.normal(-0.5e8, 1.2e8, 500)  # Mean and variance shift
    }

    detector = AdvancedDriftDetector()

    print("Indonesian Market Drift Detection Results:")
    print("=" * 50)

    # Detect drift for each feature
    for feature_name in reference_data.keys():
        results = detector.detect_univariate_drift(
            reference_data[feature_name],
            current_data[feature_name],
            feature_name,
            "technical_indicators"
        )

        print(f"\n{feature_name.upper()}:")
        for result in results:
            status = "🔴 DRIFT DETECTED" if result.drift_detected else "🟢 NO DRIFT"
            print(f"  {result.method}: {status} ({result.severity}) - {result.description}")

    # Test multivariate drift
    ref_df = pd.DataFrame(reference_data)
    cur_df = pd.DataFrame(current_data)

    multivar_results = detector.detect_multivariate_drift(ref_df, cur_df)

    print(f"\nMULTIVARIATE ANALYSIS:")
    for result in multivar_results:
        status = "🔴 DRIFT DETECTED" if result.drift_detected else "🟢 NO DRIFT"
        print(f"  {result.method}: {status} ({result.severity}) - {result.description}")