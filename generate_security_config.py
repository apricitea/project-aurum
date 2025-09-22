#!/usr/bin/env python3
"""
Security Setup Script for Project Aurum
Generates secure configuration and applies security enhancements
"""

import secrets
import os
from datetime import datetime

def generate_secure_secrets():
    """Generate secure secrets for production"""
    print("=== GENERATING SECURE SECRETS ===")
    
    jwt_secret = secrets.token_urlsafe(32)
    encryption_key = secrets.token_urlsafe(32)
    session_secret = secrets.token_urlsafe(32)
    
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print(f"SESSION_SECRET={session_secret}")
    print()
    print("IMPORTANT: Save these secrets securely and add to your .env file")
    
    return {
        "jwt_secret": jwt_secret,
        "encryption_key": encryption_key,
        "session_secret": session_secret
    }

def create_secure_env():
    """Create secure environment configuration"""
    secrets_dict = generate_secure_secrets()
    
    env_content = f"""# Project Aurum - Secure Configuration
# Generated: {datetime.now().isoformat()}

# Environment
ENVIRONMENT=production
DEBUG=false

# Security
JWT_SECRET_KEY={secrets_dict["jwt_secret"]}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
ENCRYPTION_KEY={secrets_dict["encryption_key"]}
SESSION_SECRET={secrets_dict["session_secret"]}

# Security Features
SECURITY_ENABLED=true
FORCE_HTTPS=true
RATE_LIMIT_ENABLED=true
API_RATE_LIMIT_PER_MINUTE=60
AUTH_RATE_LIMIT_PER_MINUTE=5

# Database (CHANGE PASSWORD!)
DB_PASSWORD=CHANGE_THIS_STRONG_PASSWORD_12_CHARS_MIN

# CORS (RESTRICT IN PRODUCTION!)
ALLOWED_ORIGINS=https://your-domain.com

# Password Policy
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_SPECIAL=true
PASSWORD_MAX_AGE_DAYS=90
"""
    
    with open(".env.secure", "w") as f:
        f.write(env_content)
    
    print("Created .env.secure template")
    print("Next steps:")
    print("1. Copy .env.secure to .env")
    print("2. Change DB_PASSWORD to a strong password")
    print("3. Update ALLOWED_ORIGINS for your domain")
    print("4. Review all security settings")

if __name__ == "__main__":
    create_secure_env()

