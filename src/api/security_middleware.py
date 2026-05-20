"""
Comprehensive Security Middleware for Indonesian Quantitative Trading Alert System
Production-grade security implementation with OWASP compliance
"""

import time
import hashlib
import secrets
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
import redis.asyncio as aioredis
from collections import defaultdict, deque
import ipaddress
import re
import json

from .config import settings

logger = logging.getLogger(__name__)

class SecurityHeaders:
    """Security headers implementation"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get comprehensive security headers"""
        return {
            # Content Security Policy - Prevents XSS and code injection
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https: wss: ws:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            
            # HTTP Strict Transport Security - Forces HTTPS
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # X-Content-Type-Options - Prevents MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # X-Frame-Options - Prevents clickjacking
            "X-Frame-Options": "DENY",
            
            # X-XSS-Protection - Enables XSS filtering
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer-Policy - Controls referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions-Policy - Controls browser features
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=(), "
                "accelerometer=(), ambient-light-sensor=()"
            ),
            
            # Cross-Origin-Embedder-Policy
            "Cross-Origin-Embedder-Policy": "require-corp",
            
            # Cross-Origin-Opener-Policy
            "Cross-Origin-Opener-Policy": "same-origin",
            
            # Cross-Origin-Resource-Policy
            "Cross-Origin-Resource-Policy": "same-origin",
            
            # Server header removal
            "Server": "Aurum-Trading-System/1.0",
            
            # Cache control for sensitive endpoints
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }


class RateLimiter:
    """Advanced rate limiting with Redis backend"""
    
    def __init__(self):
        self.redis_client = None
        self.local_cache = defaultdict(lambda: deque(maxlen=1000))
        self.failed_attempts = defaultdict(lambda: {"count": 0, "reset_time": time.time()})
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(
                settings.get_redis_url(),
                decode_responses=True,
                health_check_interval=30
            )
            await self.redis_client.ping()
            logger.info("Rate limiter Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed, using local cache: {e}")
            self.redis_client = None
    
    async def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is rate limited"""
        current_time = time.time()
        
        if self.redis_client:
            return await self._redis_rate_limit(key, max_requests, window_seconds, current_time)
        else:
            return await self._local_rate_limit(key, max_requests, window_seconds, current_time)
    
    async def _redis_rate_limit(self, key: str, max_requests: int, window_seconds: int, current_time: float) -> bool:
        """Redis-based rate limiting"""
        try:
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, current_time - window_seconds)
            pipe.zcard(key)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            
            current_requests = results[1]
            return current_requests >= max_requests
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            return False
    
    async def _local_rate_limit(self, key: str, max_requests: int, window_seconds: int, current_time: float) -> bool:
        """Local memory-based rate limiting"""
        requests = self.local_cache[key]
        
        # Remove old requests
        while requests and requests[0] < current_time - window_seconds:
            requests.popleft()
        
        # Check if limit exceeded
        if len(requests) >= max_requests:
            return True
        
        # Add current request
        requests.append(current_time)
        return False


class InputSanitizer:
    """Advanced input sanitization and validation"""
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\'\s*(OR|AND)\s*\'.+?\'\s*(OR|AND)\s*\')",
        r"(\bxp_\w+)",
        r"(\bsp_\w+)"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>"
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.\/",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
        r"..%252f",
        r"..%255c"
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Length check
        if len(value) > max_length:
            raise ValueError(f"Input too long (max {max_length} characters)")
        
        # Check for SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potential SQL injection detected")
        
        # Check for XSS
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potential XSS attack detected")
        
        # Check for path traversal
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potential path traversal detected")
        
        # Remove null bytes and control characters
        value = value.replace('\x00', '')
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        return value.strip()
    
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        return email.lower().strip()
    
    @classmethod
    def validate_stock_code(cls, stock_code: str) -> str:
        """Validate stock code format"""
        # Indonesian stock codes: BBCA, TLKM, ASII, etc.
        stock_pattern = r'^[A-Z]{3,4}$'
        if not re.match(stock_pattern, stock_code.upper()):
            raise ValueError("Invalid stock code format")
        return stock_code.upper()


class SecurityMonitor:
    """Security event monitoring and alerting"""
    
    def __init__(self):
        self.suspicious_activities = defaultdict(list)
        self.security_events = deque(maxlen=10000)
    
    async def log_security_event(self, event_type: str, details: Dict[str, Any], severity: str = "info"):
        """Log security event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "severity": severity,
            "details": details,
            "event_id": secrets.token_hex(16)
        }
        
        self.security_events.append(event)
        
        # Log to application logger
        log_level = getattr(logging, severity.upper(), logging.INFO)
        logger.log(log_level, f"Security Event [{event_type}]: {json.dumps(details)}")
    
    async def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary"""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        recent_events = [
            e for e in self.security_events
            if datetime.fromisoformat(e["timestamp"]) > last_hour
        ]
        
        daily_events = [
            e for e in self.security_events
            if datetime.fromisoformat(e["timestamp"]) > last_day
        ]
        
        return {
            "total_events_24h": len(daily_events),
            "total_events_1h": len(recent_events),
            "critical_events_24h": len([e for e in daily_events if e["severity"] == "critical"]),
            "warning_events_24h": len([e for e in daily_events if e["severity"] == "warning"])
        }


# Global instances
rate_limiter = RateLimiter()
security_monitor = SecurityMonitor()

async def initialize_security():
    """Initialize security components"""
    await rate_limiter.initialize()
    logger.info("Security middleware initialized")

async def get_security_status() -> Dict[str, Any]:
    """Get comprehensive security status"""
    return {
        "rate_limiter_status": "active" if rate_limiter.redis_client else "local_fallback",
        "security_monitor_status": "active",
        "security_summary": await security_monitor.get_security_summary()
    }

