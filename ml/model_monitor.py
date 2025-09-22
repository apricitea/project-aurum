"""
Model monitoring and drift detection system for Project Aurum
Monitors ML model performance and detects data/concept drift
"""

import numpy as np
import pandas as pd
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle
from scipy import stats
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    timestamp: str
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    prediction_count: int
    correct_predictions: int
    drift_score: Optional[float] = None
    alert_triggered: bool = False

@dataclass
class DriftAlert:
    """Data/concept drift alert"""
    timestamp: str
    model_name: str
    drift_type: str  # 'data_drift', 'concept_drift', 'performance_drift'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    metrics: Dict[str, float]
    recommended_action: str

class ModelMonitor:
    """
    Comprehensive model monitoring system for Indonesian stock market models
    """

    def __init__(self, db_path: str = "data/model_monitoring.db"):
        """Initialize model monitor"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)

        # Performance thresholds for Indonesian market
        self.performance_thresholds = {
            'accuracy_min': 0.65,  # Minimum acceptable accuracy for IDX predictions
            'accuracy_degradation': 0.10,  # 10% degradation triggers alert
            'f1_min': 0.60,  # Minimum F1 score
            'prediction_confidence_min': 0.55,  # Minimum prediction confidence
        }

        # Drift detection parameters
        self.drift_thresholds = {
            'ks_test_pvalue': 0.05,  # Kolmogorov-Smirnov test p-value
            'psi_threshold': 0.2,  # Population Stability Index threshold
            'performance_degradation': 0.15,  # Performance degradation threshold
        }

        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for monitoring data"""
        with sqlite3.connect(self.db_path) as conn:
            # Model metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    accuracy REAL NOT NULL,
                    precision_score REAL NOT NULL,
                    recall_score REAL NOT NULL,
                    f1_score REAL NOT NULL,
                    prediction_count INTEGER NOT NULL,
                    correct_predictions INTEGER NOT NULL,
                    drift_score REAL,
                    alert_triggered BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Drift alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS drift_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    drift_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metrics TEXT NOT NULL,  -- JSON serialized metrics
                    recommended_action TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Reference data statistics table (for drift detection)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reference_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    feature_name TEXT NOT NULL,
                    mean_value REAL,
                    std_value REAL,
                    min_value REAL,
                    max_value REAL,
                    distribution_params TEXT,  -- JSON serialized distribution parameters
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(model_name, feature_name)
                )
            """)

            # Model predictions log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    predicted_signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    actual_signal TEXT,  -- Will be updated when actual outcome is known
                    features TEXT NOT NULL,  -- JSON serialized feature values
                    market_conditions TEXT,  -- JSON serialized market context
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def log_prediction(self, model_name: str, stock_code: str,
                      predicted_signal: str, confidence: float,
                      features: Dict[str, float],
                      market_conditions: Optional[Dict[str, Any]] = None):
        """Log model prediction for later evaluation"""
        timestamp = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO predictions_log
                (timestamp, model_name, stock_code, predicted_signal, confidence, features, market_conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, model_name, stock_code, predicted_signal, confidence,
                json.dumps(features), json.dumps(market_conditions or {})
            ))
            conn.commit()

        logger.info(f"Logged prediction for {model_name}: {stock_code} -> {predicted_signal} ({confidence:.3f})")

    def update_actual_outcome(self, prediction_id: int, actual_signal: str):
        """Update prediction with actual outcome"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE predictions_log
                SET actual_signal = ?
                WHERE id = ?
            """, (actual_signal, prediction_id))
            conn.commit()

    def calculate_model_performance(self, model_name: str,
                                  days_back: int = 7) -> Optional[ModelMetrics]:
        """Calculate model performance metrics over specified period"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Get predictions with actual outcomes
            df = pd.read_sql_query("""
                SELECT predicted_signal, actual_signal, confidence
                FROM predictions_log
                WHERE model_name = ? AND timestamp >= ? AND actual_signal IS NOT NULL
            """, conn, params=(model_name, cutoff_date))

        if df.empty:
            logger.warning(f"No predictions with outcomes found for {model_name} in last {days_back} days")
            return None

        # Calculate metrics
        y_true = df['actual_signal'].values
        y_pred = df['predicted_signal'].values

        try:
            accuracy = accuracy_score(y_true, y_pred)
            precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)

            metrics = ModelMetrics(
                timestamp=datetime.now().isoformat(),
                model_name=model_name,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                prediction_count=len(df),
                correct_predictions=int((y_true == y_pred).sum())
            )

            # Check for performance degradation
            alert_triggered = self._check_performance_degradation(metrics)
            metrics.alert_triggered = alert_triggered

            # Store metrics
            self._store_metrics(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics for {model_name}: {e}")
            return None

    def detect_data_drift(self, model_name: str,
                         current_features: Dict[str, float]) -> List[DriftAlert]:
        """Detect data drift using statistical tests"""
        alerts = []

        try:
            # Get reference statistics
            reference_stats = self._get_reference_stats(model_name)
            if not reference_stats:
                logger.warning(f"No reference statistics found for {model_name}")
                return alerts

            # Get recent feature values for comparison
            recent_features = self._get_recent_features(model_name, days_back=30)

            for feature_name, current_value in current_features.items():
                if feature_name not in reference_stats:
                    continue

                ref_stats = reference_stats[feature_name]
                recent_values = recent_features.get(feature_name, [])

                if len(recent_values) < 10:  # Need sufficient data for comparison
                    continue

                # Calculate Population Stability Index (PSI)
                psi_score = self._calculate_psi(ref_stats, recent_values)

                # Perform Kolmogorov-Smirnov test
                ks_statistic, ks_pvalue = stats.ks_2samp(ref_stats['historical_values'], recent_values)

                # Check for drift
                if psi_score > self.drift_thresholds['psi_threshold']:
                    severity = 'high' if psi_score > 0.5 else 'medium'
                    alerts.append(DriftAlert(
                        timestamp=datetime.now().isoformat(),
                        model_name=model_name,
                        drift_type='data_drift',
                        severity=severity,
                        description=f"Data drift detected in feature '{feature_name}' (PSI: {psi_score:.3f})",
                        metrics={'psi_score': psi_score, 'ks_statistic': ks_statistic, 'ks_pvalue': ks_pvalue},
                        recommended_action=f"Investigate feature '{feature_name}' and consider model retraining"
                    ))

                if ks_pvalue < self.drift_thresholds['ks_test_pvalue']:
                    severity = 'high' if ks_pvalue < 0.01 else 'medium'
                    alerts.append(DriftAlert(
                        timestamp=datetime.now().isoformat(),
                        model_name=model_name,
                        drift_type='data_drift',
                        severity=severity,
                        description=f"Statistical drift detected in feature '{feature_name}' (KS p-value: {ks_pvalue:.4f})",
                        metrics={'ks_statistic': ks_statistic, 'ks_pvalue': ks_pvalue, 'psi_score': psi_score},
                        recommended_action=f"Statistical distribution has changed for '{feature_name}' - model retraining recommended"
                    ))

            # Store alerts
            for alert in alerts:
                self._store_alert(alert)

            return alerts

        except Exception as e:
            logger.error(f"Error detecting data drift for {model_name}: {e}")
            return []

    def detect_concept_drift(self, model_name: str) -> List[DriftAlert]:
        """Detect concept drift based on performance degradation patterns"""
        alerts = []

        try:
            # Get performance metrics over time
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("""
                    SELECT timestamp, accuracy, f1_score
                    FROM model_metrics
                    WHERE model_name = ?
                    ORDER BY timestamp DESC
                    LIMIT 30
                """, conn, params=(model_name,))

            if len(df) < 5:  # Need sufficient history
                return alerts

            # Calculate trends
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')

            # Check for declining performance trend
            accuracy_trend = self._calculate_trend(df['accuracy'].values)
            f1_trend = self._calculate_trend(df['f1_score'].values)

            # Check for sudden performance drops
            recent_accuracy = df['accuracy'].tail(5).mean()
            historical_accuracy = df['accuracy'].head(10).mean() if len(df) >= 15 else df['accuracy'].mean()

            accuracy_degradation = (historical_accuracy - recent_accuracy) / historical_accuracy

            if accuracy_degradation > self.drift_thresholds['performance_degradation']:
                severity = 'critical' if accuracy_degradation > 0.25 else 'high'
                alerts.append(DriftAlert(
                    timestamp=datetime.now().isoformat(),
                    model_name=model_name,
                    drift_type='concept_drift',
                    severity=severity,
                    description=f"Concept drift detected - accuracy degraded by {accuracy_degradation:.1%}",
                    metrics={
                        'accuracy_degradation': accuracy_degradation,
                        'recent_accuracy': recent_accuracy,
                        'historical_accuracy': historical_accuracy,
                        'accuracy_trend': accuracy_trend,
                        'f1_trend': f1_trend
                    },
                    recommended_action="Immediate model retraining recommended - concept drift detected"
                ))

            # Check for negative trends
            if accuracy_trend < -0.1 or f1_trend < -0.1:
                alerts.append(DriftAlert(
                    timestamp=datetime.now().isoformat(),
                    model_name=model_name,
                    drift_type='concept_drift',
                    severity='medium',
                    description=f"Declining performance trend detected (accuracy trend: {accuracy_trend:.3f})",
                    metrics={'accuracy_trend': accuracy_trend, 'f1_trend': f1_trend},
                    recommended_action="Monitor closely - consider model retraining if trend continues"
                ))

            # Store alerts
            for alert in alerts:
                self._store_alert(alert)

            return alerts

        except Exception as e:
            logger.error(f"Error detecting concept drift for {model_name}: {e}")
            return []

    def update_reference_statistics(self, model_name: str,
                                   training_data: pd.DataFrame):
        """Update reference statistics for drift detection"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for column in training_data.select_dtypes(include=[np.number]).columns:
                    values = training_data[column].dropna().values

                    # Calculate statistics
                    mean_val = float(np.mean(values))
                    std_val = float(np.std(values))
                    min_val = float(np.min(values))
                    max_val = float(np.max(values))

                    # Store distribution parameters
                    dist_params = {
                        'mean': mean_val,
                        'std': std_val,
                        'quantiles': np.quantile(values, [0.1, 0.25, 0.5, 0.75, 0.9]).tolist(),
                        'historical_values': values.tolist()[:1000]  # Store sample for comparison
                    }

                    # Insert or update
                    conn.execute("""
                        INSERT OR REPLACE INTO reference_stats
                        (model_name, feature_name, mean_value, std_value, min_value, max_value, distribution_params)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        model_name, column, mean_val, std_val, min_val, max_val,
                        json.dumps(dist_params)
                    ))

                conn.commit()
                logger.info(f"Updated reference statistics for {model_name}")

        except Exception as e:
            logger.error(f"Error updating reference statistics: {e}")

    def generate_monitoring_report(self, model_name: str,
                                 days_back: int = 30) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        report = {
            'model_name': model_name,
            'report_date': datetime.now().isoformat(),
            'period_days': days_back,
            'performance_metrics': {},
            'drift_alerts': [],
            'recommendations': [],
            'status': 'healthy'
        }

        try:
            # Get recent performance metrics
            metrics = self.calculate_model_performance(model_name, days_back)
            if metrics:
                report['performance_metrics'] = asdict(metrics)

            # Get recent alerts
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                alerts_df = pd.read_sql_query("""
                    SELECT * FROM drift_alerts
                    WHERE model_name = ? AND timestamp >= ? AND resolved = FALSE
                    ORDER BY timestamp DESC
                """, conn, params=(model_name, cutoff_date))

            report['drift_alerts'] = alerts_df.to_dict('records')

            # Determine overall status and recommendations
            critical_alerts = alerts_df[alerts_df['severity'] == 'critical']
            high_alerts = alerts_df[alerts_df['severity'] == 'high']

            if len(critical_alerts) > 0:
                report['status'] = 'critical'
                report['recommendations'].append("URGENT: Critical drift detected - immediate model retraining required")
            elif len(high_alerts) > 0:
                report['status'] = 'warning'
                report['recommendations'].append("High-priority drift detected - schedule model retraining soon")
            elif metrics and metrics.accuracy < self.performance_thresholds['accuracy_min']:
                report['status'] = 'degraded'
                report['recommendations'].append("Performance below threshold - investigate and consider retraining")

            # Indonesian market specific recommendations
            if metrics and metrics.prediction_count < 50:
                report['recommendations'].append("Low prediction volume - ensure sufficient Indonesian market data coverage")

            return report

        except Exception as e:
            logger.error(f"Error generating monitoring report: {e}")
            report['status'] = 'error'
            report['error'] = str(e)
            return report

    def _check_performance_degradation(self, current_metrics: ModelMetrics) -> bool:
        """Check if current performance indicates degradation"""
        try:
            # Get historical baseline
            with sqlite3.connect(self.db_path) as conn:
                historical_df = pd.read_sql_query("""
                    SELECT accuracy, f1_score
                    FROM model_metrics
                    WHERE model_name = ?
                    ORDER BY timestamp DESC
                    LIMIT 10 OFFSET 1
                """, conn, params=(current_metrics.model_name,))

            if historical_df.empty:
                return False

            baseline_accuracy = historical_df['accuracy'].mean()
            baseline_f1 = historical_df['f1_score'].mean()

            accuracy_degradation = (baseline_accuracy - current_metrics.accuracy) / baseline_accuracy
            f1_degradation = (baseline_f1 - current_metrics.f1_score) / baseline_f1

            return (accuracy_degradation > self.performance_thresholds['accuracy_degradation'] or
                   f1_degradation > self.performance_thresholds['accuracy_degradation'])

        except Exception as e:
            logger.error(f"Error checking performance degradation: {e}")
            return False

    def _get_reference_stats(self, model_name: str) -> Dict[str, Dict]:
        """Get reference statistics for drift detection"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("""
                    SELECT feature_name, distribution_params
                    FROM reference_stats
                    WHERE model_name = ?
                """, conn, params=(model_name,))

            stats = {}
            for _, row in df.iterrows():
                stats[row['feature_name']] = json.loads(row['distribution_params'])

            return stats

        except Exception as e:
            logger.error(f"Error getting reference stats: {e}")
            return {}

    def _get_recent_features(self, model_name: str, days_back: int = 30) -> Dict[str, List[float]]:
        """Get recent feature values for drift comparison"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("""
                    SELECT features
                    FROM predictions_log
                    WHERE model_name = ? AND timestamp >= ?
                """, conn, params=(model_name, cutoff_date))

            if df.empty:
                return {}

            # Aggregate feature values
            feature_values = {}
            for _, row in df.iterrows():
                features = json.loads(row['features'])
                for feature_name, value in features.items():
                    if feature_name not in feature_values:
                        feature_values[feature_name] = []
                    feature_values[feature_name].append(value)

            return feature_values

        except Exception as e:
            logger.error(f"Error getting recent features: {e}")
            return {}

    def _calculate_psi(self, reference_stats: Dict, current_values: List[float]) -> float:
        """Calculate Population Stability Index"""
        try:
            if not current_values:
                return 0.0

            # Get reference quantiles
            ref_quantiles = reference_stats.get('quantiles', [])
            if len(ref_quantiles) < 5:
                return 0.0

            # Create bins based on reference quantiles
            bins = [-np.inf] + ref_quantiles + [np.inf]

            # Calculate distributions
            ref_dist = np.array([0.1, 0.15, 0.25, 0.25, 0.15, 0.1])  # Expected distribution
            current_hist, _ = np.histogram(current_values, bins=bins, density=True)
            current_dist = current_hist / current_hist.sum()

            # Add small epsilon to avoid log(0)
            epsilon = 1e-8
            ref_dist = np.maximum(ref_dist, epsilon)
            current_dist = np.maximum(current_dist, epsilon)

            # Calculate PSI
            psi = np.sum((current_dist - ref_dist) * np.log(current_dist / ref_dist))

            return float(psi)

        except Exception as e:
            logger.error(f"Error calculating PSI: {e}")
            return 0.0

    def _calculate_trend(self, values: np.ndarray) -> float:
        """Calculate trend using linear regression slope"""
        try:
            if len(values) < 2:
                return 0.0

            x = np.arange(len(values))
            slope, _ = np.polyfit(x, values, 1)
            return float(slope)

        except Exception as e:
            logger.error(f"Error calculating trend: {e}")
            return 0.0

    def _store_metrics(self, metrics: ModelMetrics):
        """Store performance metrics in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO model_metrics
                    (timestamp, model_name, accuracy, precision_score, recall_score, f1_score,
                     prediction_count, correct_predictions, drift_score, alert_triggered)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp, metrics.model_name, metrics.accuracy,
                    metrics.precision, metrics.recall, metrics.f1_score,
                    metrics.prediction_count, metrics.correct_predictions,
                    metrics.drift_score, metrics.alert_triggered
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error storing metrics: {e}")

    def _store_alert(self, alert: DriftAlert):
        """Store drift alert in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO drift_alerts
                    (timestamp, model_name, drift_type, severity, description, metrics, recommended_action)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.timestamp, alert.model_name, alert.drift_type,
                    alert.severity, alert.description, json.dumps(alert.metrics),
                    alert.recommended_action
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error storing alert: {e}")

# CLI interface for model monitoring
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Model Monitoring System for Project Aurum")
    parser.add_argument("--model", required=True, help="Model name to monitor")
    parser.add_argument("--action", choices=['performance', 'drift', 'report'],
                       default='report', help="Monitoring action to perform")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze")

    args = parser.parse_args()

    monitor = ModelMonitor()

    if args.action == 'performance':
        metrics = monitor.calculate_model_performance(args.model, args.days)
        if metrics:
            print(f"Performance Metrics for {args.model}:")
            print(f"  Accuracy: {metrics.accuracy:.3f}")
            print(f"  F1 Score: {metrics.f1_score:.3f}")
            print(f"  Predictions: {metrics.prediction_count}")
            print(f"  Alert Triggered: {metrics.alert_triggered}")

    elif args.action == 'drift':
        # Example drift detection (would need actual feature data)
        example_features = {
            'rsi': 65.5,
            'macd': 0.15,
            'volume_ratio': 1.2,
            'price_change': 0.03
        }
        alerts = monitor.detect_data_drift(args.model, example_features)
        concept_alerts = monitor.detect_concept_drift(args.model)

        all_alerts = alerts + concept_alerts
        if all_alerts:
            print(f"Drift Alerts for {args.model}:")
            for alert in all_alerts:
                print(f"  {alert.severity.upper()}: {alert.description}")
        else:
            print(f"No drift detected for {args.model}")

    elif args.action == 'report':
        report = monitor.generate_monitoring_report(args.model, args.days)
        print(f"Monitoring Report for {args.model}")
        print(f"Status: {report['status'].upper()}")

        if report.get('performance_metrics'):
            pm = report['performance_metrics']
            print(f"Performance: Accuracy={pm.get('accuracy', 0):.3f}, F1={pm.get('f1_score', 0):.3f}")

        if report['drift_alerts']:
            print(f"Active Alerts: {len(report['drift_alerts'])}")

        if report['recommendations']:
            print("Recommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")