"""
Comprehensive logging configuration for Project Aurum
Structured logging with JSON format, centralized collection, and Indonesian market context
"""

import logging
import logging.handlers
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
import threading
from queue import Queue
import atexit

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """

    def __init__(self, service_name: str = "project-aurum", include_extra: bool = True):
        super().__init__()
        self.service_name = service_name
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add extra fields if enabled
        if self.include_extra:
            # Indonesian market specific fields
            if hasattr(record, 'stock_code'):
                log_entry["stock_code"] = record.stock_code
            if hasattr(record, 'model_name'):
                log_entry["model_name"] = record.model_name
            if hasattr(record, 'trading_session'):
                log_entry["trading_session"] = record.trading_session
            if hasattr(record, 'market'):
                log_entry["market"] = record.market
            if hasattr(record, 'user_id'):
                log_entry["user_id"] = record.user_id
            if hasattr(record, 'request_id'):
                log_entry["request_id"] = record.request_id
            if hasattr(record, 'performance_metrics'):
                log_entry["performance_metrics"] = record.performance_metrics
            if hasattr(record, 'drift_score'):
                log_entry["drift_score"] = record.drift_score

            # Add any other extra fields
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                             'filename', 'module', 'lineno', 'funcName', 'created',
                             'msecs', 'relativeCreated', 'thread', 'threadName',
                             'processName', 'process', 'getMessage', 'exc_info',
                             'exc_text', 'stack_info'] and not key.startswith('_'):
                    if not hasattr(logging.LogRecord, key):
                        log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)

class IndonesianMarketContextFilter(logging.Filter):
    """
    Filter to add Indonesian market context to log records
    """

    def __init__(self):
        super().__init__()
        self.timezone = "Asia/Jakarta"

    def filter(self, record: logging.LogRecord) -> bool:
        """Add market context to log record"""
        # Add Indonesian timezone
        record.timezone = self.timezone

        # Add market session information
        jakarta_time = datetime.now()
        hour = jakarta_time.hour
        minute = jakarta_time.minute
        time_minutes = hour * 60 + minute

        # IDX trading hours: 09:00-15:49 WIB
        if 540 <= time_minutes <= 949:  # 9:00 AM to 3:49 PM
            if time_minutes <= 720:  # Before 12:00 PM
                record.trading_session = "morning"
            elif 720 < time_minutes <= 810:  # 12:00-1:30 PM (break)
                record.trading_session = "break"
            else:
                record.trading_session = "afternoon"
            record.market_open = True
        else:
            record.trading_session = "closed"
            record.market_open = False

        # Add day of week (Indonesian market is closed on weekends)
        weekday = jakarta_time.weekday()
        record.weekday = weekday
        record.is_trading_day = weekday < 5  # Monday=0, Friday=4

        return True

class PerformanceLogFilter(logging.Filter):
    """
    Filter for performance-sensitive logging
    """

    def __init__(self, min_duration_ms: float = 100.0):
        super().__init__()
        self.min_duration_ms = min_duration_ms

    def filter(self, record: logging.LogRecord) -> bool:
        """Only log performance records above threshold"""
        if hasattr(record, 'duration_ms'):
            return record.duration_ms >= self.min_duration_ms
        return True

class SecurityLogFilter(logging.Filter):
    """
    Filter to sanitize sensitive information from logs
    """

    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'key', 'credential',
        'auth', 'session', 'cookie', 'authorization'
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize sensitive information"""
        message = record.getMessage()

        # Mask sensitive information in the message
        for field in self.SENSITIVE_FIELDS:
            if field in message.lower():
                # Simple masking - in production, use more sophisticated methods
                import re
                pattern = rf'({field}["\s]*[:=]["\s]*)([^"\s,}}]+)'
                message = re.sub(pattern, r'\1***REDACTED***', message, flags=re.IGNORECASE)

        # Update the record
        record.msg = message
        record.args = ()

        return True

class AsyncFileHandler(logging.handlers.RotatingFileHandler):
    """
    Asynchronous file handler for high-performance logging
    """

    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0,
                 encoding=None, delay=False, queue_size=1000):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.queue = Queue(maxsize=queue_size)
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        atexit.register(self._cleanup)

    def emit(self, record):
        """Emit log record asynchronously"""
        try:
            if not self.queue.full():
                self.queue.put(record, block=False)
        except Exception:
            # If queue is full or other error, fall back to synchronous logging
            super().emit(record)

    def _worker(self):
        """Worker thread for processing log records"""
        while True:
            try:
                record = self.queue.get()
                if record is None:  # Shutdown signal
                    break
                super().emit(record)
                self.queue.task_done()
            except Exception:
                # Continue processing even if one record fails
                continue

    def _cleanup(self):
        """Cleanup on application shutdown"""
        self.queue.put(None)  # Signal shutdown
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)

class AuditLogger:
    """
    Specialized logger for audit events
    """

    def __init__(self, logger_name: str = "project_aurum.audit"):
        self.logger = logging.getLogger(logger_name)

    def log_user_action(self, user_id: str, action: str, resource: str,
                       result: str, details: Optional[Dict[str, Any]] = None):
        """Log user action for audit purposes"""
        self.logger.info(
            f"User action: {action} on {resource}",
            extra={
                "event_type": "user_action",
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "result": result,
                "details": details or {},
                "audit": True
            }
        )

    def log_trading_action(self, model_name: str, stock_code: str, signal: str,
                          confidence: float, user_id: Optional[str] = None):
        """Log trading signal generation for audit"""
        self.logger.info(
            f"Trading signal generated: {signal} for {stock_code}",
            extra={
                "event_type": "trading_signal",
                "model_name": model_name,
                "stock_code": stock_code,
                "signal": signal,
                "confidence": confidence,
                "user_id": user_id,
                "market": "IDX",
                "audit": True
            }
        )

    def log_model_action(self, model_name: str, action: str, result: str,
                        metrics: Optional[Dict[str, Any]] = None):
        """Log model-related actions"""
        self.logger.info(
            f"Model action: {action} for {model_name}",
            extra={
                "event_type": "model_action",
                "model_name": model_name,
                "action": action,
                "result": result,
                "metrics": metrics or {},
                "audit": True
            }
        )

    def log_security_event(self, event_type: str, severity: str, description: str,
                          user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log security-related events"""
        self.logger.warning(
            f"Security event: {event_type}",
            extra={
                "event_type": "security_event",
                "security_event_type": event_type,
                "severity": severity,
                "description": description,
                "user_id": user_id,
                "ip_address": ip_address,
                "audit": True
            }
        )

def setup_logging(
    service_name: str = "project-aurum",
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_file_size: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 10,
    enable_console: bool = True,
    enable_json: bool = True,
    enable_audit: bool = True
) -> Dict[str, logging.Logger]:
    """
    Set up comprehensive logging configuration for Project Aurum

    Args:
        service_name: Name of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        max_file_size: Maximum size of each log file
        backup_count: Number of backup files to keep
        enable_console: Enable console logging
        enable_json: Enable JSON formatted logging
        enable_audit: Enable audit logging

    Returns:
        Dictionary of configured loggers
    """

    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatters
    json_formatter = JSONFormatter(service_name=service_name)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create filters
    market_filter = IndonesianMarketContextFilter()
    security_filter = SecurityLogFilter()
    performance_filter = PerformanceLogFilter()

    loggers = {}

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(market_filter)
        console_handler.addFilter(security_filter)
        root_logger.addHandler(console_handler)

    # Main application log file
    if enable_json:
        app_handler = AsyncFileHandler(
            filename=log_path / f"{service_name}.log",
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        app_handler.setLevel(getattr(logging, log_level.upper()))
        app_handler.setFormatter(json_formatter)
        app_handler.addFilter(market_filter)
        app_handler.addFilter(security_filter)
        root_logger.addHandler(app_handler)

    # Error log file (errors and above only)
    error_handler = AsyncFileHandler(
        filename=log_path / f"{service_name}-errors.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    error_handler.addFilter(market_filter)
    root_logger.addHandler(error_handler)

    # Performance log file
    performance_logger = logging.getLogger(f"{service_name}.performance")
    performance_handler = AsyncFileHandler(
        filename=log_path / f"{service_name}-performance.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    performance_handler.setLevel(logging.INFO)
    performance_handler.setFormatter(json_formatter)
    performance_handler.addFilter(performance_filter)
    performance_logger.addHandler(performance_handler)
    performance_logger.propagate = False
    loggers['performance'] = performance_logger

    # Trading log file (trading-specific events)
    trading_logger = logging.getLogger(f"{service_name}.trading")
    trading_handler = AsyncFileHandler(
        filename=log_path / f"{service_name}-trading.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    trading_handler.setLevel(logging.INFO)
    trading_handler.setFormatter(json_formatter)
    trading_handler.addFilter(market_filter)
    trading_logger.addHandler(trading_handler)
    trading_logger.propagate = False
    loggers['trading'] = trading_logger

    # Model monitoring log file
    model_logger = logging.getLogger(f"{service_name}.models")
    model_handler = AsyncFileHandler(
        filename=log_path / f"{service_name}-models.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    model_handler.setLevel(logging.INFO)
    model_handler.setFormatter(json_formatter)
    model_logger.addHandler(model_handler)
    model_logger.propagate = False
    loggers['models'] = model_logger

    # Security log file
    security_logger = logging.getLogger(f"{service_name}.security")
    security_handler = AsyncFileHandler(
        filename=log_path / f"{service_name}-security.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(json_formatter)
    security_logger.addHandler(security_handler)
    security_logger.propagate = False
    loggers['security'] = security_logger

    # Audit log file
    if enable_audit:
        audit_logger = logging.getLogger(f"{service_name}.audit")
        audit_handler = AsyncFileHandler(
            filename=log_path / f"{service_name}-audit.log",
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(json_formatter)
        audit_handler.addFilter(market_filter)
        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = False
        loggers['audit'] = audit_logger

    # Add main logger
    loggers['main'] = logging.getLogger(service_name)

    return loggers

class LoggingContextManager:
    """
    Context manager for adding context to logs within a scope
    """

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)

# Convenience functions for common logging patterns
def log_performance(logger: logging.Logger, operation: str, duration_ms: float,
                   **kwargs):
    """Log performance metrics"""
    logger.info(
        f"Performance: {operation} completed in {duration_ms:.2f}ms",
        extra={
            "operation": operation,
            "duration_ms": duration_ms,
            "performance_log": True,
            **kwargs
        }
    )

def log_trading_signal(logger: logging.Logger, model_name: str, stock_code: str,
                      signal: str, confidence: float, **kwargs):
    """Log trading signal generation"""
    logger.info(
        f"Trading signal: {signal} for {stock_code} (confidence: {confidence:.3f})",
        extra={
            "model_name": model_name,
            "stock_code": stock_code,
            "signal": signal,
            "confidence": confidence,
            "market": "IDX",
            "trading_log": True,
            **kwargs
        }
    )

def log_model_drift(logger: logging.Logger, model_name: str, drift_type: str,
                   drift_score: float, severity: str, **kwargs):
    """Log model drift detection"""
    logger.warning(
        f"Model drift detected: {drift_type} for {model_name} (score: {drift_score:.3f})",
        extra={
            "model_name": model_name,
            "drift_type": drift_type,
            "drift_score": drift_score,
            "severity": severity,
            "model_monitoring": True,
            **kwargs
        }
    )

# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    loggers = setup_logging(
        service_name="project-aurum-demo",
        log_level="INFO",
        log_dir="demo_logs"
    )

    main_logger = loggers['main']
    trading_logger = loggers['trading']
    performance_logger = loggers['performance']
    models_logger = loggers['models']

    # Test logging
    main_logger.info("Project Aurum logging system initialized")

    # Test trading logs
    log_trading_signal(
        trading_logger,
        model_name="lq45_ensemble",
        stock_code="BBCA.JK",
        signal="BUY",
        confidence=0.78,
        target_price=8500,
        current_price=8200
    )

    # Test performance logs
    log_performance(
        performance_logger,
        operation="model_prediction",
        duration_ms=45.6,
        model_name="momentum_predictor",
        input_features=12
    )

    # Test model monitoring logs
    log_model_drift(
        models_logger,
        model_name="sector_rotation",
        drift_type="data_drift",
        drift_score=0.34,
        severity="medium",
        affected_features=["volume", "price_momentum"]
    )

    # Test context manager
    with LoggingContextManager(main_logger, request_id="req_123", user_id="user_456"):
        main_logger.info("Processing user request")
        main_logger.info("Request completed successfully")

    # Test audit logging
    audit = AuditLogger()
    audit.log_user_action(
        user_id="admin",
        action="model_retrain",
        resource="lq45_ensemble",
        result="success",
        details={"training_samples": 10000, "accuracy_improvement": 0.05}
    )

    audit.log_trading_action(
        model_name="momentum_predictor",
        stock_code="TLKM.JK",
        signal="SELL",
        confidence=0.89,
        user_id="trader_001"
    )

    print("Logging test completed. Check demo_logs/ directory for output files.")