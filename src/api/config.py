"""
Configuration module for Indonesian Quantitative Trading Alert System
Environment-based configuration management
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    """Application settings"""

    # Application settings
    APP_NAME: str = "Indonesian Quantitative Trading Alert System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Database settings
    DB_URL: Optional[str] = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "trading_system"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    # JWT settings
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # ML Model settings
    MODEL_PATH: str = "models/idx_quant_model.pkl"
    MODEL_VERSION: str = "1.0"
    AUTO_RETRAIN_ENABLED: bool = True
    RETRAIN_SCHEDULE: str = "0 20 * * 0"  # Every Sunday at 8 PM

    # Indonesian Market settings
    MARKET_TIMEZONE: str = "Asia/Jakarta"
    MARKET_OPEN_TIME: str = "09:00"
    MARKET_CLOSE_TIME: str = "15:49"
    MARKET_LUNCH_START: str = "12:00"
    MARKET_LUNCH_END: str = "13:30"
    TRADING_DAYS: List[int] = [0, 1, 2, 3, 4]  # Monday to Friday

    # Signal Generation settings
    SIGNAL_GENERATION_TIME: str = "08:30"
    AUTO_SIGNAL_GENERATION: bool = True
    SIGNAL_CONFIDENCE_THRESHOLD: float = 0.6
    MAX_DAILY_SIGNALS: int = 50

    # Risk Management settings
    MAX_POSITION_SIZE: float = 0.05  # 5%
    MAX_SECTOR_CONCENTRATION: float = 0.25  # 25%
    MAX_PORTFOLIO_VOLATILITY: float = 0.20  # 20%
    MAX_DRAWDOWN: float = 0.15  # 15%
    RISK_CHECK_INTERVAL_MINUTES: int = 5

    # Email notification settings
    EMAIL_ENABLED: bool = False
    EMAIL_CONFIG: Dict[str, Any] = {
        "server": "smtp.gmail.com",
        "port": 587,
        "username": "",
        "password": "",
        "from_email": ""
    }
    DEFAULT_EMAIL_RECIPIENTS: List[str] = []

    # Telegram notification settings
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    DEFAULT_TELEGRAM_CHATS: List[str] = []
    WEB_APP_URL: str = "http://localhost:3000"

    # SMS notification settings (Twilio)
    SMS_ENABLED: bool = False
    TWILIO_CONFIG: Dict[str, Any] = {
        "account_sid": "",
        "auth_token": "",
        "from_number": ""
    }
    DEFAULT_SMS_NUMBERS: List[str] = []

    # Webhook notification settings
    WEBHOOK_ENABLED: bool = True
    DEFAULT_WEBHOOK_URLS: List[str] = []

    # Data sources settings
    IDX_DATA_ENABLED: bool = True
    IDX_API_KEY: str = ""
    IDX_API_URL: str = "https://api.idx.co.id"

    YAHOO_FINANCE_ENABLED: bool = True
    ALPHA_VANTAGE_ENABLED: bool = False
    ALPHA_VANTAGE_API_KEY: str = ""

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/trading_system.log"
    LOG_ROTATION: str = "midnight"
    LOG_RETENTION: int = 30  # days

    # Monitoring settings
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 60  # seconds

    # Backup settings
    BACKUP_ENABLED: bool = True
    BACKUP_SCHEDULE: str = "0 2 * * *"  # Daily at 2 AM
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_LOCATION: str = "backups/"

    # Performance settings
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    API_RATE_LIMIT: str = "100/minute"
    MAX_CONCURRENT_REQUESTS: int = 100

    # Feature flags
    REAL_TIME_ALERTS: bool = True
    ADVANCED_ANALYTICS: bool = True
    MOBILE_NOTIFICATIONS: bool = True
    EXPORT_REPORTS: bool = True

    # LLM / Agents configuration
    LLM_PROVIDER: str = "google"
    LLM_PRIMARY_MODEL: str = "gpt-4o-mini"
    LLM_SECONDARY_MODEL: str = "gpt-4.1-mini"
    LLM_BASE_URL: Optional[str] = None
    LLM_TEMPERATURE: float = 0.4
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_CACHE_ENABLED: bool = True
    LLM_MAX_TOKENS: int = 4096
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    LLM_RUN_LOG_PATH: str = "logs/ai_research_runs.jsonl"

    @validator('EMAIL_CONFIG', pre=True)
    def parse_email_config(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @validator('TWILIO_CONFIG', pre=True)
    def parse_twilio_config(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @validator('DEFAULT_EMAIL_RECIPIENTS', pre=True)
    def parse_email_recipients(cls, v):
        if isinstance(v, str):
            return v.split(',') if v else []
        return v

    @validator('DEFAULT_TELEGRAM_CHATS', pre=True)
    def parse_telegram_chats(cls, v):
        if isinstance(v, str):
            return v.split(',') if v else []
        return v

    @validator('DEFAULT_SMS_NUMBERS', pre=True)
    def parse_sms_numbers(cls, v):
        if isinstance(v, str):
            return v.split(',') if v else []
        return v

    @validator('DEFAULT_WEBHOOK_URLS', pre=True)
    def parse_webhook_urls(cls, v):
        if isinstance(v, str):
            return v.split(',') if v else []
        return v

    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return v.split(',') if v else ["*"]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Get database connection URL"""
        if self.DB_URL:
            return self.DB_URL
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"

    def is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        from datetime import datetime, time
        import pytz

        tz = pytz.timezone(self.MARKET_TIMEZONE)
        now = datetime.now(tz).time()

        market_open = time.fromisoformat(self.MARKET_OPEN_TIME)
        market_close = time.fromisoformat(self.MARKET_CLOSE_TIME)
        lunch_start = time.fromisoformat(self.MARKET_LUNCH_START)
        lunch_end = time.fromisoformat(self.MARKET_LUNCH_END)

        # Check if it's a trading day
        weekday = datetime.now(tz).weekday()
        if weekday not in self.TRADING_DAYS:
            return False

        # Check if within market hours (excluding lunch break)
        morning_session = market_open <= now < lunch_start
        afternoon_session = lunch_end <= now <= market_close

        return morning_session or afternoon_session

    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration"""
        return {
            "email": {
                "enabled": self.EMAIL_ENABLED,
                "config": self.EMAIL_CONFIG,
                "recipients": self.DEFAULT_EMAIL_RECIPIENTS
            },
            "telegram": {
                "enabled": self.TELEGRAM_ENABLED,
                "bot_token": self.TELEGRAM_BOT_TOKEN,
                "chats": self.DEFAULT_TELEGRAM_CHATS
            },
            "sms": {
                "enabled": self.SMS_ENABLED,
                "config": self.TWILIO_CONFIG,
                "numbers": self.DEFAULT_SMS_NUMBERS
            },
            "webhook": {
                "enabled": self.WEBHOOK_ENABLED,
                "urls": self.DEFAULT_WEBHOOK_URLS
            }
        }

    def get_risk_limits(self) -> Dict[str, float]:
        """Get risk management limits"""
        return {
            "max_position_size": self.MAX_POSITION_SIZE,
            "max_sector_concentration": self.MAX_SECTOR_CONCENTRATION,
            "max_portfolio_volatility": self.MAX_PORTFOLIO_VOLATILITY,
            "max_drawdown": self.MAX_DRAWDOWN
        }

    def get_data_source_config(self) -> Dict[str, Any]:
        """Get data source configuration"""
        return {
            "idx": {
                "enabled": self.IDX_DATA_ENABLED,
                "api_key": self.IDX_API_KEY,
                "api_url": self.IDX_API_URL
            },
            "yahoo_finance": {
                "enabled": self.YAHOO_FINANCE_ENABLED
            },
            "alpha_vantage": {
                "enabled": self.ALPHA_VANTAGE_ENABLED,
                "api_key": self.ALPHA_VANTAGE_API_KEY
            }
        }


class DevelopmentSettings(Settings):
    """Development environment settings"""
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"

    # Development database
    DB_NAME: str = "trading_system_dev"

    # Relaxed security for development
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Enable all features for testing
    EMAIL_ENABLED: bool = True
    TELEGRAM_ENABLED: bool = True
    REAL_TIME_ALERTS: bool = True
    ADVANCED_ANALYTICS: bool = True


class ProductionSettings(Settings):
    """Production environment settings"""
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    # Production security
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # Production database with connection pooling
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40

    # Production API settings
    API_WORKERS: int = 4
    MAX_CONCURRENT_REQUESTS: int = 200

    # Strict CORS in production
    ALLOWED_ORIGINS: List[str] = [
        "https://trading.yourcompany.com",
        "https://api.yourcompany.com"
    ]


class TestSettings(Settings):
    """Test environment settings"""
    DEBUG: bool = True
    ENVIRONMENT: str = "test"

    # Test database
    DB_NAME: str = "trading_system_test"

    # Disable external services in tests
    EMAIL_ENABLED: bool = False
    TELEGRAM_ENABLED: bool = False
    SMS_ENABLED: bool = False

    # Fast tokens for testing
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 5

    # Disable background tasks
    AUTO_SIGNAL_GENERATION: bool = False
    AUTO_RETRAIN_ENABLED: bool = False


def get_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionSettings()
    elif env == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()


# Configuration validation
def validate_configuration():
    """Validate critical configuration settings"""
    errors = []

    # Validate JWT secret in production
    if settings.is_production() and settings.JWT_SECRET_KEY == "your-secret-key-change-in-production":
        errors.append("JWT_SECRET_KEY must be changed in production")

    # Validate database configuration
    if not all([settings.DB_HOST, settings.DB_NAME, settings.DB_USER, settings.DB_PASSWORD]):
        errors.append("Database configuration is incomplete")

    # Validate notification settings if enabled
    if settings.EMAIL_ENABLED:
        email_config = settings.EMAIL_CONFIG
        if not all([email_config.get("username"), email_config.get("password")]):
            errors.append("Email configuration is incomplete")

    if settings.TELEGRAM_ENABLED and not settings.TELEGRAM_BOT_TOKEN:
        errors.append("Telegram bot token is required when Telegram is enabled")

    if settings.SMS_ENABLED:
        twilio_config = settings.TWILIO_CONFIG
        if not all([twilio_config.get("account_sid"), twilio_config.get("auth_token")]):
            errors.append("Twilio configuration is incomplete")

    # Validate model path
    if not os.path.exists(os.path.dirname(settings.MODEL_PATH)):
        errors.append(f"Model directory does not exist: {os.path.dirname(settings.MODEL_PATH)}")

    # Validate risk limits
    risk_limits = settings.get_risk_limits()
    for limit_name, limit_value in risk_limits.items():
        if not 0 < limit_value <= 1:
            errors.append(f"Invalid risk limit {limit_name}: {limit_value}")

    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))


# Environment-specific logging configuration
def configure_logging():
    """Configure logging based on settings"""
    import logging
    import logging.handlers
    import os

    # Create logs directory
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.handlers.TimedRotatingFileHandler(
                settings.LOG_FILE,
                when=settings.LOG_ROTATION,
                backupCount=settings.LOG_RETENTION
            )
        ]
    )

    # Set specific logger levels
    if settings.DEBUG:
        logging.getLogger("asyncpg").setLevel(logging.WARNING)
        logging.getLogger("redis").setLevel(logging.WARNING)
    else:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Initialize configuration
try:
    validate_configuration()
    configure_logging()
except Exception as e:
    print(f"Configuration error: {e}")
    if settings.is_production():
        raise
    else:
        print("Continuing with potentially invalid configuration in development mode")
