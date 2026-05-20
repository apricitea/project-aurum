# Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all identified bugs, add test coverage for core business logic, and harden the configuration so the system can safely run in production.

**Architecture:** Fix bugs in-place following existing patterns; add pytest tests alongside existing `tests/` structure; harden `config.py` with startup validation. No new abstractions.

**Tech Stack:** Python 3.12, FastAPI, asyncpg, SQLAlchemy 2.0, Redis, Celery, XGBoost/scikit-learn, pytest + pytest-asyncio

---

## Audit Findings Summary

### Hard Bugs (prevent app/module from loading)
| # | File | Issue |
|---|------|-------|
| B1 | `src/domains/trading/infrastructure/ml_models/model_ensemble.py:14` | `from sklearn.metrics import sharpe_ratio` — does not exist in sklearn; `ImportError` on import |
| B2 | `src/api/database.py:477` | `create_alert()` raw SQL uses column `metadata`; DB column is `meta_data` (with underscore); `UndefinedColumn` at runtime |
| B3 | `src/api/main.py` | `Request` used in middleware (line 127) but not imported; `NameError` on first HTTP request |

### Structural Bugs (latent failures)
| # | File | Issue |
|---|------|-------|
| B4 | `src/api/signal_service.py:21-26` | `sys.path.append` + root-relative imports; breaks in Celery workers and non-root CWDs |
| B5 | `src/domains/trading/infrastructure/ml_models/model_ensemble.py:193` | `fillna(method='ffill')` deprecated in pandas 2.x; will become error in future pandas |
| B6 | `src/api/alert_engine.py:361-365` | Creates second Celery app inside `AlertEngine.initialize()`; never used, wastes connections |
| B7 | `src/api/schemas.py:54` | `LoginRequest.password` has `min_length=6`; actual policy requires 12 chars; schema passes passwords the service then rejects |

### Production Config Issues
| # | File | Issue |
|---|------|-------|
| C1 | `src/api/config.py:341-345` | `ProductionSettings.ALLOWED_ORIGINS` has hardcoded placeholder URLs; never replaced at deploy time |
| C2 | `src/api/config.py:46` | Default JWT secret is a known string; predictable tokens in dev environments |
| C3 | `src/api/config.py:118` | Base `Settings.ALLOWED_ORIGINS = ["*"]` — wide-open CORS for any deployment that doesn't override |
| C4 | `docker-compose.yml` | Dev compose hardcodes `POSTGRES_PASSWORD: password` and `DB_PASSWORD: password`; acceptable in dev but needs clear env-var override path for staging |

---

## File Map

**Modified:**
- `src/domains/trading/infrastructure/ml_models/model_ensemble.py` — remove bad import, fix pandas deprecation
- `src/api/database.py` — fix `metadata` → `meta_data` column name in `create_alert()`
- `src/api/main.py` — add missing `Request` import
- `src/api/signal_service.py` — replace `sys.path.append` with proper package imports
- `src/api/alert_engine.py` — remove unused second Celery app
- `src/api/schemas.py` — fix `LoginRequest.password` min_length
- `src/api/config.py` — add startup guard for production ALLOWED_ORIGINS

**Created:**
- `tests/test_model_ensemble.py` — import smoke test + ensemble instantiation
- `tests/test_database.py` — `create_alert` column name, portfolio upsert
- `tests/test_auth.py` — token creation, decode, permission checks
- `tests/test_config.py` — settings validation, `get_database_url`, `is_market_hours`
- `tests/test_password_security.py` — policy enforcement, edge cases
- `tests/test_api_health.py` — app startup, `/health`, `/health/detailed`
- `tests/test_schemas.py` — LoginRequest validation, CreateAlertRequest

---

## Task 1: Fix B1 — Remove non-existent sklearn import

**Files:**
- Modify: `src/domains/trading/infrastructure/ml_models/model_ensemble.py:14`
- Test: `tests/test_model_ensemble.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_model_ensemble.py
"""Smoke tests for model_ensemble module."""

def test_model_ensemble_imports():
    """Module must import without error."""
    import importlib
    mod = importlib.import_module(
        "src.domains.trading.infrastructure.ml_models.model_ensemble"
    )
    assert hasattr(mod, "IDXQuantitativeModel")


def test_idx_quantitative_model_instantiates():
    from src.domains.trading.infrastructure.ml_models.model_ensemble import IDXQuantitativeModel
    model = IDXQuantitativeModel()
    assert model.is_trained is False
    assert model.technical_model is not None
    assert model.fundamental_model is not None
    assert model.sentiment_model is not None
    assert model.meta_model is not None
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /home/vlain/workspaces/personal/project-aurum
uv run pytest tests/test_model_ensemble.py -v
```
Expected: `ImportError: cannot import name 'sharpe_ratio' from 'sklearn.metrics'`

- [ ] **Step 3: Fix the import**

In `src/domains/trading/infrastructure/ml_models/model_ensemble.py`, line 14, change:

```python
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, sharpe_ratio
```

to:

```python
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
uv run pytest tests/test_model_ensemble.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/model_ensemble.py tests/test_model_ensemble.py
git commit -m "fix: remove non-existent sharpe_ratio import from sklearn.metrics [nyx-auto]"
```

---

## Task 2: Fix B2 — `metadata` vs `meta_data` column name in `create_alert()`

**Files:**
- Modify: `src/api/database.py:477-492`
- Test: `tests/test_database.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_database.py
"""Unit tests for DatabaseManager raw SQL correctness."""

import pytest
import re


def test_create_alert_sql_uses_correct_column_name():
    """
    Raw SQL in create_alert() must use 'meta_data', matching the DB column.
    The SQLAlchemy model defines the column as 'meta_data' (Alert.__tablename__).
    """
    import inspect
    from src.api.database import DatabaseManager

    source = inspect.getsource(DatabaseManager.create_alert)

    # The SQL INSERT must name the column meta_data, not metadata
    # Look for the VALUES list in the INSERT statement
    assert "meta_data" in source, (
        "create_alert() SQL must use column name 'meta_data', not 'metadata'"
    )
    # Ensure the wrong name is NOT present in the INSERT column list
    # (allow it in other contexts like dict keys)
    insert_match = re.search(
        r"INSERT INTO alerts\s*\(([^)]+)\)", source, re.DOTALL
    )
    assert insert_match, "Could not find INSERT INTO alerts in create_alert()"
    column_list = insert_match.group(1)
    assert "meta_data" in column_list, f"Column list must contain 'meta_data': {column_list}"
    assert "metadata," not in column_list and not column_list.strip().endswith("metadata"), (
        f"Column list must not contain bare 'metadata': {column_list}"
    )


def test_alert_model_column_name():
    """SQLAlchemy Alert model must define column as 'meta_data'."""
    from src.api.database import Alert
    col_names = [c.key for c in Alert.__table__.columns]
    assert "meta_data" in col_names, f"Alert model columns: {col_names}"
    assert "metadata" not in col_names
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/test_database.py::test_create_alert_sql_uses_correct_column_name -v
```
Expected: assertion failure showing `metadata` in column list.

- [ ] **Step 3: Fix the raw SQL in `create_alert()`**

In `src/api/database.py`, in the `create_alert` method, change the INSERT SQL:

```python
            query = """
                INSERT INTO alerts (alert_type, message, priority, status, metadata,
                                  stock_code, user_id, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """
```

to:

```python
            query = """
                INSERT INTO alerts (alert_type, message, priority, status, meta_data,
                                  stock_code, user_id, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
uv run pytest tests/test_database.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/api/database.py tests/test_database.py
git commit -m "fix: correct meta_data column name in create_alert() SQL [nyx-auto]"
```

---

## Task 3: Fix B3 — Missing `Request` import in `main.py`

**Files:**
- Modify: `src/api/main.py:6`
- Test: `tests/test_api_health.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_health.py
"""Tests that the FastAPI app can be imported and health endpoints work."""

def test_app_imports_without_error():
    """App module must import without NameError."""
    import importlib
    # This will raise NameError if Request is not imported
    mod = importlib.import_module("src.api.main")
    assert hasattr(mod, "app")


def test_health_endpoint_exists():
    from src.api.main import app
    routes = {route.path for route in app.routes}
    assert "/health" in routes
    assert "/health/detailed" in routes
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/test_api_health.py::test_app_imports_without_error -v
```
Expected: `NameError: name 'Request' is not defined` when middleware is evaluated.

- [ ] **Step 3: Add the missing import**

In `src/api/main.py`, change the FastAPI imports line:

```python
from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks
```

to:

```python
from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks, Request
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_api_health.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/api/main.py tests/test_api_health.py
git commit -m "fix: add missing Request import in main.py middleware [nyx-auto]"
```

---

## Task 4: Fix B4 — Replace `sys.path` hack in `signal_service.py`

**Files:**
- Modify: `src/api/signal_service.py:8-9,21-26`

The root shim files (`feature_engineering.py`, `model_ensemble.py`, `signal_generator.py`, `main_pipeline.py`) re-export from their proper `src.` locations. Use those proper import paths directly.

- [ ] **Step 1: Verify the proper import paths exist**

```bash
uv run python -c "
from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer
from src.domains.trading.infrastructure.ml_models.model_ensemble import IDXQuantitativeModel
from src.domains.trading.application.services.signal_generator import SignalGenerator, AlertSystem
from src.data_pipeline.unified_pipeline import UnifiedDataPipeline
print('All imports OK')
"
```
Expected: `All imports OK`

- [ ] **Step 2: Replace the imports**

In `src/api/signal_service.py`, remove:

```python
import sys
...
# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from feature_engineering import IDXFeatureEngineer
from model_ensemble import IDXQuantitativeModel
from signal_generator import SignalGenerator, AlertSystem
from main_pipeline import DataCollector, TradingPipeline
```

Replace with:

```python
from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer
from src.domains.trading.infrastructure.ml_models.model_ensemble import IDXQuantitativeModel
from src.domains.trading.application.services.signal_generator import SignalGenerator, AlertSystem
from src.data_pipeline.unified_pipeline import UnifiedDataPipeline as DataCollector, UnifiedDataPipeline as TradingPipeline
```

Also remove `import sys` and the `from pathlib import Path` line if `Path` is no longer used (check — `Path` is still used in `_load_model`; keep it).

- [ ] **Step 3: Verify app still imports cleanly**

```bash
uv run python -c "from src.api.signal_service import SignalService; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Run existing tests to confirm no regressions**

```bash
uv run pytest tests/ -v --tb=short
```
Expected: all previously passing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/api/signal_service.py
git commit -m "fix: replace sys.path hack with proper package imports in signal_service [nyx-auto]"
```

---

## Task 5: Fix B5 — Pandas 2.x deprecation in `model_ensemble.py`

**Files:**
- Modify: `src/domains/trading/infrastructure/ml_models/model_ensemble.py:193`

- [ ] **Step 1: Find all occurrences of the deprecated pattern**

```bash
grep -n "fillna(method=" src/domains/trading/infrastructure/ml_models/model_ensemble.py
```

- [ ] **Step 2: Replace deprecated `fillna(method='ffill')` with `ffill()`**

In `FundamentalValueModel.prepare_features()`, change:

```python
        feature_matrix = data[fundamental_cols].fillna(method='ffill').fillna(0)
```

to:

```python
        feature_matrix = data[fundamental_cols].ffill().fillna(0)
```

- [ ] **Step 3: Verify no deprecation warnings**

```bash
uv run python -W error::FutureWarning -c "
from src.domains.trading.infrastructure.ml_models.model_ensemble import FundamentalValueModel
print('No deprecation warnings')
"
```
Expected: `No deprecation warnings`

- [ ] **Step 4: Add test to `test_model_ensemble.py`**

```python
def test_no_pandas_deprecation_on_import():
    """No FutureWarning from pandas on model import."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        from src.domains.trading.infrastructure.ml_models import model_ensemble  # noqa: F401
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_model_ensemble.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/domains/trading/infrastructure/ml_models/model_ensemble.py tests/test_model_ensemble.py
git commit -m "fix: replace deprecated fillna(method='ffill') with ffill() [nyx-auto]"
```

---

## Task 6: Fix B6 + B7 — Remove unused Celery in AlertEngine; fix LoginRequest min_length

**Files:**
- Modify: `src/api/alert_engine.py:354-365`
- Modify: `src/api/schemas.py:54`
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_schemas.py
"""Tests for request/response schema validation."""
import pytest
from pydantic import ValidationError
from src.api.schemas import LoginRequest, CreateAlertRequest


def test_login_request_password_min_length_is_12():
    """LoginRequest must reject passwords shorter than 12 characters."""
    with pytest.raises(ValidationError):
        LoginRequest(username="testuser", password="short")


def test_login_request_password_exactly_12_accepted():
    req = LoginRequest(username="testuser", password="Ab#defgh1234")
    assert req.password == "Ab#defgh1234"


def test_login_request_password_11_chars_rejected():
    with pytest.raises(ValidationError):
        LoginRequest(username="testuser", password="Ab#defgh123")


def test_create_alert_request_valid():
    req = CreateAlertRequest(
        alert_type="risk_breach",
        message="Portfolio exceeded limit",
        priority="high",
    )
    assert req.priority == "high"


def test_create_alert_request_message_too_long():
    with pytest.raises(ValidationError):
        CreateAlertRequest(
            alert_type="x",
            message="x" * 1001,
        )
```

- [ ] **Step 2: Run tests to confirm `test_login_request_password_min_length_is_12` fails**

```bash
uv run pytest tests/test_schemas.py -v
```
Expected: `test_login_request_password_min_length_is_12` FAILS (password "short" currently passes schema validation with `min_length=6`).

- [ ] **Step 3: Fix `LoginRequest` min_length**

In `src/api/schemas.py`, line 54, change:

```python
    password: str = Field(..., min_length=6)
```

to:

```python
    password: str = Field(..., min_length=12)
```

- [ ] **Step 4: Remove unused Celery app in AlertEngine**

In `src/api/alert_engine.py`, in the `initialize()` method, remove:

```python
            # Initialize Celery for background tasks
            self.celery_app = Celery(
                'alert_engine',
                broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
                backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
            )
```

Also remove the `celery_app: None` initialization from `__init__` and the `self.celery_app` attribute from `__init__`:

```python
        self.celery_app = None  # ← remove this line
```

And remove the `from celery import Celery` import at the top of `alert_engine.py` since `Celery` is no longer used in that file.

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_schemas.py -v
```
Expected: all 5 pass.

- [ ] **Step 6: Confirm AlertEngine still imports**

```bash
uv run python -c "from src.api.alert_engine import AlertEngine; print('OK')"
```

- [ ] **Step 7: Commit**

```bash
git add src/api/schemas.py src/api/alert_engine.py tests/test_schemas.py
git commit -m "fix: align LoginRequest password min_length with policy; remove duplicate Celery in AlertEngine [nyx-auto]"
```

---

## Task 7: Production config hardening

**Files:**
- Modify: `src/api/config.py`
- Test: `tests/test_config.py`

Issues to address:
- C1: `ProductionSettings.ALLOWED_ORIGINS` has placeholder URLs
- C3: Base `ALLOWED_ORIGINS = ["*"]` is too open
- C2: Default JWT secret validation already exists in `validate_configuration()` — verify it's called at startup

- [ ] **Step 1: Write config tests**

```python
# tests/test_config.py
"""Tests for settings validation and helper methods."""
import os
import pytest
from unittest.mock import patch


def test_get_database_url_uses_db_url_when_set():
    """If DB_URL is set, it must be returned directly."""
    from src.api.config import Settings
    s = Settings(DB_URL="postgresql://user:pass@host/db")
    assert s.get_database_url() == "postgresql://user:pass@host/db"


def test_get_database_url_returns_postgres_when_credentials_set():
    """With real credentials, URL must be postgresql://"""
    from src.api.config import Settings
    s = Settings(
        DB_HOST="myhost",
        DB_PORT=5432,
        DB_NAME="mydb",
        DB_USER="myuser",
        DB_PASSWORD="mypass",
        ENVIRONMENT="production",
    )
    url = s.get_database_url()
    assert url.startswith("postgresql://")
    assert "myhost" in url
    assert "mydb" in url


def test_get_database_url_does_not_fallback_to_sqlite_in_production():
    """Production environment must never return a SQLite URL."""
    from src.api.config import Settings
    s = Settings(ENVIRONMENT="production")
    url = s.get_database_url()
    assert not url.startswith("sqlite"), "Production must not use SQLite"


def test_validate_configuration_raises_for_default_jwt_secret():
    """validate_configuration() must raise if JWT secret is the default placeholder."""
    from src.api.config import ProductionSettings, validate_configuration
    with patch.object(ProductionSettings, "is_production", return_value=True):
        s = ProductionSettings(JWT_SECRET_KEY="your-secret-key-change-in-production")
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            # Call validate_configuration with a production-like settings object
            # by temporarily patching the module-level settings
            import src.api.config as cfg
            original = cfg.settings
            cfg.settings = s
            try:
                validate_configuration()
            finally:
                cfg.settings = original


def test_production_settings_allowed_origins_are_not_placeholders():
    """
    ProductionSettings.ALLOWED_ORIGINS must not contain the default placeholder URLs.
    In real deployments these are overridden via env var; the test ensures the
    guard exists to catch un-configured deploys.
    """
    from src.api.config import ProductionSettings
    s = ProductionSettings()
    placeholders = {"https://trading.yourcompany.com", "https://api.yourcompany.com"}
    actual = set(s.ALLOWED_ORIGINS)
    # If ANY placeholder is still present, validate_configuration should catch it.
    # Here we just verify that if they're present, the validator will flag them.
    if actual & placeholders:
        import src.api.config as cfg
        original = cfg.settings
        cfg.settings = s
        try:
            with pytest.raises(ValueError, match="ALLOWED_ORIGINS"):
                from src.api.config import validate_configuration
                validate_configuration()
        finally:
            cfg.settings = original


def test_is_market_hours_returns_bool():
    from src.api.config import Settings
    s = Settings()
    result = s.is_market_hours()
    assert isinstance(result, bool)


def test_get_redis_url_without_password():
    from src.api.config import Settings
    s = Settings(REDIS_HOST="myredis", REDIS_PORT=6380)
    url = s.get_redis_url()
    assert url == "redis://myredis:6380/0"


def test_get_redis_url_with_password():
    from src.api.config import Settings
    s = Settings(REDIS_HOST="myredis", REDIS_PORT=6380, REDIS_PASSWORD="secret")
    url = s.get_redis_url()
    assert "secret@myredis" in url
```

- [ ] **Step 2: Run tests to establish baseline**

```bash
uv run pytest tests/test_config.py -v
```
Note which tests fail.

- [ ] **Step 3: Add ALLOWED_ORIGINS placeholder check to `validate_configuration()`**

In `src/api/config.py`, in `validate_configuration()`, add after the JWT secret check:

```python
    # Validate ALLOWED_ORIGINS in production
    if settings.is_production():
        placeholder_origins = {"https://trading.yourcompany.com", "https://api.yourcompany.com"}
        if set(settings.ALLOWED_ORIGINS) & placeholder_origins:
            errors.append(
                "ALLOWED_ORIGINS contains placeholder URLs — set ALLOWED_ORIGINS env var for your domain"
            )
        if "*" in settings.ALLOWED_ORIGINS:
            errors.append("ALLOWED_ORIGINS must not be '*' in production")
```

- [ ] **Step 4: Add `get_database_url` guard against SQLite in production**

In `src/api/config.py`, in `get_database_url()`, change:

```python
    def get_database_url(self) -> str:
        """Get database connection URL"""
        if self.DB_URL:
            return self.DB_URL
        # For development, prefer SQLite if PostgreSQL credentials are defaults
        if (self.ENVIRONMENT.lower() == "development" and
            self.DB_PASSWORD == "password" and self.DB_USER == "postgres"):
            return "sqlite:///./data/trading_system.db"
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
```

to:

```python
    def get_database_url(self) -> str:
        """Get database connection URL"""
        if self.DB_URL:
            return self.DB_URL
        # SQLite fallback only in development with default credentials
        if (self.ENVIRONMENT.lower() not in ("production", "staging") and
                self.DB_PASSWORD == "password" and self.DB_USER == "postgres"):
            return "sqlite:///./data/trading_system.db"
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_config.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/api/config.py tests/test_config.py
git commit -m "fix: harden production config validation for ALLOWED_ORIGINS and DB URL [nyx-auto]"
```

---

## Task 8: Core auth tests

**Files:**
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_auth.py
"""Unit tests for AuthManager token operations (no DB required)."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.api.auth import AuthManager, User


@pytest.fixture
def auth():
    return AuthManager()


def test_hash_and_verify_password(auth):
    pw = "MySecureP@ss12"
    hashed = auth.hash_password(pw)
    assert auth.verify_password(pw, hashed)
    assert not auth.verify_password("wrong", hashed)


def test_create_access_token_contains_expected_fields(auth):
    import jwt
    data = {"sub": "user-123", "username": "alice", "role": "trader", "permissions": {}}
    token = auth.create_access_token(data)
    payload = jwt.decode(token, auth.secret_key, algorithms=[auth.algorithm])
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token_type_is_refresh(auth):
    import jwt
    token = auth.create_refresh_token({"sub": "user-123"})
    payload = jwt.decode(token, auth.secret_key, algorithms=[auth.algorithm])
    assert payload["type"] == "refresh"


def test_decode_expired_token_raises_401(auth):
    from datetime import timedelta
    import jwt
    expired = jwt.encode(
        {"sub": "x", "exp": datetime.utcnow() - timedelta(minutes=1), "type": "access"},
        auth.secret_key,
        algorithm=auth.algorithm,
    )
    with pytest.raises(HTTPException) as exc:
        auth.decode_token(expired)
    assert exc.value.status_code == 401


def test_decode_tampered_token_raises_401(auth):
    with pytest.raises(HTTPException) as exc:
        auth.decode_token("not.a.valid.token")
    assert exc.value.status_code == 401


def test_user_has_permission_admin_always_true():
    user = User(
        id="1", username="admin", email="a@b.com", role="admin",
        permissions={}, is_active=True, created_at=datetime.now()
    )
    assert user.has_permission("anything")


def test_user_has_permission_trader_respects_map():
    user = User(
        id="1", username="t", email="t@b.com", role="trader",
        permissions={"manage_portfolio": True, "generate_signals": False},
        is_active=True, created_at=datetime.now()
    )
    assert user.has_permission("manage_portfolio")
    assert not user.has_permission("generate_signals")
    assert not user.has_permission("nonexistent")


def test_role_permissions_trader_cannot_generate_signals(auth):
    perms = auth.role_permissions["trader"]
    assert perms["generate_signals"] is False
    assert perms["manage_portfolio"] is True


def test_role_permissions_admin_has_all(auth):
    perms = auth.role_permissions["admin"]
    assert all(perms.values()), "Admin should have all permissions True"
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_auth.py -v
```
Expected: all 9 pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth.py
git commit -m "test: add auth unit tests for token lifecycle and RBAC [nyx-auto]"
```

---

## Task 9: Password security tests

**Files:**
- Test: `tests/test_password_security.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_password_security.py
"""Tests for password validation policy."""
import pytest
from src.api.password_security import validate_password, generate_secure_password, verify_password, hash_password


def test_valid_password_passes():
    result = validate_password("MySecureP@ss12!")
    assert result["is_valid"] is True
    assert result["errors"] == []


def test_short_password_fails():
    result = validate_password("Short1!")
    assert result["is_valid"] is False
    assert any("12" in e for e in result["errors"])


def test_no_uppercase_fails():
    result = validate_password("mysecurep@ss12!")
    assert result["is_valid"] is False
    assert any("uppercase" in e.lower() for e in result["errors"])


def test_no_lowercase_fails():
    result = validate_password("MYSECUREP@SS12!")
    assert result["is_valid"] is False
    assert any("lowercase" in e.lower() for e in result["errors"])


def test_no_digit_fails():
    result = validate_password("MySecureP@ssWord!")
    assert result["is_valid"] is False
    assert any("digit" in e.lower() for e in result["errors"])


def test_insufficient_special_chars_fails():
    result = validate_password("MySecurePassword1")
    assert result["is_valid"] is False
    assert any("special" in e.lower() for e in result["errors"])


def test_exactly_two_special_chars_passes():
    result = validate_password("MySecurePass12@!")
    assert result["is_valid"] is True


def test_generate_secure_password_meets_policy():
    for _ in range(10):
        pw = generate_secure_password(16)
        result = validate_password(pw)
        assert result["is_valid"] is True, f"Generated password failed: {pw} — {result['errors']}"


def test_hash_and_verify_round_trip():
    pw = "TestPass@word12"
    h = hash_password(pw)
    assert verify_password(pw, h)
    assert not verify_password("wrong", h)


def test_verify_password_wrong_returns_false():
    h = hash_password("CorrectP@ss12")
    assert not verify_password("WrongP@ss12", h)
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_password_security.py -v
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_password_security.py
git commit -m "test: add password security policy tests [nyx-auto]"
```

---

## Task 10: Database layer tests

**Files:**
- Test: `tests/test_database.py` (extend existing file from Task 2)

- [ ] **Step 1: Add portfolio and signal query tests to `tests/test_database.py`**

```python
# Append to tests/test_database.py

def test_database_manager_singleton_not_initialized_raises():
    """get_db_manager() must raise RuntimeError before initialization."""
    from src.api.database import _db_manager_instance, get_db_manager
    import src.api.database as db_module
    original = db_module._db_manager_instance
    db_module._db_manager_instance = None
    try:
        with pytest.raises(RuntimeError, match="not initialized"):
            get_db_manager()
    finally:
        db_module._db_manager_instance = original


def test_set_db_manager_registers_singleton():
    """set_db_manager() must make get_db_manager() return the same instance."""
    from src.api.database import set_db_manager, get_db_manager, DatabaseManager
    import src.api.database as db_module
    original = db_module._db_manager_instance
    fake = object()
    set_db_manager(fake)
    try:
        assert get_db_manager() is fake
    finally:
        db_module._db_manager_instance = original


def test_guid_type_processes_none():
    """GUID type must return None for None input."""
    from src.api.database import GUID
    from unittest.mock import MagicMock
    guid = GUID()
    dialect = MagicMock()
    dialect.name = "postgresql"
    result = guid.process_bind_param(None, dialect)
    assert result is None


def test_jsonb_type_uses_postgres_jsonb_for_pg_dialect():
    """JSONB custom type must delegate to PostgreSQL JSONB for pg dialect."""
    from src.api.database import JSONB
    from unittest.mock import MagicMock
    from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
    jsonb = JSONB()
    dialect = MagicMock()
    dialect.name = "postgresql"
    descriptor = MagicMock()
    dialect.type_descriptor = MagicMock(return_value=descriptor)
    result = jsonb.load_dialect_impl(dialect)
    # Verify type_descriptor was called with a PG_JSONB instance
    call_arg = dialect.type_descriptor.call_args[0][0]
    assert isinstance(call_arg, PG_JSONB)
```

- [ ] **Step 2: Run all database tests**

```bash
uv run pytest tests/test_database.py -v
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_database.py
git commit -m "test: extend database layer tests for singleton, GUID, JSONB types [nyx-auto]"
```

---

## Task 11: Full test suite run + verify no regressions

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest tests/ -v --tb=short 2>&1 | tail -30
```

- [ ] **Step 2: Check import health of all top-level modules**

```bash
uv run python -c "
from src.api.main import app
from src.api.database import DatabaseManager
from src.api.auth import AuthManager
from src.api.alert_engine import AlertEngine
from src.api.signal_service import SignalService
from src.api.risk_monitor import RiskMonitor
from src.api.config import settings, validate_configuration
from src.domains.trading.infrastructure.ml_models.model_ensemble import IDXQuantitativeModel
from src.data_pipeline.unified_pipeline import UnifiedDataPipeline
print('All modules imported successfully')
"
```
Expected: `All modules imported successfully` with no errors or warnings.

- [ ] **Step 3: Check for remaining `sys.path.append` in src/**

```bash
grep -r "sys.path.append" src/
```
Expected: no output.

- [ ] **Step 4: Check for remaining `sharpe_ratio` reference**

```bash
grep -r "sharpe_ratio" src/
```
Expected: no output.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: production readiness — all bugs fixed, tests added [nyx-auto]"
```

---

## Task 12: Verify test count and coverage summary

- [ ] **Step 1: Run with coverage**

```bash
uv run pytest tests/ -v --tb=short -q 2>&1 | tail -20
```

- [ ] **Step 2: Confirm minimum test count**

The following test files must exist and pass:
- `tests/test_model_ensemble.py` (3 tests)
- `tests/test_database.py` (6 tests)
- `tests/test_api_health.py` (2 tests)
- `tests/test_schemas.py` (5 tests)
- `tests/test_auth.py` (9 tests)
- `tests/test_password_security.py` (10 tests)
- `tests/test_config.py` (8 tests)
- `tests/test_telegram_bot.py` (existing)

Total new tests: ~43 (up from ~0 meaningful coverage)

---

## Bug Fix Checklist (for final verification)

| Bug | File | Fix |
|-----|------|-----|
| B1 `sharpe_ratio` ImportError | `model_ensemble.py:14` | Remove from import line |
| B2 `metadata` column name | `database.py:477` | Rename to `meta_data` in SQL |
| B3 Missing `Request` import | `main.py:6` | Add to FastAPI import |
| B4 `sys.path` hack | `signal_service.py:21-26` | Use `src.` package paths |
| B5 pandas `fillna(method=)` | `model_ensemble.py:193` | Use `.ffill()` |
| B6 Unused Celery in AlertEngine | `alert_engine.py:361` | Remove |
| B7 LoginRequest min_length=6 | `schemas.py:54` | Change to 12 |
| C1/C3 ALLOWED_ORIGINS | `config.py` | Add placeholder validation |
| C2 SQLite in prod | `config.py` | Guard `get_database_url` |
