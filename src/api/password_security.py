"""
Password Security Module for Indonesian Quantitative Trading Alert System
Implements strong password policies and secure password handling
"""

import re
import secrets
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import bcrypt
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PasswordPolicy:
    """Password policy configuration"""
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_chars: bool = True
    min_special_chars: int = 2
    max_consecutive_chars: int = 3
    prevent_username_inclusion: bool = True
    prevent_common_passwords: bool = True
    prevent_keyboard_patterns: bool = True
    prevent_repeated_chars: int = 3
    history_check_count: int = 5
    min_age_hours: int = 24
    max_age_days: int = 90

class PasswordValidator:
    """Comprehensive password validation"""
    
    # Common weak passwords
    COMMON_PASSWORDS = {
        'password', '123456', '12345678', 'qwerty', 'abc123', 'password123',
        'admin', 'letmein', 'welcome', 'monkey', 'dragon', 'master',
        'sunshine', 'princess', 'football', 'baseball', 'superman', 'access',
        '123456789', 'iloveyou', 'trustno1', 'loveme', 'hello', 'welcome123',
        'admin123', 'root', 'toor', 'pass', 'test', 'guest', 'user',
        '1234567890', 'administrator', 'changeme', 'login', 'god',
        # Indonesian common passwords
        'indonesia', 'jakarta', 'bandung', 'surabaya', 'semarang',
        'yogyakarta', 'medan', 'palembang', 'makassar', 'depok',
        'tangerang', 'bekasi', 'bogor', 'batam', 'pekanbaru',
        'garuda', 'nusantara', 'merdeka', 'pancasila', 'bhinneka'
    }
    
    # Keyboard patterns
    KEYBOARD_PATTERNS = [
        'qwerty', 'qwertyui', 'asdf', 'asdfgh', 'zxcv', 'zxcvbn',
        '123456', '1234567', '12345678', '123456789', '1234567890',
        'abcdef', 'abcdefg', 'abcdefgh'
    ]
    
    # Special characters that are required
    SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    def __init__(self, policy: PasswordPolicy = None):
        self.policy = policy or PasswordPolicy()
    
    def validate_password(self, password: str, username: str = None, 
                         password_history: List[str] = None) -> Tuple[bool, List[str]]:
        """
        Comprehensive password validation
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        if not password:
            errors.append("Password is required")
            return False, errors
        
        # Length validation
        if len(password) < self.policy.min_length:
            errors.append(f"Password must be at least {self.policy.min_length} characters long")
        
        if len(password) > self.policy.max_length:
            errors.append(f"Password must not exceed {self.policy.max_length} characters")
        
        # Character requirements
        if self.policy.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.policy.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.policy.require_digits and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if self.policy.require_special_chars:
            special_count = sum(1 for char in password if char in self.SPECIAL_CHARS)
            if special_count < self.policy.min_special_chars:
                errors.append(f"Password must contain at least {self.policy.min_special_chars} special characters ({self.SPECIAL_CHARS})")
        
        return len(errors) == 0, errors

# Global password manager functions
def validate_password(password: str, username: str = None) -> Dict[str, any]:
    """Convenience function for password validation"""
    validator = PasswordValidator()
    is_valid, errors = validator.validate_password(password, username)
    
    return {
        "is_valid": is_valid,
        "errors": errors,
        "strength_score": 75 if is_valid else 25,
        "strength_label": "Strong" if is_valid else "Weak"
    }

def hash_password(password: str) -> str:
    """Convenience function for password hashing"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Convenience function for password verification"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def generate_secure_password(length: int = 16) -> str:
    """Generate a secure password"""
    uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    lowercase = 'abcdefghijklmnopqrstuvwxyz'
    digits = '0123456789'
    special = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    # Ensure the generated password meets PasswordPolicy.min_special_chars (= 2)
    # as well as one of each other required class.
    password_chars = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special),
        secrets.choice(special),
    ]

    all_chars = uppercase + lowercase + digits + special
    for _ in range(max(0, length - 5)):
        password_chars.append(secrets.choice(all_chars))
    
    # Shuffle the password
    secrets.SystemRandom().shuffle(password_chars)
    
    return ''.join(password_chars)
