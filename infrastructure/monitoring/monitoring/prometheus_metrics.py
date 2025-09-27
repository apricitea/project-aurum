"""
Prometheus metrics collection for Project Aurum
Comprehensive monitoring and observability for Indonesian stock trading system
"""

from prometheus_client import (
    Counter, Histogram, Gauge, Info, Enum,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import sys
import os
from pathlib import Path
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

logger = logging.getLogger(__name__)

class ProjectAurumMetrics:
    """
    Comprehensive metrics collection for Project Aurum trading system
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics collectors"""
        self.registry = registry or CollectorRegistry()

        # System metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )

        self.system_memory_usage = Gauge(
            'system_memory_usage_bytes',
            'System memory usage in bytes',
            registry=self.registry
        )

        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            ['mount_point'],
            registry=self.registry
        )

        # Application metrics
        self.app_info = Info(
            'project_aurum_info',
            'Project Aurum application information',
            registry=self.registry
        )

        self.app_uptime = Gauge(
            'project_aurum_uptime_seconds',
            'Application uptime in seconds',
            registry=self.registry
        )

        # Model performance metrics
        self.model_predictions_total = Counter(
            'model_predictions_total',
            'Total number of predictions made by models',
            ['model_name', 'signal_type'],
            registry=self.registry
        )

        self.model_accuracy = Gauge(
            'model_accuracy_ratio',
            'Current model accuracy ratio (0-1)',
            ['model_name'],
            registry=self.registry
        )

        self.model_prediction_latency = Histogram(
            'model_prediction_latency_seconds',
            'Time taken to generate predictions',
            ['model_name'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )

        self.model_drift_score = Gauge(
            'model_drift_score',
            'Model drift detection score',
            ['model_name', 'drift_type'],
            registry=self.registry
        )

        # Trading metrics
        self.trading_signals_generated = Counter(
            'trading_signals_generated_total',
            'Total trading signals generated',
            ['stock_code', 'signal_type', 'market'],
            registry=self.registry
        )

        self.portfolio_value = Gauge(
            'portfolio_value_idr',
            'Current portfolio value in Indonesian Rupiah',
            ['portfolio_type'],
            registry=self.registry
        )

        self.trading_pnl = Gauge(
            'trading_pnl_idr',
            'Current trading P&L in Indonesian Rupiah',
            ['time_period'],
            registry=self.registry
        )

        self.position_count = Gauge(
            'open_positions_count',
            'Number of open trading positions',
            ['market', 'position_type'],
            registry=self.registry
        )

        # Indonesian market specific metrics
        self.idx_market_status = Enum(
            'idx_market_status',
            'Indonesian Stock Exchange market status',
            states=['pre_market', 'open', 'closed', 'break'],
            registry=self.registry
        )

        self.lq45_index_value = Gauge(
            'lq45_index_value',
            'LQ45 index current value',
            registry=self.registry
        )

        self.rupiah_exchange_rate = Gauge(
            'idr_usd_exchange_rate',
            'Indonesian Rupiah to USD exchange rate',
            registry=self.registry
        )

        self.jakarta_trading_volume = Gauge(
            'jakarta_trading_volume_shares',
            'Jakarta Stock Exchange trading volume',
            ['session'],
            registry=self.registry
        )

        # API metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )

        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )

        self.websocket_connections = Gauge(
            'websocket_connections_active',
            'Active WebSocket connections',
            ['connection_type'],
            registry=self.registry
        )

        # Database metrics
        self.database_connections = Gauge(
            'database_connections_active',
            'Active database connections',
            ['database'],
            registry=self.registry
        )

        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query execution time',
            ['query_type', 'table'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )

        self.database_errors_total = Counter(
            'database_errors_total',
            'Total database errors',
            ['database', 'error_type'],
            registry=self.registry
        )

        # Alert metrics
        self.alerts_generated_total = Counter(
            'alerts_generated_total',
            'Total alerts generated',
            ['alert_type', 'severity', 'model_name'],
            registry=self.registry
        )

        self.alerts_active = Gauge(
            'alerts_active_count',
            'Number of active alerts',
            ['severity'],
            registry=self.registry
        )

        # Business metrics
        self.daily_profit_loss = Gauge(
            'daily_profit_loss_idr',
            'Daily profit/loss in Indonesian Rupiah',
            ['strategy'],
            registry=self.registry
        )

        self.successful_trades_ratio = Gauge(
            'successful_trades_ratio',
            'Ratio of successful trades (0-1)',
            ['strategy', 'time_period'],
            registry=self.registry
        )

        self.risk_exposure = Gauge(
            'risk_exposure_ratio',
            'Current risk exposure ratio (0-1)',
            ['risk_type'],
            registry=self.registry
        )

        # Initialize app info
        self.app_info.info({
            'version': '1.0.0',
            'market': 'IDX',
            'currency': 'IDR',
            'timezone': 'Asia/Jakarta',
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        })

        # Start background metrics collection
        self.start_time = time.time()
        self._start_system_metrics_collection()

    def _start_system_metrics_collection(self):
        """Start background thread for system metrics collection"""
        def collect_system_metrics():
            while True:
                try:
                    # CPU usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.system_cpu_usage.set(cpu_percent)

                    # Memory usage
                    memory = psutil.virtual_memory()
                    self.system_memory_usage.set(memory.used)

                    # Disk usage
                    for disk in psutil.disk_partitions():
                        try:
                            disk_usage = psutil.disk_usage(disk.mountpoint)
                            usage_percent = (disk_usage.used / disk_usage.total) * 100
                            self.system_disk_usage.labels(mount_point=disk.mountpoint).set(usage_percent)
                        except (PermissionError, FileNotFoundError):
                            continue

                    # Application uptime
                    uptime = time.time() - self.start_time
                    self.app_uptime.set(uptime)

                    time.sleep(30)  # Collect every 30 seconds

                except Exception as e:
                    logger.error(f"Error collecting system metrics: {e}")
                    time.sleep(60)  # Wait longer on error

        metrics_thread = threading.Thread(target=collect_system_metrics, daemon=True)
        metrics_thread.start()

    # Model metrics methods
    def record_prediction(self, model_name: str, signal_type: str, latency: float):
        """Record a model prediction"""
        self.model_predictions_total.labels(model_name=model_name, signal_type=signal_type).inc()
        self.model_prediction_latency.labels(model_name=model_name).observe(latency)

    def update_model_accuracy(self, model_name: str, accuracy: float):
        """Update model accuracy metric"""
        self.model_accuracy.labels(model_name=model_name).set(accuracy)

    def update_drift_score(self, model_name: str, drift_type: str, score: float):
        """Update model drift score"""
        self.model_drift_score.labels(model_name=model_name, drift_type=drift_type).set(score)

    # Trading metrics methods
    def record_trading_signal(self, stock_code: str, signal_type: str, market: str = "IDX"):
        """Record a trading signal generation"""
        self.trading_signals_generated.labels(
            stock_code=stock_code,
            signal_type=signal_type,
            market=market
        ).inc()

    def update_portfolio_value(self, portfolio_type: str, value: float):
        """Update portfolio value"""
        self.portfolio_value.labels(portfolio_type=portfolio_type).set(value)

    def update_trading_pnl(self, time_period: str, pnl: float):
        """Update trading P&L"""
        self.trading_pnl.labels(time_period=time_period).set(pnl)

    def update_position_count(self, market: str, position_type: str, count: int):
        """Update position count"""
        self.position_count.labels(market=market, position_type=position_type).set(count)

    # Indonesian market metrics methods
    def update_market_status(self, status: str):
        """Update IDX market status"""
        self.idx_market_status.state(status)

    def update_lq45_value(self, value: float):
        """Update LQ45 index value"""
        self.lq45_index_value.set(value)

    def update_rupiah_rate(self, rate: float):
        """Update IDR/USD exchange rate"""
        self.rupiah_exchange_rate.set(rate)

    def update_trading_volume(self, session: str, volume: int):
        """Update Jakarta trading volume"""
        self.jakarta_trading_volume.labels(session=session).set(volume)

    # API metrics methods
    def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        self.http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        self.http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    def update_websocket_connections(self, connection_type: str, count: int):
        """Update WebSocket connection count"""
        self.websocket_connections.labels(connection_type=connection_type).set(count)

    # Database metrics methods
    def update_database_connections(self, database: str, count: int):
        """Update database connection count"""
        self.database_connections.labels(database=database).set(count)

    def record_database_query(self, query_type: str, table: str, duration: float):
        """Record database query metrics"""
        self.database_query_duration.labels(query_type=query_type, table=table).observe(duration)

    def record_database_error(self, database: str, error_type: str):
        """Record database error"""
        self.database_errors_total.labels(database=database, error_type=error_type).inc()

    # Alert metrics methods
    def record_alert(self, alert_type: str, severity: str, model_name: str):
        """Record alert generation"""
        self.alerts_generated_total.labels(
            alert_type=alert_type,
            severity=severity,
            model_name=model_name
        ).inc()

    def update_active_alerts(self, severity: str, count: int):
        """Update active alerts count"""
        self.alerts_active.labels(severity=severity).set(count)

    # Business metrics methods
    def update_daily_pnl(self, strategy: str, pnl: float):
        """Update daily P&L"""
        self.daily_profit_loss.labels(strategy=strategy).set(pnl)

    def update_success_ratio(self, strategy: str, time_period: str, ratio: float):
        """Update successful trades ratio"""
        self.successful_trades_ratio.labels(strategy=strategy, time_period=time_period).set(ratio)

    def update_risk_exposure(self, risk_type: str, exposure: float):
        """Update risk exposure"""
        self.risk_exposure.labels(risk_type=risk_type).set(exposure)

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get content type for metrics endpoint"""
        return CONTENT_TYPE_LATEST

class IndonesianMarketMetricsCollector:
    """
    Custom collector for Indonesian market specific metrics
    """

    def __init__(self, metrics: ProjectAurumMetrics):
        self.metrics = metrics

    def collect(self):
        """Collect Indonesian market metrics"""
        try:
            # Mock Indonesian market data - in production, this would fetch real data
            yield GaugeMetricFamily(
                'idx_composite_index',
                'IDX Composite Index value',
                value=7156.78
            )

            yield CounterMetricFamily(
                'lq45_stocks_monitored_total',
                'Total LQ45 stocks being monitored',
                value=45
            )

            # Sector performance metrics
            sectors = ['banking', 'mining', 'telecoms', 'consumer', 'property']
            sector_performances = [0.021, -0.015, 0.008, 0.012, -0.003]

            for sector, performance in zip(sectors, sector_performances):
                yield GaugeMetricFamily(
                    'sector_performance_ratio',
                    'Sector performance ratio',
                    value=performance,
                    labels=['sector']
                )

        except Exception as e:
            logger.error(f"Error collecting Indonesian market metrics: {e}")

class MetricsMiddleware:
    """
    Middleware for automatically collecting HTTP request metrics
    """

    def __init__(self, metrics: ProjectAurumMetrics):
        self.metrics = metrics

    async def __call__(self, request, call_next):
        """Process request and collect metrics"""
        start_time = time.time()
        method = request.method
        endpoint = str(request.url.path)

        try:
            response = await call_next(request)
            status = response.status_code
            duration = time.time() - start_time

            self.metrics.record_http_request(method, endpoint, status, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_http_request(method, endpoint, 500, duration)
            raise

class DatabaseMetricsCollector:
    """
    Collector for database performance metrics
    """

    def __init__(self, metrics: ProjectAurumMetrics):
        self.metrics = metrics

    def time_query(self, query_type: str, table: str):
        """Context manager for timing database queries"""
        class QueryTimer:
            def __init__(self, collector, query_type, table):
                self.collector = collector
                self.query_type = query_type
                self.table = table
                self.start_time = None

            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.collector.metrics.record_database_query(
                    self.query_type, self.table, duration
                )
                if exc_type:
                    self.collector.metrics.record_database_error(
                        "postgres", exc_type.__name__
                    )

        return QueryTimer(self, query_type, table)

# Global metrics instance
metrics = ProjectAurumMetrics()

# Export metrics instance for use in other modules
def get_metrics() -> ProjectAurumMetrics:
    """Get the global metrics instance"""
    return metrics

def init_metrics() -> ProjectAurumMetrics:
    """Initialize and return metrics instance"""
    return metrics

# Example usage and demo data
if __name__ == "__main__":
    import random
    import asyncio

    # Simulate some metrics
    metrics = ProjectAurumMetrics()

    # Simulate model predictions
    models = ["lq45_ensemble", "sector_rotation", "momentum_predictor"]
    signals = ["BUY", "SELL", "HOLD"]
    stocks = ["BBCA.JK", "BMRI.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"]

    print("Generating sample metrics for Project Aurum...")

    for _ in range(100):
        model = random.choice(models)
        signal = random.choice(signals)
        stock = random.choice(stocks)
        latency = random.uniform(0.01, 0.5)

        metrics.record_prediction(model, signal, latency)
        metrics.record_trading_signal(stock, signal)

    # Update some gauges
    for model in models:
        accuracy = random.uniform(0.6, 0.8)
        metrics.update_model_accuracy(model, accuracy)

        drift_score = random.uniform(0, 0.3)
        metrics.update_drift_score(model, "data_drift", drift_score)

    # Indonesian market metrics
    metrics.update_market_status("open")
    metrics.update_lq45_value(1087.45)
    metrics.update_rupiah_rate(15420.0)
    metrics.update_trading_volume("morning", 2.3e9)

    # Business metrics
    metrics.update_portfolio_value("main", 1.5e9)  # 1.5B IDR
    metrics.update_trading_pnl("daily", 125000000)  # 125M IDR profit
    metrics.update_success_ratio("lq45_strategy", "daily", 0.68)

    # Print metrics
    print("\nPrometheus Metrics Output:")
    print("=" * 50)
    print(metrics.get_metrics().decode('utf-8'))