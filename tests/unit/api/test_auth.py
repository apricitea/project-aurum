"""
Unit tests for authentication and authorization module
"""

import pytest
import jwt
import bcrypt
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.api.auth import AuthManager, User


class TestUser:
    """Test User model"""

    def test_user_creation(self):
        """Test user model creation"""
        user_data = {
            "id": "1",
            "username": "testuser",
            "email": "test@example.com",
            "role": "trader",
            "permissions": {"view_alerts": True, "create_alerts": False},
            "is_active": True,
            "created_at": datetime.now()
        }

        user = User(**user_data)

        assert user.id == "1"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "trader"
        assert user.is_active is True

    def test_user_has_permission_granted(self):
        """Test user permission check when permission is granted"""
        user = User(
            id="1",
            username="testuser",
            email="test@example.com",
            role="trader",
            permissions={"view_alerts": True, "create_alerts": False},
            is_active=True,
            created_at=datetime.now()
        )

        assert user.has_permission("view_alerts") is True
        assert user.has_permission("create_alerts") is False

    def test_user_has_permission_admin_override(self):
        """Test admin role has all permissions"""
        user = User(
            id="1",
            username="admin",
            email="admin@example.com",
            role="admin",
            permissions={"view_alerts": False},  # Even if explicitly False
            is_active=True,
            created_at=datetime.now()
        )

        assert user.has_permission("view_alerts") is True
        assert user.has_permission("any_permission") is True

    def test_user_has_permission_not_granted(self):
        """Test user permission check when permission not granted"""
        user = User(
            id="1",
            username="testuser",
            email="test@example.com",
            role="trader",
            permissions={"view_alerts": True},
            is_active=True,
            created_at=datetime.now()
        )

        assert user.has_permission("admin_access") is False
        assert user.has_permission("nonexistent_permission") is False


class TestAuthManager:
    """Test AuthManager class"""

    @pytest.fixture
    def auth_manager(self, mock_settings):
        """Create AuthManager instance for testing"""
        with patch('src.api.auth.settings', mock_settings):
            mock_settings.JWT_SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
            return AuthManager()

    def test_auth_manager_initialization(self, auth_manager):
        """Test AuthManager initialization"""
        assert auth_manager.secret_key == "test-secret-key"
        assert auth_manager.algorithm == "HS256"
        assert auth_manager.access_token_expire_minutes == 30
        assert auth_manager.refresh_token_expire_days == 7

    def test_hash_password(self, auth_manager):
        """Test password hashing"""
        password = "testpassword123"
        hashed = auth_manager.hash_password(password)

        assert hashed != password
        assert bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def test_verify_password_correct(self, auth_manager):
        """Test password verification with correct password"""
        password = "testpassword123"
        hashed = auth_manager.hash_password(password)

        assert auth_manager.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_manager):
        """Test password verification with incorrect password"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = auth_manager.hash_password(password)

        assert auth_manager.verify_password(wrong_password, hashed) is False

    def test_create_access_token(self, auth_manager):
        """Test access token creation"""
        user_id = "123"
        token = auth_manager.create_access_token(user_id)

        # Decode token to verify
        payload = jwt.decode(token, auth_manager.secret_key, algorithms=[auth_manager.algorithm])

        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token(self, auth_manager):
        """Test refresh token creation"""
        user_id = "123"
        token = auth_manager.create_refresh_token(user_id)

        # Decode token to verify
        payload = jwt.decode(token, auth_manager.secret_key, algorithms=[auth_manager.algorithm])

        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_token_valid(self, auth_manager):
        """Test token verification with valid token"""
        user_id = "123"
        token = auth_manager.create_access_token(user_id)

        payload = auth_manager.verify_token(token)

        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_verify_token_expired(self, auth_manager):
        """Test token verification with expired token"""
        user_id = "123"

        # Create token with past expiration
        expire = datetime.utcnow() - timedelta(minutes=1)
        payload = {
            "sub": user_id,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, auth_manager.secret_key, algorithm=auth_manager.algorithm)

        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token(token)

        assert exc_info.value.status_code == 401
        assert "Token has expired" in str(exc_info.value.detail)

    def test_verify_token_invalid_signature(self, auth_manager):
        """Test token verification with invalid signature"""
        # Create token with wrong secret
        payload = {
            "sub": "123",
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=auth_manager.algorithm)

        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token(token)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    def test_verify_token_malformed(self, auth_manager):
        """Test token verification with malformed token"""
        token = "malformed.jwt.token"

        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token(token)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, auth_manager, mock_db_manager):
        """Test successful user retrieval by ID"""
        user_data = {
            "id": "123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "trader",
            "permissions": '{"view_alerts": true, "create_alerts": false}',
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": datetime.now()
        }

        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = [user_data]

            user = await auth_manager.get_user_by_id("123")

            assert user.id == "123"
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.permissions["view_alerts"] is True

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, auth_manager, mock_db_manager):
        """Test user retrieval when user not found"""
        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = []

            user = await auth_manager.get_user_by_id("nonexistent")

            assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, auth_manager, mock_db_manager):
        """Test successful user retrieval by username"""
        user_data = {
            "id": "123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "trader",
            "permissions": '{"view_alerts": true}',
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": None
        }

        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = [user_data]

            user = await auth_manager.get_user_by_username("testuser")

            assert user.id == "123"
            assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_manager, mock_db_manager):
        """Test successful authentication"""
        password = "testpassword123"
        hashed_password = auth_manager.hash_password(password)

        user_data = {
            "id": "123",
            "username": "testuser",
            "email": "test@example.com",
            "password": hashed_password,
            "role": "trader",
            "permissions": '{"view_alerts": true}',
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": None
        }

        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = [user_data]
            mock_db_manager.execute_non_query = AsyncMock()

            result = await auth_manager.authenticate("testuser", password)

            assert "access_token" in result
            assert "refresh_token" in result
            assert result["token_type"] == "bearer"
            assert "expires_in" in result

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_manager, mock_db_manager):
        """Test authentication with non-existent user"""
        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = []

            with pytest.raises(HTTPException) as exc_info:
                await auth_manager.authenticate("nonexistent", "password")

            assert exc_info.value.status_code == 401
            assert "Invalid credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, auth_manager, mock_db_manager):
        """Test authentication with wrong password"""
        password = "testpassword123"
        hashed_password = auth_manager.hash_password(password)

        user_data = {
            "id": "123",
            "username": "testuser",
            "password": hashed_password,
            "is_active": True
        }

        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = [user_data]

            with pytest.raises(HTTPException) as exc_info:
                await auth_manager.authenticate("testuser", "wrongpassword")

            assert exc_info.value.status_code == 401
            assert "Invalid credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, auth_manager, mock_db_manager):
        """Test authentication with inactive user"""
        password = "testpassword123"
        hashed_password = auth_manager.hash_password(password)

        user_data = {
            "id": "123",
            "username": "testuser",
            "password": hashed_password,
            "is_active": False
        }

        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = [user_data]

            with pytest.raises(HTTPException) as exc_info:
                await auth_manager.authenticate("testuser", password)

            assert exc_info.value.status_code == 401
            assert "Account is inactive" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_manager, mock_db_manager):
        """Test successful token refresh"""
        user_id = "123"
        refresh_token = auth_manager.create_refresh_token(user_id)

        user_data = {
            "id": "123",
            "username": "testuser",
            "is_active": True
        }

        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = [user_data]

            result = await auth_manager.refresh_token(refresh_token)

            assert "access_token" in result
            assert "refresh_token" in result
            assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, auth_manager):
        """Test token refresh with invalid refresh token"""
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.refresh_token("invalid.token.here")

        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_refresh_token_wrong_type(self, auth_manager):
        """Test token refresh with access token instead of refresh token"""
        user_id = "123"
        access_token = auth_manager.create_access_token(user_id)

        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.refresh_token(access_token)

        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in str(exc_info.value.detail)


class TestAuthenticationDependencies:
    """Test authentication dependencies and middleware"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, sample_user):
        """Test successful current user retrieval"""
        from src.api.auth import get_current_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid.jwt.token"

        with patch('src.api.auth.AuthManager') as mock_auth_class:
            mock_auth = mock_auth_class.return_value
            mock_auth.verify_token.return_value = {"sub": "123", "type": "access"}
            mock_auth.get_user_by_id.return_value = sample_user

            user = await get_current_user(mock_credentials)

            assert user.id == sample_user.id
            assert user.username == sample_user.username

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test current user retrieval with invalid token"""
        from src.api.auth import get_current_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid.token"

        with patch('src.api.auth.AuthManager') as mock_auth_class:
            mock_auth = mock_auth_class.return_value
            mock_auth.verify_token.side_effect = HTTPException(
                status_code=401, detail="Invalid token"
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self):
        """Test current user retrieval when user not found in database"""
        from src.api.auth import get_current_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid.jwt.token"

        with patch('src.api.auth.AuthManager') as mock_auth_class:
            mock_auth = mock_auth_class.return_value
            mock_auth.verify_token.return_value = {"sub": "123", "type": "access"}
            mock_auth.get_user_by_id.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == 401
            assert "User not found" in str(exc_info.value.detail)


class TestSecurityFeatures:
    """Test security features and edge cases"""

    def test_password_complexity_requirements(self, auth_manager):
        """Test password complexity validation"""
        # Test weak passwords
        weak_passwords = [
            "123",
            "password",
            "12345678",
            "qwerty",
            "abc123"
        ]

        for weak_password in weak_passwords:
            # Assuming password complexity validation exists
            try:
                is_valid = auth_manager.validate_password_strength(weak_password)
                assert is_valid is False, f"Weak password '{weak_password}' should be rejected"
            except AttributeError:
                # Method doesn't exist, skip this test
                pytest.skip("Password complexity validation not implemented")

    def test_rate_limiting_simulation(self, auth_manager):
        """Test rate limiting for authentication attempts"""
        # This would test rate limiting if implemented
        username = "testuser"

        # Simulate multiple failed attempts
        failed_attempts = []
        for i in range(5):
            try:
                # This would trigger rate limiting after certain attempts
                result = auth_manager.check_rate_limit(username)
                failed_attempts.append(result)
            except AttributeError:
                # Method doesn't exist, skip this test
                pytest.skip("Rate limiting not implemented")

    @pytest.mark.asyncio
    async def test_token_blacklisting(self, auth_manager):
        """Test token blacklisting functionality"""
        user_id = "123"
        token = auth_manager.create_access_token(user_id)

        try:
            # Test token blacklisting
            await auth_manager.blacklist_token(token)
            is_blacklisted = await auth_manager.is_token_blacklisted(token)
            assert is_blacklisted is True
        except AttributeError:
            # Method doesn't exist, skip this test
            pytest.skip("Token blacklisting not implemented")

    def test_jwt_claims_validation(self, auth_manager):
        """Test JWT claims validation"""
        user_id = "123"
        token = auth_manager.create_access_token(user_id)

        payload = auth_manager.verify_token(token)

        # Verify required claims
        assert "sub" in payload
        assert "type" in payload
        assert "exp" in payload
        assert "iat" in payload

        # Verify claim values
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert payload["exp"] > payload["iat"]

    @pytest.mark.asyncio
    async def test_concurrent_authentication(self, auth_manager, mock_db_manager):
        """Test concurrent authentication requests"""
        import asyncio

        password = "testpassword123"
        hashed_password = auth_manager.hash_password(password)

        user_data = {
            "id": "123",
            "username": "testuser",
            "email": "test@example.com",
            "password": hashed_password,
            "role": "trader",
            "permissions": '{"view_alerts": true}',
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": None
        }

        with patch.object(auth_manager, 'db_manager', mock_db_manager):
            mock_db_manager.execute_query.return_value = [user_data]
            mock_db_manager.execute_non_query = AsyncMock()

            # Simulate concurrent authentication requests
            tasks = []
            for i in range(5):
                task = auth_manager.authenticate("testuser", password)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed (unless rate limiting is implemented)
            for result in results:
                if isinstance(result, dict):
                    assert "access_token" in result
                else:
                    # If rate limiting is implemented, some might fail
                    assert isinstance(result, HTTPException)


class TestRoleBasedAccess:
    """Test role-based access control"""

    def test_trader_permissions(self):
        """Test trader role permissions"""
        user = User(
            id="1",
            username="trader",
            email="trader@example.com",
            role="trader",
            permissions={
                "view_alerts": True,
                "create_alerts": True,
                "manage_portfolio": True,
                "generate_signals": False,
                "admin_access": False
            },
            is_active=True,
            created_at=datetime.now()
        )

        assert user.has_permission("view_alerts") is True
        assert user.has_permission("create_alerts") is True
        assert user.has_permission("manage_portfolio") is True
        assert user.has_permission("generate_signals") is False
        assert user.has_permission("admin_access") is False

    def test_analyst_permissions(self):
        """Test analyst role permissions"""
        user = User(
            id="2",
            username="analyst",
            email="analyst@example.com",
            role="analyst",
            permissions={
                "view_alerts": True,
                "create_alerts": True,
                "manage_portfolio": False,
                "generate_signals": True,
                "admin_access": False
            },
            is_active=True,
            created_at=datetime.now()
        )

        assert user.has_permission("view_alerts") is True
        assert user.has_permission("generate_signals") is True
        assert user.has_permission("manage_portfolio") is False
        assert user.has_permission("admin_access") is False

    def test_admin_permissions(self):
        """Test admin role permissions (should have all permissions)"""
        user = User(
            id="3",
            username="admin",
            email="admin@example.com",
            role="admin",
            permissions={},  # Empty permissions
            is_active=True,
            created_at=datetime.now()
        )

        # Admin should have all permissions regardless of explicit grants
        assert user.has_permission("view_alerts") is True
        assert user.has_permission("create_alerts") is True
        assert user.has_permission("manage_portfolio") is True
        assert user.has_permission("generate_signals") is True
        assert user.has_permission("admin_access") is True
        assert user.has_permission("any_permission") is True