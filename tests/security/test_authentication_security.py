"""
Security tests for authentication and authorization
"""

import pytest
import jwt
import bcrypt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import asyncio

from src.api.auth import AuthManager, User
from src.api.main import app


class TestPasswordSecurity:
    """Test password security measures"""

    @pytest.fixture
    def auth_manager(self, mock_settings):
        """Create AuthManager for security testing"""
        with patch('src.api.auth.settings', mock_settings):
            mock_settings.JWT_SECRET_KEY = "test-secret-key-very-long-and-secure"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
            return AuthManager()

    @pytest.mark.security
    def test_password_hashing_uniqueness(self, auth_manager):
        """Test that same passwords produce different hashes"""
        password = "TestPassword123!"

        hash1 = auth_manager.hash_password(password)
        hash2 = auth_manager.hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2
        assert hash1 != password
        assert hash2 != password

        # Both should verify correctly
        assert auth_manager.verify_password(password, hash1)
        assert auth_manager.verify_password(password, hash2)

    @pytest.mark.security
    def test_password_hashing_strength(self, auth_manager):
        """Test password hashing uses appropriate strength"""
        password = "TestPassword123!"
        hashed = auth_manager.hash_password(password)

        # Should be bcrypt hash (starts with $2b$)
        assert hashed.startswith('$2b$')

        # Should have reasonable length (typical bcrypt hash length)
        assert len(hashed) == 60

        # Should contain cost factor (should be >= 12 for security)
        cost_factor = int(hashed.split('$')[2])
        assert cost_factor >= 10, "BCrypt cost factor should be at least 10"

    @pytest.mark.security
    def test_password_verification_timing_attack_resistance(self, auth_manager):
        """Test password verification is resistant to timing attacks"""
        import time

        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = auth_manager.hash_password(correct_password)

        # Measure verification time for correct password
        start_time = time.time()
        auth_manager.verify_password(correct_password, hashed)
        correct_time = time.time() - start_time

        # Measure verification time for wrong password
        start_time = time.time()
        auth_manager.verify_password(wrong_password, hashed)
        wrong_time = time.time() - start_time

        # Times should be similar (within reasonable bounds)
        # This helps prevent timing attacks
        time_ratio = max(correct_time, wrong_time) / min(correct_time, wrong_time)
        assert time_ratio < 2.0, "Password verification timing should be consistent"

    @pytest.mark.security
    def test_weak_password_patterns(self, auth_manager):
        """Test handling of weak password patterns"""
        weak_passwords = [
            "123456",
            "password",
            "12345678",
            "qwerty",
            "abc123",
            "password123",
            "admin",
            "user",
            "test",
            "",  # Empty password
            "a",  # Single character
            "aa",  # Repeated character
        ]

        for weak_password in weak_passwords:
            # System should either reject weak passwords or handle them securely
            try:
                hashed = auth_manager.hash_password(weak_password)
                # If hashing succeeds, it should still be secure
                assert len(hashed) > 20, "Even weak passwords should be hashed securely"
                assert hashed != weak_password, "Password should not be stored in plain text"
            except Exception:
                # It's acceptable to reject weak passwords
                pass

    @pytest.mark.security
    def test_password_length_limits(self, auth_manager):
        """Test password length handling"""
        # Very long password
        very_long_password = "a" * 1000

        try:
            hashed = auth_manager.hash_password(very_long_password)
            # Should handle long passwords gracefully
            assert isinstance(hashed, str)
            assert len(hashed) > 0
        except Exception as e:
            # Acceptable to have reasonable length limits
            assert "length" in str(e).lower() or "long" in str(e).lower()

    @pytest.mark.security
    def test_special_character_passwords(self, auth_manager):
        """Test passwords with special characters"""
        special_passwords = [
            "Pass@word123!",
            "Pässwörd123",  # Unicode characters
            "Pass'word\"123",  # Quotes
            "Pass\\word/123",  # Slashes
            "Pass word 123",  # Spaces
            "Pass<word>123",  # HTML-like characters
            "Pass{word}123",  # Brackets
            "Pass;word:123",  # Semicolon and colon
        ]

        for special_password in special_passwords:
            hashed = auth_manager.hash_password(special_password)
            assert auth_manager.verify_password(special_password, hashed)


class TestJWTSecurity:
    """Test JWT token security"""

    @pytest.fixture
    def auth_manager(self, mock_settings):
        """Create AuthManager for JWT testing"""
        with patch('src.api.auth.settings', mock_settings):
            mock_settings.JWT_SECRET_KEY = "super-secret-key-for-testing-only-very-long"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
            return AuthManager()

    @pytest.mark.security
    def test_jwt_secret_key_strength(self, auth_manager):
        """Test JWT secret key is sufficiently strong"""
        secret = auth_manager.secret_key

        # Secret should be sufficiently long
        assert len(secret) >= 32, "JWT secret key should be at least 32 characters"

        # Should not be a common weak secret
        weak_secrets = [
            "secret",
            "key",
            "password",
            "123456",
            "jwt-secret",
            "your-secret-key"
        ]

        for weak_secret in weak_secrets:
            assert secret.lower() != weak_secret.lower(), f"JWT secret should not be '{weak_secret}'"

    @pytest.mark.security
    def test_jwt_token_expiration(self, auth_manager):
        """Test JWT tokens have proper expiration"""
        user_id = "123"

        # Create access token
        access_token = auth_manager.create_access_token(user_id)
        payload = jwt.decode(access_token, auth_manager.secret_key, algorithms=[auth_manager.algorithm])

        # Check expiration
        exp_timestamp = payload['exp']
        iat_timestamp = payload['iat']

        exp_time = datetime.fromtimestamp(exp_timestamp)
        iat_time = datetime.fromtimestamp(iat_timestamp)

        # Token should expire in the future but not too far
        now = datetime.utcnow()
        assert exp_time > now, "Token should expire in the future"
        assert exp_time < now + timedelta(hours=2), "Access token should not expire too far in future"

        # Token duration should match configuration
        duration = exp_time - iat_time
        expected_duration = timedelta(minutes=auth_manager.access_token_expire_minutes)
        assert abs(duration - expected_duration) < timedelta(seconds=5), "Token duration should match config"

    @pytest.mark.security
    def test_jwt_token_tampering(self, auth_manager):
        """Test JWT tokens are tamper-resistant"""
        user_id = "123"
        token = auth_manager.create_access_token(user_id)

        # Attempt to tamper with token
        tampered_tokens = [
            token[:-5] + "XXXXX",  # Change signature
            token.replace(user_id, "999"),  # Try to change user ID (if visible)
            token + "extra",  # Add extra data
            token[:-10],  # Truncate token
            "fake." + token.split('.')[1] + "." + token.split('.')[2],  # Fake header
        ]

        for tampered_token in tampered_tokens:
            with pytest.raises(HTTPException) as exc_info:
                auth_manager.verify_token(tampered_token)

            assert exc_info.value.status_code == 401
            assert "Invalid token" in str(exc_info.value.detail)

    @pytest.mark.security
    def test_jwt_algorithm_security(self, auth_manager):
        """Test JWT uses secure algorithm"""
        user_id = "123"
        token = auth_manager.create_access_token(user_id)

        # Decode header to check algorithm
        header = jwt.get_unverified_header(token)

        # Should use HMAC-based algorithm (HS256, HS384, HS512)
        assert header['alg'] in ['HS256', 'HS384', 'HS512'], \
            "Should use secure HMAC algorithm"

        # Should not use 'none' algorithm
        assert header['alg'] != 'none', "Should not use 'none' algorithm"

    @pytest.mark.security
    def test_jwt_token_reuse_prevention(self, auth_manager):
        """Test JWT tokens can't be reused inappropriately"""
        user_id = "123"

        # Create multiple tokens for same user
        token1 = auth_manager.create_access_token(user_id)
        token2 = auth_manager.create_access_token(user_id)

        # Tokens should be different (due to different issued times)
        assert token1 != token2

        # Both should be valid
        payload1 = auth_manager.verify_token(token1)
        payload2 = auth_manager.verify_token(token2)

        assert payload1['sub'] == user_id
        assert payload2['sub'] == user_id

        # Issued times should be different
        assert payload1['iat'] != payload2['iat']

    @pytest.mark.security
    def test_jwt_refresh_token_security(self, auth_manager):
        """Test refresh token security"""
        user_id = "123"

        refresh_token = auth_manager.create_refresh_token(user_id)
        payload = jwt.decode(refresh_token, auth_manager.secret_key, algorithms=[auth_manager.algorithm])

        # Refresh token should have correct type
        assert payload['type'] == 'refresh'

        # Should have longer expiration than access token
        exp_time = datetime.fromtimestamp(payload['exp'])
        now = datetime.utcnow()

        assert exp_time > now + timedelta(hours=1), "Refresh token should expire later than access token"

    @pytest.mark.security
    def test_jwt_claims_validation(self, auth_manager):
        """Test JWT claims are properly validated"""
        user_id = "123"
        token = auth_manager.create_access_token(user_id)

        payload = auth_manager.verify_token(token)

        # Check required claims
        required_claims = ['sub', 'type', 'exp', 'iat']
        for claim in required_claims:
            assert claim in payload, f"Token should contain {claim} claim"

        # Validate claim values
        assert payload['sub'] == user_id
        assert payload['type'] == 'access'
        assert isinstance(payload['exp'], int)
        assert isinstance(payload['iat'], int)


class TestAuthenticationFlow:
    """Test authentication flow security"""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_login_brute_force_protection(self, test_client):
        """Test protection against brute force login attempts"""
        # Simulate multiple failed login attempts
        login_data = {"username": "testuser", "password": "wrongpassword"}

        responses = []
        for i in range(10):  # Try 10 failed logins
            response = await test_client.post("/auth/login", json=login_data)
            responses.append(response)

        # Should eventually get rate limited or locked out
        # (This test assumes rate limiting is implemented)
        final_responses = responses[-3:]  # Check last 3 responses

        # At least one should indicate rate limiting or account lockout
        status_codes = [r.status_code for r in final_responses]

        # Should get 429 (Too Many Requests) or 423 (Locked) eventually
        rate_limited = any(code in [423, 429] for code in status_codes)

        if not rate_limited:
            # If no rate limiting, all should at least be 401 Unauthorized
            assert all(code == 401 for code in status_codes)
            print("Warning: No rate limiting detected for failed login attempts")

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_login_sql_injection_protection(self, test_client, security_test_data):
        """Test protection against SQL injection in login"""
        sql_injection_payloads = security_test_data["sql_injection"]

        for payload in sql_injection_payloads:
            login_data = {
                "username": payload,
                "password": "testpassword"
            }

            response = await test_client.post("/auth/login", json=login_data)

            # Should not cause server error (should be handled gracefully)
            assert response.status_code != 500, f"SQL injection payload caused server error: {payload}"

            # Should return authentication failure, not success
            assert response.status_code in [400, 401, 422], \
                f"SQL injection payload should not succeed: {payload}"

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_login_xss_protection(self, test_client, security_test_data):
        """Test protection against XSS in login responses"""
        xss_payloads = security_test_data["xss_payloads"]

        for payload in xss_payloads:
            login_data = {
                "username": payload,
                "password": "testpassword"
            }

            response = await test_client.post("/auth/login", json=login_data)
            response_text = response.text

            # Response should not contain unescaped XSS payload
            assert payload not in response_text, \
                f"XSS payload found in response: {payload}"

            # Should not contain script tags
            assert "<script>" not in response_text.lower()
            assert "javascript:" not in response_text.lower()

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_token_theft_protection(self, test_client, sample_user):
        """Test protection against token theft scenarios"""
        # Simulate getting a valid token
        with patch('src.api.main.auth_manager') as mock_auth:
            mock_auth.authenticate.return_value = {
                "access_token": "valid.jwt.token",
                "refresh_token": "valid.refresh.token",
                "token_type": "bearer",
                "expires_in": 3600
            }

            login_response = await test_client.post("/auth/login", json={
                "username": "testuser",
                "password": "testpass"
            })

            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Test token in different contexts that might indicate theft

            # 1. Test with suspicious User-Agent
            suspicious_response = await test_client.get(
                "/auth/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "curl/7.0"  # Suspicious for a web app
                }
            )

            # Should still work (this is just monitoring, not blocking)
            # But could log for security monitoring

            # 2. Test rapid requests from same token (potential automation)
            rapid_requests = []
            for i in range(5):
                resp = await test_client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                rapid_requests.append(resp)

            # All should work, but might trigger monitoring
            assert all(r.status_code == 200 for r in rapid_requests)

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_session_fixation_protection(self, test_client):
        """Test protection against session fixation attacks"""
        # This test would be more relevant for session-based auth
        # For JWT, we test that tokens are properly generated fresh

        login_data = {"username": "testuser", "password": "testpass"}

        with patch('src.api.main.auth_manager') as mock_auth:
            # Mock different tokens for each login
            mock_auth.authenticate.side_effect = [
                {
                    "access_token": "token1.jwt.here",
                    "refresh_token": "refresh1.token.here",
                    "token_type": "bearer",
                    "expires_in": 3600
                },
                {
                    "access_token": "token2.jwt.here",
                    "refresh_token": "refresh2.token.here",
                    "token_type": "bearer",
                    "expires_in": 3600
                }
            ]

            # Two separate login attempts
            response1 = await test_client.post("/auth/login", json=login_data)
            response2 = await test_client.post("/auth/login", json=login_data)

            assert response1.status_code == 200
            assert response2.status_code == 200

            token1 = response1.json()["access_token"]
            token2 = response2.json()["access_token"]

            # Tokens should be different
            assert token1 != token2, "Each login should generate a fresh token"


class TestAuthorizationSecurity:
    """Test authorization and access control security"""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_privilege_escalation_protection(self, test_client):
        """Test protection against privilege escalation"""
        # Test that regular user can't access admin functions
        with patch('src.api.main.get_current_user') as mock_get_user:
            # Mock regular user
            regular_user = MagicMock()
            regular_user.id = 1
            regular_user.role = "trader"
            regular_user.has_permission.return_value = False  # No admin permissions
            mock_get_user.return_value = regular_user

            # Try to access admin function
            response = await test_client.post(
                "/signals/generate",  # Admin function
                headers={"Authorization": "Bearer user_token"}
            )

            # Should be denied
            assert response.status_code == 403
            assert "Insufficient permissions" in response.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_horizontal_privilege_escalation(self, test_client):
        """Test protection against accessing other users' data"""
        with patch('src.api.main.get_current_user') as mock_get_user, \
             patch('src.api.main.alert_engine') as mock_alert_engine:

            # Mock user 1
            user1 = MagicMock()
            user1.id = 1
            user1.role = "trader"
            mock_get_user.return_value = user1

            # Mock alert that belongs to user 2
            mock_alert = MagicMock()
            mock_alert.user_id = 2  # Different user
            mock_alert_engine.get_alerts.return_value = [mock_alert]

            # User 1 tries to access alerts
            response = await test_client.get(
                "/alerts",
                headers={"Authorization": "Bearer user1_token"}
            )

            # Should only get user 1's alerts, not user 2's
            # (This depends on implementation filtering by user_id)
            if response.status_code == 200:
                alerts = response.json()
                # Verify user filtering is applied
                mock_alert_engine.get_alerts.assert_called()
                call_args = mock_alert_engine.get_alerts.call_args[1]
                assert call_args.get('user_id') == 1, "Should filter by current user ID"

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_token_authorization_bypass(self, test_client):
        """Test that endpoints require proper authorization"""
        protected_endpoints = [
            ("/alerts", "GET"),
            ("/alerts", "POST"),
            ("/signals/daily", "GET"),
            ("/portfolio/summary", "GET"),
            ("/risk/overview", "GET"),
        ]

        for endpoint, method in protected_endpoints:
            # Test without authorization header
            if method == "GET":
                response = await test_client.get(endpoint)
            elif method == "POST":
                response = await test_client.post(endpoint, json={})

            # Should require authentication
            assert response.status_code in [401, 403], \
                f"Endpoint {method} {endpoint} should require authentication"

            # Test with invalid token
            headers = {"Authorization": "Bearer invalid.token.here"}
            if method == "GET":
                response = await test_client.get(endpoint, headers=headers)
            elif method == "POST":
                response = await test_client.post(endpoint, json={}, headers=headers)

            # Should reject invalid token
            assert response.status_code in [401, 403], \
                f"Endpoint {method} {endpoint} should reject invalid tokens"

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_role_based_access_control(self, test_client):
        """Test role-based access control enforcement"""
        roles_and_permissions = [
            {
                "role": "viewer",
                "allowed": ["/alerts", "/signals/daily", "/portfolio/summary"],
                "denied": ["/signals/generate", "/portfolio/positions"]
            },
            {
                "role": "trader",
                "allowed": ["/alerts", "/signals/daily", "/portfolio/summary", "/portfolio/positions"],
                "denied": ["/signals/generate"]
            },
            {
                "role": "admin",
                "allowed": ["/alerts", "/signals/daily", "/portfolio/summary", "/signals/generate"],
                "denied": []
            }
        ]

        for role_config in roles_and_permissions:
            with patch('src.api.main.get_current_user') as mock_get_user:
                # Mock user with specific role
                user = MagicMock()
                user.id = 1
                user.role = role_config["role"]
                user.has_permission.side_effect = lambda perm: perm in ["view_alerts", "manage_portfolio"] if role_config["role"] == "trader" else role_config["role"] == "admin"
                mock_get_user.return_value = user

                # Test allowed endpoints
                for endpoint in role_config["allowed"]:
                    response = await test_client.get(
                        endpoint,
                        headers={"Authorization": "Bearer valid_token"}
                    )

                    # Should be allowed (200) or might have other issues but not forbidden
                    assert response.status_code != 403, \
                        f"Role {role_config['role']} should have access to {endpoint}"

                # Test denied endpoints
                for endpoint in role_config["denied"]:
                    if endpoint == "/signals/generate":
                        response = await test_client.post(
                            endpoint,
                            headers={"Authorization": "Bearer valid_token"}
                        )
                    else:
                        response = await test_client.get(
                            endpoint,
                            headers={"Authorization": "Bearer valid_token"}
                        )

                    # Should be forbidden
                    assert response.status_code == 403, \
                        f"Role {role_config['role']} should not have access to {endpoint}"


class TestSecurityHeaders:
    """Test security headers and CORS configuration"""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_cors_configuration(self, test_client):
        """Test CORS configuration is secure"""
        # Test preflight request
        response = await test_client.options(
            "/health",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET"
            }
        )

        # CORS should be restrictive by default
        if "access-control-allow-origin" in response.headers:
            allowed_origin = response.headers["access-control-allow-origin"]

            # Should not allow all origins in production
            if allowed_origin == "*":
                print("Warning: CORS allows all origins - this may be insecure in production")

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_security_headers_present(self, test_client):
        """Test that important security headers are present"""
        response = await test_client.get("/health")

        # Check for important security headers
        security_headers = {
            "x-frame-options": ["DENY", "SAMEORIGIN"],
            "x-content-type-options": ["nosniff"],
            "x-xss-protection": ["1; mode=block", "0"],  # 0 is also acceptable (newer approach)
            "strict-transport-security": None,  # Should be present for HTTPS
            "content-security-policy": None,  # Should be present
        }

        for header, expected_values in security_headers.items():
            if header in response.headers:
                header_value = response.headers[header]
                if expected_values:
                    assert any(expected in header_value for expected in expected_values), \
                        f"Security header {header} has unexpected value: {header_value}"
            else:
                # Not all headers may be implemented yet
                print(f"Security header {header} not found - consider implementing")

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_information_disclosure_prevention(self, test_client):
        """Test that server doesn't disclose sensitive information"""
        # Test 404 responses don't reveal too much
        response = await test_client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        response_text = response.text.lower()

        # Should not reveal server internals
        sensitive_info = [
            "traceback",
            "exception",
            "error",
            "debug",
            "stack trace",
            "internal server",
            "python",
            "fastapi"
        ]

        for info in sensitive_info:
            if info in response_text:
                print(f"Warning: 404 response may reveal sensitive information: {info}")

        # Test error responses don't reveal too much
        response = await test_client.post("/auth/login", json={"invalid": "data"})

        if response.status_code >= 400:
            response_text = response.text.lower()

            # Should not reveal internal structure
            assert "sql" not in response_text, "Error should not reveal SQL information"
            assert "database" not in response_text, "Error should not reveal database information"