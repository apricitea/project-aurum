"""Unit tests for AuthManager token operations (no DB required)."""
import sys
import pytest
from datetime import datetime
from unittest.mock import patch
from fastapi import HTTPException


# conftest.py patches src.api.config — we need to load auth after that mock is in place
# so we import it here at module level (after conftest runs)
def _load_auth():
    """Import auth module, ensuring the config mock from conftest is active."""
    import importlib
    if "src.api.auth" in sys.modules:
        return sys.modules["src.api.auth"]
    return importlib.import_module("src.api.auth")


@pytest.fixture
def auth():
    from src.api.auth import AuthManager
    manager = AuthManager()
    # conftest mocks settings — override JWT fields with real values for token tests
    manager.secret_key = "test-secret-key-for-unit-tests-only"
    manager.algorithm = "HS256"
    manager.access_token_expire_minutes = 30
    manager.refresh_token_expire_days = 7
    return manager


def test_hash_and_verify_password(auth):
    pw = "MySecureP@ss12"
    hashed = auth.hash_password(pw)
    assert auth.verify_password(pw, hashed)
    assert not auth.verify_password("wrong", hashed)


def test_hash_produces_different_salts(auth):
    pw = "MySecureP@ss12"
    h1 = auth.hash_password(pw)
    h2 = auth.hash_password(pw)
    assert h1 != h2  # bcrypt uses random salt


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
    from src.api.auth import User
    user = User(
        id="1", username="admin", email="a@b.com", role="admin",
        permissions={}, is_active=True, created_at=datetime.now()
    )
    assert user.has_permission("anything")
    assert user.has_permission("generate_signals")
    assert user.has_permission("nonexistent_perm")


def test_user_has_permission_trader_respects_map():
    from src.api.auth import User
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


def test_role_permissions_viewer_cannot_manage_portfolio(auth):
    perms = auth.role_permissions["viewer"]
    assert perms["manage_portfolio"] is False
    assert perms["view_signals"] is True
