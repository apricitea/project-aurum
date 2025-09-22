"""
Security Configuration and Implementation for Project Aurum
Comprehensive security enhancements for production deployment
"""

import secrets
import hashlib
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import time
import re
import ipaddress

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration constants"""
    
    # JWT Security
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short for security
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Rate Limiting
    API_RATE_LIMIT_PER_MINUTE = 60
    AUTH_RATE_LIMIT_PER_MINUTE = 5
    FAILED_LOGIN_MAX_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    # Password Policy
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_MIN_SPECIAL_CHARS = 2
    
    # Session Security
    SESSION_TIMEOUT_MINUTES = 30
    MAX_CONCURRENT_SESSIONS = 3

class SecurityValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def validate_password_strength(password: str):
        """Validate password against security policy"""
        errors = []
        
        if len(password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {SecurityConfig.PASSWORD_MIN_LENGTH} characters")
        
        if SecurityConfig.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain uppercase letters")
        
        if SecurityConfig.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain lowercase letters")
        
        if SecurityConfig.PASSWORD_REQUIRE_DIGITS and not re.search(r"\d", password):
            errors.append("Password must contain digits")
        
        if SecurityConfig.PASSWORD_REQUIRE_SPECIAL:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            special_count = sum(1 for char in password if char in special_chars)
            if special_count < SecurityConfig.PASSWORD_MIN_SPECIAL_CHARS:
                errors.append(f"Password must contain at least {SecurityConfig.PASSWORD_MIN_SPECIAL_CHARS} special characters")
        
        return len(errors) == 0, errors

def generate_secure_jwt_secret():
    """Generate cryptographically secure JWT secret"""
    return secrets.token_urlsafe(32)

def hash_password_secure(password: str):
    """Securely hash password"""
    import bcrypt
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password_secure(password: str, hashed: str):
    """Verify password against hash"""
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

