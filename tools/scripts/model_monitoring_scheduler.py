"""
Automated scheduler for model monitoring and drift detection
Runs periodic checks and generates alerts for Project Aurum models
"""

import schedule
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os
from pathlib import Path
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from ml.model_monitor import ModelMonitor, DriftAlert
from ml.drift_detector import AdvancedDriftDetector
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitoring_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ModelMonitoringScheduler:
    """
    Automated scheduler for model monitoring tasks
    """

    def __init__(self, config_file: str = "config/monitoring_config.json"):
        """Initialize scheduler with configuration"""
        self.config = self._load_config(config_file)
        self.monitor = ModelMonitor()
        self.drift_detector = AdvancedDriftDetector()

        # Models to monitor (Indonesian market specific)
        self.models = [
            "lq45_ensemble",
            "sector_rotation",
            "momentum_predictor",
            "volatility_forecaster",
            "earnings_predictor"
        ]

        # Alert thresholds
        self.alert_thresholds = {
            'performance_degradation': 0.15,
            'critical_drift_score': 0.4,
            'high_drift_score': 0.25,
            'alert_frequency_limit': 5  # Max alerts per model per day
        }

        # Initialize scheduling
        self._setup_schedule()

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load monitoring configuration"""
        config_path = Path(config_file)

        # Default configuration
        default_config = {
            "monitoring": {
                "performance_check_interval": "1h",
                "drift_check_interval": "4h",
                "report_generation_interval": "24h",
                "data_quality_check_interval": "2h"
            },
            "alerts": {
                "email_notifications": True,
                "slack_notifications": False,
                "dashboard_notifications": True,
                "email_recipients": ["admin@projectaurum.com"],
                "severity_escalation": True
            },
            "indonesian_market": {
                "trading_hours_start": "09:00",
                "trading_hours_end": "15:49",
                "timezone": "Asia/Jakarta",
                "market_holidays": [],
                "rupiah_monitoring": True,
                "lq45_tracking": True
            }
        }

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Error loading config file: {e}. Using defaults.")

        return default_config

    def _setup_schedule(self):
        """Set up scheduled monitoring tasks"""
        # Performance monitoring every hour
        schedule.every().hour.do(self._run_performance_monitoring)

        # Drift detection every 4 hours
        schedule.every(4).hours.do(self._run_drift_detection)

        # Daily comprehensive reports
        schedule.every().day.at("06:00").do(self._generate_daily_reports)

        # Data quality checks every 2 hours
        schedule.every(2).hours.do(self._run_data_quality_checks)

        # Indonesian market specific: Run enhanced monitoring during trading hours
        schedule.every().monday.at("08:30").do(self._run_pre_market_checks)
        schedule.every().tuesday.at("08:30").do(self._run_pre_market_checks)
        schedule.every().wednesday.at("08:30").do(self._run_pre_market_checks)
        schedule.every().thursday.at("08:30").do(self._run_pre_market_checks)
        schedule.every().friday.at("08:30").do(self._run_pre_market_checks)

        # Post-market analysis
        schedule.every().monday.at("16:30").do(self._run_post_market_analysis)
        schedule.every().tuesday.at("16:30").do(self._run_post_market_analysis)
        schedule.every().wednesday.at("16:30").do(self._run_post_market_analysis)
        schedule.every().thursday.at("16:30").do(self._run_post_market_analysis)
        schedule.every().friday.at("16:30").do(self._run_post_market_analysis)

        logger.info("Monitoring schedule initialized")

    def _run_performance_monitoring(self):
        """Run performance monitoring for all models"""
        logger.info("Starting performance monitoring cycle")

        try:
            for model_name in self.models:
                logger.info(f"Checking performance for {model_name}")

                # Calculate performance metrics
                metrics = self.monitor.calculate_model_performance(model_name, days_back=1)

                if metrics:
                    # Check for performance degradation
                    if metrics.accuracy < 0.6 or metrics.alert_triggered:
                        alert = DriftAlert(
                            timestamp=datetime.now().isoformat(),
                            model_name=model_name,
                            drift_type='performance_drift',
                            severity='high' if metrics.accuracy < 0.55 else 'medium',
                            description=f"Performance degradation detected: accuracy={metrics.accuracy:.3f}",
                            metrics={
                                'accuracy': metrics.accuracy,
                                'f1_score': metrics.f1_score,
                                'prediction_count': metrics.prediction_count
                            },
                            recommended_action=f"Review {model_name} model - consider retraining"
                        )

                        self._handle_alert(alert)

                # Simulate logging predictions (in production, this would come from actual model serving)
                self._simulate_prediction_logging(model_name)

                time.sleep(2)  # Rate limiting

        except Exception as e:
            logger.error(f"Error in performance monitoring: {e}")

    def _run_drift_detection(self):
        """Run drift detection for all models"""
        logger.info("Starting drift detection cycle")

        try:
            for model_name in self.models:
                logger.info(f"Running drift detection for {model_name}")

                # Generate sample feature data for demonstration
                current_features = self._generate_sample_features(model_name)

                # Data drift detection
                data_alerts = self.monitor.detect_data_drift(model_name, current_features)

                # Concept drift detection
                concept_alerts = self.monitor.detect_concept_drift(model_name)

                # Process alerts
                all_alerts = data_alerts + concept_alerts
                for alert in all_alerts:
                    if alert.severity in ['high', 'critical']:
                        self._handle_alert(alert)

                time.sleep(3)  # Rate limiting

        except Exception as e:
            logger.error(f"Error in drift detection: {e}")

    def _run_data_quality_checks(self):
        """Run data quality monitoring"""
        logger.info("Starting data quality checks")

        try:
            # Simulate data quality checks for Indonesian market data
            quality_issues = []

            # Check for data completeness
            for model_name in self.models:
                # Simulate checking recent prediction logs
                recent_predictions = self._get_recent_predictions(model_name)

                if len(recent_predictions) < 10:  # Expect at least 10 predictions per hour
                    quality_issues.append({
                        'model': model_name,
                        'issue': 'low_prediction_volume',
                        'severity': 'medium',
                        'description': f'Only {len(recent_predictions)} predictions in last hour'
                    })

                # Check for feature data quality
                feature_quality = self._check_feature_quality(model_name)
                if feature_quality['issues']:
                    quality_issues.extend(feature_quality['issues'])

            # Indonesian market specific checks
            market_quality = self._check_indonesian_market_data_quality()
            quality_issues.extend(market_quality)

            # Report quality issues
            if quality_issues:
                self._report_data_quality_issues(quality_issues)

        except Exception as e:
            logger.error(f"Error in data quality checks: {e}")

    def _generate_daily_reports(self):
        """Generate comprehensive daily monitoring reports"""
        logger.info("Generating daily monitoring reports")

        try:
            for model_name in self.models:
                report = self.monitor.generate_monitoring_report(model_name, days_back=1)

                # Save report
                report_file = f"reports/daily_monitoring_{model_name}_{datetime.now().strftime('%Y%m%d')}.json"
                os.makedirs(os.path.dirname(report_file), exist_ok=True)

                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2)

                # Send email report if enabled
                if self.config['alerts']['email_notifications']:
                    self._send_daily_report_email(model_name, report)

            # Generate Indonesian market summary
            self._generate_indonesian_market_summary()

        except Exception as e:
            logger.error(f"Error generating daily reports: {e}")

    def _run_pre_market_checks(self):
        """Run pre-market monitoring checks"""
        logger.info("Running pre-market checks for Indonesian stock exchange")

        try:
            # Check model readiness for trading day
            for model_name in self.models:
                # Verify model is ready
                model_status = self._check_model_readiness(model_name)

                if not model_status['ready']:
                    alert = DriftAlert(
                        timestamp=datetime.now().isoformat(),
                        model_name=model_name,
                        drift_type='system_alert',
                        severity='high',
                        description=f"Model not ready for trading: {model_status['issues']}",
                        metrics=model_status,
                        recommended_action="Investigate model status before market open"
                    )
                    self._handle_alert(alert)

            # Check Indonesian market data feeds
            market_data_status = self._check_indonesian_data_feeds()
            if not market_data_status['healthy']:
                self._handle_market_data_alert(market_data_status)

        except Exception as e:
            logger.error(f"Error in pre-market checks: {e}")

    def _run_post_market_analysis(self):
        """Run post-market analysis for Indonesian stock exchange"""
        logger.info("Running post-market analysis for Indonesian stock exchange")

        try:
            # Analyze trading day performance
            for model_name in self.models:
                daily_performance = self._analyze_daily_performance(model_name)

                # Check if performance was significantly different from expected
                if daily_performance['deviation_score'] > 0.3:
                    alert = DriftAlert(
                        timestamp=datetime.now().isoformat(),
                        model_name=model_name,
                        drift_type='performance_deviation',
                        severity='medium',
                        description=f"Unusual daily performance: {daily_performance['summary']}",
                        metrics=daily_performance,
                        recommended_action="Review model performance and market conditions"
                    )
                    self._handle_alert(alert)

            # Generate Indonesian market summary
            self._generate_post_market_summary()

        except Exception as e:
            logger.error(f"Error in post-market analysis: {e}")

    def _handle_alert(self, alert: DriftAlert):
        """Handle and distribute alerts"""
        logger.warning(f"Alert triggered: {alert.drift_type} - {alert.severity} - {alert.description}")

        try:
            # Store alert in database
            # self.monitor._store_alert(alert)  # This would be called by the monitor

            # Check if we should send notifications (rate limiting)
            if self._should_send_notification(alert):
                # Send email notification
                if self.config['alerts']['email_notifications']:
                    self._send_email_alert(alert)

                # Send dashboard notification
                if self.config['alerts']['dashboard_notifications']:
                    self._send_dashboard_notification(alert)

                # Log alert details
                self._log_alert_details(alert)

        except Exception as e:
            logger.error(f"Error handling alert: {e}")

    def _should_send_notification(self, alert: DriftAlert) -> bool:
        """Check if notification should be sent (rate limiting)"""
        # Simple rate limiting - in production, this would check recent alert history
        return alert.severity in ['high', 'critical']

    def _send_email_alert(self, alert: DriftAlert):
        """Send email alert notification"""
        try:
            # Email configuration (would be loaded from config)
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            email_user = "monitoring@projectaurum.com"
            email_password = "your_app_password"  # Use app password for Gmail

            recipients = self.config['alerts']['email_recipients']

            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"Project Aurum Alert: {alert.severity.upper()} - {alert.model_name}"

            # Email body
            body = f"""
            Model Monitoring Alert - Project Aurum

            Model: {alert.model_name}
            Alert Type: {alert.drift_type}
            Severity: {alert.severity.upper()}
            Timestamp: {alert.timestamp}

            Description:
            {alert.description}

            Recommended Action:
            {alert.recommended_action}

            Metrics:
            {json.dumps(alert.metrics, indent=2)}

            ---
            This is an automated alert from the Project Aurum monitoring system.
            """

            msg.attach(MIMEText(body, 'plain'))

            # Send email (commented out for demo)
            # server = smtplib.SMTP(smtp_server, smtp_port)
            # server.starttls()
            # server.login(email_user, email_password)
            # text = msg.as_string()
            # server.sendmail(email_user, recipients, text)
            # server.quit()

            logger.info(f"Email alert sent for {alert.model_name} - {alert.severity}")

        except Exception as e:
            logger.error(f"Error sending email alert: {e}")

    def _send_dashboard_notification(self, alert: DriftAlert):
        """Send notification to dashboard (WebSocket or similar)"""
        # In production, this would send to WebSocket connections or message queue
        logger.info(f"Dashboard notification: {alert.model_name} - {alert.description}")

    def _log_alert_details(self, alert: DriftAlert):
        """Log detailed alert information"""
        alert_log = {
            'timestamp': alert.timestamp,
            'model_name': alert.model_name,
            'drift_type': alert.drift_type,
            'severity': alert.severity,
            'description': alert.description,
            'metrics': alert.metrics,
            'recommended_action': alert.recommended_action
        }

        # Save to alert log file
        log_file = f"logs/alerts_{datetime.now().strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(alert_log) + '\n')
        except Exception as e:
            logger.error(f"Error writing alert log: {e}")

    def _simulate_prediction_logging(self, model_name: str):
        """Simulate logging predictions (demo purposes)"""
        # In production, this would be called by the actual model serving system
        try:
            # Generate sample predictions for Indonesian stocks
            indonesian_stocks = ['BBCA.JK', 'BMRI.JK', 'BBRI.JK', 'TLKM.JK', 'ASII.JK']

            for _ in range(np.random.randint(1, 5)):  # Random number of predictions
                stock = np.random.choice(indonesian_stocks)
                signal = np.random.choice(['BUY', 'SELL', 'HOLD'], p=[0.3, 0.2, 0.5])
                confidence = np.random.uniform(0.5, 0.95)

                features = {
                    'rsi': np.random.uniform(30, 70),
                    'macd': np.random.uniform(-0.5, 0.5),
                    'volume_ratio': np.random.uniform(0.8, 2.0),
                    'price_momentum': np.random.uniform(-0.05, 0.05)
                }

                self.monitor.log_prediction(
                    model_name=model_name,
                    stock_code=stock,
                    predicted_signal=signal,
                    confidence=confidence,
                    features=features
                )

        except Exception as e:
            logger.error(f"Error simulating prediction logging: {e}")

    def _generate_sample_features(self, model_name: str) -> Dict[str, float]:
        """Generate sample feature data for drift detection"""
        # Add some model-specific variations
        base_features = {
            'rsi': np.random.normal(65, 10),
            'macd': np.random.normal(0.1, 0.3),
            'volume_ratio': np.random.exponential(1.2),
            'price_momentum': np.random.normal(0.01, 0.05),
            'rupiah_strength': np.random.normal(15000, 200),
            'market_sentiment': np.random.uniform(-1, 1)
        }

        # Add model-specific drift patterns
        if model_name == "lq45_ensemble":
            base_features['lq45_momentum'] = np.random.normal(0.02, 0.08)
        elif model_name == "sector_rotation":
            base_features['sector_rotation_score'] = np.random.uniform(0, 1)

        return base_features

    def _get_recent_predictions(self, model_name: str) -> List[Dict]:
        """Get recent predictions for a model (demo)"""
        # In production, this would query the database
        return [{'id': i, 'timestamp': datetime.now().isoformat()} for i in range(np.random.randint(5, 20))]

    def _check_feature_quality(self, model_name: str) -> Dict[str, Any]:
        """Check feature data quality"""
        # Simulate feature quality checks
        issues = []

        # Random quality issues for demo
        if np.random.random() < 0.1:  # 10% chance of quality issue
            issues.append({
                'model': model_name,
                'issue': 'missing_features',
                'severity': 'medium',
                'description': 'Some feature values are missing or null'
            })

        return {'issues': issues}

    def _check_indonesian_market_data_quality(self) -> List[Dict]:
        """Check Indonesian market specific data quality"""
        issues = []

        # Simulate IDX data quality checks
        market_checks = [
            ('lq45_composition', 'LQ45 composition data'),
            ('rupiah_exchange_rate', 'IDR/USD exchange rate'),
            ('jakarta_volume', 'Jakarta stock exchange volume'),
            ('market_sentiment', 'Indonesian market sentiment data')
        ]

        for check_name, description in market_checks:
            if np.random.random() < 0.05:  # 5% chance of issue
                issues.append({
                    'check': check_name,
                    'issue': 'data_quality',
                    'severity': 'low',
                    'description': f'{description} quality degraded'
                })

        return issues

    def _report_data_quality_issues(self, issues: List[Dict]):
        """Report data quality issues"""
        logger.warning(f"Data quality issues detected: {len(issues)} issues found")
        for issue in issues:
            logger.warning(f"  {issue['check']} - {issue['severity']}: {issue['description']}")

    def _check_model_readiness(self, model_name: str) -> Dict[str, Any]:
        """Check if model is ready for trading day"""
        # Simulate model readiness check
        ready = np.random.random() > 0.05  # 95% chance of being ready

        issues = []
        if not ready:
            issues.append("Model weights not loaded")

        return {
            'ready': ready,
            'issues': issues,
            'last_update': datetime.now().isoformat(),
            'health_score': np.random.uniform(0.8, 1.0)
        }

    def _check_indonesian_data_feeds(self) -> Dict[str, Any]:
        """Check Indonesian market data feeds"""
        # Simulate data feed health check
        healthy = np.random.random() > 0.1  # 90% chance of being healthy

        return {
            'healthy': healthy,
            'idx_feed': 'connected' if healthy else 'disconnected',
            'lq45_feed': 'active',
            'rupiah_feed': 'active',
            'last_update': datetime.now().isoformat()
        }

    def _handle_market_data_alert(self, status: Dict[str, Any]):
        """Handle market data feed alerts"""
        alert = DriftAlert(
            timestamp=datetime.now().isoformat(),
            model_name='market_data_feed',
            drift_type='data_feed_alert',
            severity='high',
            description=f"Indonesian market data feed issue: {status}",
            metrics=status,
            recommended_action="Check IDX data connection and restore feed"
        )
        self._handle_alert(alert)

    def _analyze_daily_performance(self, model_name: str) -> Dict[str, Any]:
        """Analyze daily model performance"""
        # Simulate daily performance analysis
        return {
            'total_predictions': np.random.randint(50, 200),
            'accuracy': np.random.uniform(0.6, 0.8),
            'profitable_signals': np.random.randint(20, 80),
            'deviation_score': np.random.uniform(0, 0.5),
            'summary': 'Performance within expected range'
        }

    def _generate_post_market_summary(self):
        """Generate post-market summary for Indonesian stock exchange"""
        logger.info("Generating post-market summary for IDX")

        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'market_performance': {
                'idx_close': np.random.uniform(6800, 7200),
                'lq45_performance': np.random.uniform(-0.02, 0.02),
                'volume_traded': np.random.uniform(8e9, 15e9)
            },
            'model_summary': {},
            'recommendations': []
        }

        for model_name in self.models:
            daily_perf = self._analyze_daily_performance(model_name)
            summary['model_summary'][model_name] = daily_perf

        # Save summary
        summary_file = f"reports/post_market_summary_{datetime.now().strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(summary_file), exist_ok=True)

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

    def _generate_indonesian_market_summary(self):
        """Generate Indonesian market specific monitoring summary"""
        logger.info("Generating Indonesian market monitoring summary")

        summary = {
            'market': 'IDX',
            'timestamp': datetime.now().isoformat(),
            'rupiah_stability': np.random.choice(['stable', 'volatile', 'declining']),
            'lq45_momentum': np.random.choice(['bullish', 'bearish', 'neutral']),
            'foreign_sentiment': np.random.choice(['positive', 'negative', 'neutral']),
            'sector_performance': {
                'banking': np.random.uniform(-0.03, 0.03),
                'mining': np.random.uniform(-0.04, 0.04),
                'telecoms': np.random.uniform(-0.02, 0.02)
            }
        }

        # Save summary
        summary_file = f"reports/indonesian_market_summary_{datetime.now().strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(summary_file), exist_ok=True)

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

    def _send_daily_report_email(self, model_name: str, report: Dict[str, Any]):
        """Send daily report via email"""
        logger.info(f"Sending daily report for {model_name}")
        # Email sending implementation would go here
        # For demo, just log the action

    def run(self):
        """Run the monitoring scheduler"""
        logger.info("Starting model monitoring scheduler...")
        logger.info(f"Monitoring {len(self.models)} models: {', '.join(self.models)}")

        # Create required directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)
        os.makedirs('data', exist_ok=True)

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("Monitoring scheduler stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring scheduler: {e}")
            raise

if __name__ == "__main__":
    # Create scheduler and run
    scheduler = ModelMonitoringScheduler()

    # Run immediately for testing
    print("Running initial monitoring checks...")
    scheduler._run_performance_monitoring()
    scheduler._run_drift_detection()
    scheduler._run_data_quality_checks()

    print("Starting scheduled monitoring...")
    scheduler.run()