"""Tests for settings validation and helper methods.

Note: conftest.py patches sys.modules['src.api.config'] with a Mock at module
level to support Telegram bot tests. These tests temporarily remove that mock
to exercise the real Settings class, then restore it.
"""
import sys
import pytest
import importlib


def _real_config():
    """Load the real config module, bypassing the conftest Mock."""
    mock = sys.modules.pop("src.api.config", None)
    try:
        import src.api.config as real_mod
        return real_mod
    finally:
        if mock is not None:
            sys.modules["src.api.config"] = mock


@pytest.fixture
def cfg():
    return _real_config()


def test_get_database_url_uses_db_url_when_set(cfg):
    """If DB_URL is set, it must be returned directly."""
    s = cfg.Settings(DB_URL="postgresql://user:pass@host/db")
    assert s.get_database_url() == "postgresql://user:pass@host/db"


def test_get_database_url_returns_postgres_with_real_creds(cfg):
    """With non-default credentials, URL must be postgresql://"""
    s = cfg.Settings(
        DB_HOST="myhost",
        DB_PORT=5432,
        DB_NAME="mydb",
        DB_USER="myuser",
        DB_PASSWORD="mypass",
        ENVIRONMENT="development",
    )
    url = s.get_database_url()
    assert url.startswith("postgresql://")
    assert "myhost" in url
    assert "mydb" in url


def test_get_database_url_falls_back_to_sqlite_in_dev_with_defaults(cfg):
    """Dev environment with default credentials must use SQLite."""
    s = cfg.Settings(
        DB_USER="postgres",
        DB_PASSWORD="password",
        ENVIRONMENT="development",
    )
    url = s.get_database_url()
    assert url.startswith("sqlite")


def test_get_database_url_does_not_fallback_to_sqlite_in_production(cfg):
    """Production environment must never return a SQLite URL."""
    s = cfg.Settings(
        DB_USER="postgres",
        DB_PASSWORD="password",
        ENVIRONMENT="production",
    )
    url = s.get_database_url()
    assert not url.startswith("sqlite"), "Production must not use SQLite"


def test_get_database_url_does_not_fallback_to_sqlite_in_staging(cfg):
    """Staging environment must not return a SQLite URL."""
    s = cfg.Settings(
        DB_USER="postgres",
        DB_PASSWORD="password",
        ENVIRONMENT="staging",
    )
    url = s.get_database_url()
    assert not url.startswith("sqlite"), "Staging must not use SQLite"


def test_validate_configuration_raises_for_default_jwt_secret_in_production(cfg):
    """validate_configuration() must raise and include JWT_SECRET_KEY in the error message."""
    original = cfg.settings
    # Pass ENVIRONMENT explicitly — .env has ENVIRONMENT=development which would override the class default
    s = cfg.ProductionSettings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="your-secret-key-change-in-production",
        ALLOWED_ORIGINS=["https://myapp.com"],
        MODEL_PATH="",  # empty dirname skips the model-dir check
    )
    cfg.settings = s
    try:
        with pytest.raises(ValueError) as exc_info:
            cfg.validate_configuration()
        assert "JWT_SECRET_KEY" in str(exc_info.value)
    finally:
        cfg.settings = original


def test_validate_configuration_raises_for_placeholder_allowed_origins(cfg):
    """validate_configuration() must raise and include ALLOWED_ORIGINS in the error message."""
    original = cfg.settings
    s = cfg.ProductionSettings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a-real-secret-key-that-is-sufficiently-long-yes",
        ALLOWED_ORIGINS=["https://trading.yourcompany.com"],
        MODEL_PATH="",  # empty dirname skips the model-dir check
    )
    cfg.settings = s
    try:
        with pytest.raises(ValueError) as exc_info:
            cfg.validate_configuration()
        assert "ALLOWED_ORIGINS" in str(exc_info.value)
    finally:
        cfg.settings = original


def test_is_market_hours_returns_bool(cfg):
    s = cfg.Settings()
    result = s.is_market_hours()
    assert isinstance(result, bool)


def test_get_redis_url_without_password(cfg):
    # Explicitly clear REDIS_PASSWORD to avoid picking it up from .env
    s = cfg.Settings(REDIS_HOST="myredis", REDIS_PORT=6380, REDIS_PASSWORD=None, REDIS_DB=0)
    url = s.get_redis_url()
    assert url == "redis://myredis:6380/0"


def test_get_redis_url_with_password(cfg):
    s = cfg.Settings(REDIS_HOST="myredis", REDIS_PORT=6380, REDIS_PASSWORD="secret", REDIS_DB=0)
    url = s.get_redis_url()
    assert "secret@myredis" in url
