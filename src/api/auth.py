"""
Authentication and Authorization module for Indonesian Quantitative Trading System
JWT-based authentication with role-based access control
"""

import jwt
import bcrypt
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg
from pydantic import BaseModel

from .config import settings
from .database import DatabaseManager, get_db_manager
from .password_security import validate_password as check_password_strength

logger = logging.getLogger(__name__)

security = HTTPBearer()


class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: str
    role: str
    permissions: Dict[str, bool]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return self.permissions.get(permission, False) or self.role == "admin"


class AuthManager:
    """Authentication manager"""

    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

        # Default role permissions
        self.role_permissions = {
            "admin": {
                "view_dashboard": True,
                "view_signals": True,
                "view_portfolio": True,
                "view_alerts": True,
                "manage_portfolio": True,
                "generate_signals": True,
                "manage_users": True,
                "manage_settings": True,
                "view_risk_metrics": True,
                "manage_risk_limits": True,
                "view_analytics": True,
                "generate_reports": True
            },
            "trader": {
                "view_dashboard": True,
                "view_signals": True,
                "view_portfolio": True,
                "view_alerts": True,
                "manage_portfolio": True,
                "generate_signals": False,
                "manage_users": False,
                "manage_settings": False,
                "view_risk_metrics": True,
                "manage_risk_limits": False,
                "view_analytics": True,
                "generate_reports": True
            },
            "viewer": {
                "view_dashboard": True,
                "view_signals": True,
                "view_portfolio": True,
                "view_alerts": True,
                "manage_portfolio": False,
                "generate_signals": False,
                "manage_users": False,
                "manage_settings": False,
                "view_risk_metrics": True,
                "manage_risk_limits": False,
                "view_analytics": True,
                "generate_reports": False
            },
            "api_user": {
                "view_dashboard": False,
                "view_signals": True,
                "view_portfolio": True,
                "view_alerts": True,
                "manage_portfolio": False,
                "generate_signals": False,
                "manage_users": False,
                "manage_settings": False,
                "view_risk_metrics": True,
                "manage_risk_limits": False,
                "view_analytics": True,
                "generate_reports": True
            }
        }

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt with rounds=12"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except (jwt.PyJWTError, Exception):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens"""
        try:
            db_manager = get_db_manager()

            async with db_manager.get_connection() as conn:
                user_row = await conn.fetchrow(
                    "SELECT * FROM users WHERE username = $1 AND is_active = true",
                    username
                )

            if not user_row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )

            # Verify password
            if not self.verify_password(password, user_row['password_hash']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )

            # Get user permissions
            user_permissions = user_row.get('permissions', {})
            role_permissions = self.role_permissions.get(user_row['role'], {})

            # Merge role permissions with user-specific permissions
            combined_permissions = {**role_permissions, **user_permissions}

            # Create token payload
            token_data = {
                "sub": str(user_row['id']),
                "username": user_row['username'],
                "email": user_row['email'],
                "role": user_row['role'],
                "permissions": combined_permissions
            }

            # Generate tokens
            access_token = self.create_access_token(token_data)
            refresh_token = self.create_refresh_token({"sub": str(user_row['id'])})

            # Update last login
            async with db_manager.get_connection() as conn:
                await conn.execute(
                    "UPDATE users SET last_login = NOW() WHERE id = $1",
                    user_row['id']
                )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user_row['id']),
                    "username": user_row['username'],
                    "email": user_row['email'],
                    "role": user_row['role'],
                    "permissions": combined_permissions
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            # Decode refresh token
            payload = self.decode_token(refresh_token)

            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            # Get user from database
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )

            db_manager = get_db_manager()

            async with db_manager.get_connection() as conn:
                user_row = await conn.fetchrow(
                    "SELECT * FROM users WHERE id = $1 AND is_active = true",
                    user_id
                )

            if not user_row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )

            # Get user permissions
            user_permissions = user_row.get('permissions', {})
            role_permissions = self.role_permissions.get(user_row['role'], {})
            combined_permissions = {**role_permissions, **user_permissions}

            # Create new token payload
            token_data = {
                "sub": str(user_row['id']),
                "username": user_row['username'],
                "email": user_row['email'],
                "role": user_row['role'],
                "permissions": combined_permissions
            }

            # Generate new access token
            new_access_token = self.create_access_token(token_data)

            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh service error"
            )

    async def get_user_from_token(self, token: str) -> User:
        """Get user object from JWT token"""
        payload = self.decode_token(token)

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Create user object from token payload
        user = User(
            id=user_id,
            username=payload.get("username", ""),
            email=payload.get("email", ""),
            role=payload.get("role", ""),
            permissions=payload.get("permissions", {}),
            is_active=True,
            created_at=datetime.now()  # This would come from database in real implementation
        )

        return user

    async def create_user(self, username: str, email: str, password: str,
                         role: str = "trader", permissions: Dict[str, bool] = None) -> Dict[str, Any]:
        """Create new user"""
        try:
            # Enforce password policy before doing anything else
            strength = check_password_strength(password, username=username)
            if not strength["is_valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Password does not meet requirements: {'; '.join(strength['errors'])}"
                )

            # Hash password
            password_hash = self.hash_password(password)

            # Get role permissions
            role_permissions = self.role_permissions.get(role, {})
            user_permissions = permissions or {}
            combined_permissions = {**role_permissions, **user_permissions}

            db_manager = get_db_manager()

            async with db_manager.get_transaction() as conn:
                # Check if username or email already exists
                existing = await conn.fetchrow(
                    "SELECT id FROM users WHERE username = $1 OR email = $2",
                    username, email
                )

                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username or email already exists"
                    )

                # Create user
                user_row = await conn.fetchrow("""
                    INSERT INTO users (username, email, password_hash, role, permissions)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id, username, email, role, created_at
                """, username, email, password_hash, role, combined_permissions)

            return {
                "id": str(user_row['id']),
                "username": user_row['username'],
                "email": user_row['email'],
                "role": user_row['role'],
                "permissions": combined_permissions,
                "created_at": user_row['created_at'].isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User creation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation service error"
            )

    async def update_user_permissions(self, user_id: str,
                                    permissions: Dict[str, bool]) -> bool:
        """Update user permissions"""
        try:
            async with get_db_manager().get_connection() as conn:
                await conn.execute(
                    "UPDATE users SET permissions = $2 WHERE id = $1",
                    user_id, permissions
                )
            return True
        except Exception as e:
            logger.error(f"Permission update error: {str(e)}")
            return False

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        try:
            async with get_db_manager().get_connection() as conn:
                await conn.execute(
                    "UPDATE users SET is_active = false WHERE id = $1",
                    user_id
                )
            return True
        except Exception as e:
            logger.error(f"User deactivation error: {str(e)}")
            return False


# Global auth manager instance
auth_manager = AuthManager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """FastAPI dependency to get current authenticated user"""
    try:
        token = credentials.credentials
        user = await auth_manager.get_user_from_token(token)
        return user
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def permission_dependency(current_user: User = Depends(get_current_user)):
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    return permission_dependency


def require_role(role: str):
    """Decorator to require specific role"""
    def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return current_user
    return role_dependency


# Permission decorators for common operations
require_admin = require_role("admin")
require_trader = require_permission("manage_portfolio")
require_signal_generation = require_permission("generate_signals")
require_user_management = require_permission("manage_users")
require_settings_management = require_permission("manage_settings")
require_risk_management = require_permission("manage_risk_limits")