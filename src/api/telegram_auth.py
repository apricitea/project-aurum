"""
Telegram Authentication System for Indonesian Quantitative Trading System
Handles user authentication, session management, and authorization for Telegram bot
"""

import asyncio
import logging
import secrets
import hashlib
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from functools import wraps
import json

from telegram import Update
from telegram.ext import ContextTypes

from .database import DatabaseManager
from .config import settings

logger = logging.getLogger(__name__)


class TelegramAuthManager:
    """
    Manages Telegram user authentication and authorization
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.redis_client = None

        # Authentication configuration
        self.token_expiry_minutes = 15  # Auth tokens expire in 15 minutes
        self.session_expiry_days = 7  # Sessions last 7 days

        # Rate limiting configuration
        self.auth_attempt_limit = 5  # Max auth attempts per chat_id
        self.auth_attempt_window = 300  # 5 minutes window for rate limiting

    async def initialize(self, redis_client):
        """Initialize auth manager with Redis client"""
        self.redis_client = redis_client
        logger.info("Telegram auth manager initialized")

    async def generate_auth_token(self, telegram_chat_id: int, telegram_username: str = None) -> Dict[str, Any]:
        """
        Generate authentication token for Telegram user to link account

        Args:
            telegram_chat_id: Telegram chat ID
            telegram_username: Optional Telegram username

        Returns:
            Dict containing token and auth URL
        """
        try:
            # Check rate limiting
            if not await self._check_auth_rate_limit(telegram_chat_id):
                raise ValueError("Too many authentication attempts. Please try again later.")

            # Generate secure token
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            # Store token in database
            async with self.db_manager.get_transaction() as conn:
                await conn.execute("""
                    INSERT INTO telegram_auth_tokens
                    (token_hash, telegram_chat_id, telegram_username, created_at, expires_at)
                    VALUES ($1, $2, $3, NOW(), NOW() + INTERVAL '15 minutes')
                """, token_hash, telegram_chat_id, telegram_username)

            # Cache token in Redis for quick verification
            await self.redis_client.setex(
                f"telegram_auth_token:{token_hash}",
                self.token_expiry_minutes * 60,
                json.dumps({
                    'telegram_chat_id': telegram_chat_id,
                    'telegram_username': telegram_username,
                    'created_at': datetime.now().isoformat()
                })
            )

            # Increment auth attempt counter
            await self._increment_auth_attempts(telegram_chat_id)

            # Generate auth URL
            auth_url = f"{settings.WEB_APP_URL}/telegram-auth?token={token}"

            logger.info(f"Auth token generated for chat_id: {telegram_chat_id}")

            return {
                'token': token,
                'auth_url': auth_url,
                'expires_in_minutes': self.token_expiry_minutes,
                'expires_at': (datetime.now() + timedelta(minutes=self.token_expiry_minutes)).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate auth token: {str(e)}")
            raise

    async def verify_auth_token(self, token: str, user_id: str) -> bool:
        """
        Verify authentication token and link Telegram account to user

        Args:
            token: Authentication token from user
            user_id: User ID from authenticated web session

        Returns:
            bool: True if token verified and account linked successfully
        """
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            # Check Redis cache first
            cached_token = await self.redis_client.get(f"telegram_auth_token:{token_hash}")

            if not cached_token:
                # Check database
                async with self.db_manager.get_connection() as conn:
                    token_data = await conn.fetchrow("""
                        SELECT telegram_chat_id, telegram_username, expires_at
                        FROM telegram_auth_tokens
                        WHERE token_hash = $1 AND used_at IS NULL
                    """, token_hash)

                    if not token_data:
                        logger.warning(f"Invalid or expired auth token")
                        return False

                    # Check expiration
                    if token_data['expires_at'] < datetime.now():
                        logger.warning(f"Auth token expired")
                        return False

                    telegram_chat_id = token_data['telegram_chat_id']
                    telegram_username = token_data['telegram_username']
            else:
                token_info = json.loads(cached_token)
                telegram_chat_id = token_info['telegram_chat_id']
                telegram_username = token_info.get('telegram_username')

            # Link Telegram account to user
            async with self.db_manager.get_transaction() as conn:
                # Update user with Telegram info
                await conn.execute("""
                    UPDATE users
                    SET telegram_chat_id = $1,
                        telegram_username = $2,
                        telegram_linked_at = NOW()
                    WHERE id = $3
                """, telegram_chat_id, telegram_username, user_id)

                # Mark token as used
                await conn.execute("""
                    UPDATE telegram_auth_tokens
                    SET used_at = NOW(), user_id = $1
                    WHERE token_hash = $2
                """, user_id, token_hash)

            # Create session in Redis
            await self._create_telegram_session(telegram_chat_id, user_id)

            # Clear auth token from cache
            await self.redis_client.delete(f"telegram_auth_token:{token_hash}")

            logger.info(f"Telegram account linked: chat_id={telegram_chat_id}, user_id={user_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to verify auth token: {str(e)}")
            return False

    async def get_user_by_chat_id(self, telegram_chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user information by Telegram chat ID

        Args:
            telegram_chat_id: Telegram chat ID

        Returns:
            User information dict or None if not found
        """
        try:
            # Check Redis session cache first
            cached_user = await self.redis_client.get(f"telegram_session:{telegram_chat_id}")

            if cached_user:
                return json.loads(cached_user)

            # Query database
            async with self.db_manager.get_connection() as conn:
                user = await conn.fetchrow("""
                    SELECT id, username, email, role, permissions, is_active, telegram_username
                    FROM users
                    WHERE telegram_chat_id = $1 AND is_active = TRUE
                """, telegram_chat_id)

                if not user:
                    return None

                user_dict = dict(user)

                # Cache in Redis
                await self._create_telegram_session(telegram_chat_id, user_dict['id'])

                return user_dict

        except Exception as e:
            logger.error(f"Failed to get user by chat_id: {str(e)}")
            return None

    async def is_authenticated(self, telegram_chat_id: int) -> bool:
        """
        Check if Telegram user is authenticated

        Args:
            telegram_chat_id: Telegram chat ID

        Returns:
            bool: True if authenticated
        """
        user = await self.get_user_by_chat_id(telegram_chat_id)
        return user is not None

    async def require_auth(self, telegram_chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Require authentication, raise exception if not authenticated

        Args:
            telegram_chat_id: Telegram chat ID

        Returns:
            User information dict

        Raises:
            ValueError: If user is not authenticated
        """
        user = await self.get_user_by_chat_id(telegram_chat_id)

        if not user:
            raise ValueError("Authentication required. Please use /start to authenticate.")

        return user

    async def check_permission(self, telegram_chat_id: int, permission: str) -> bool:
        """
        Check if user has specific permission

        Args:
            telegram_chat_id: Telegram chat ID
            permission: Permission name to check

        Returns:
            bool: True if user has permission
        """
        user = await self.get_user_by_chat_id(telegram_chat_id)

        if not user:
            return False

        # Admin has all permissions
        if user.get('role') == 'admin':
            return True

        # Check specific permission
        permissions = user.get('permissions', {})
        return permissions.get(permission, False)

    async def revoke_session(self, telegram_chat_id: int) -> bool:
        """
        Revoke Telegram session for user

        Args:
            telegram_chat_id: Telegram chat ID

        Returns:
            bool: True if session revoked successfully
        """
        try:
            # Delete session from Redis
            await self.redis_client.delete(f"telegram_session:{telegram_chat_id}")

            # Update database
            async with self.db_manager.get_transaction() as conn:
                await conn.execute("""
                    UPDATE users
                    SET telegram_chat_id = NULL,
                        telegram_username = NULL,
                        telegram_linked_at = NULL
                    WHERE telegram_chat_id = $1
                """, telegram_chat_id)

            logger.info(f"Telegram session revoked for chat_id: {telegram_chat_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke session: {str(e)}")
            return False

    async def _create_telegram_session(self, telegram_chat_id: int, user_id: str):
        """Create or refresh Telegram session in Redis"""
        try:
            async with self.db_manager.get_connection() as conn:
                user = await conn.fetchrow("""
                    SELECT id, username, email, role, permissions, telegram_username
                    FROM users
                    WHERE id = $1
                """, user_id)

                if user:
                    session_data = {
                        'id': str(user['id']),
                        'username': user['username'],
                        'email': user['email'],
                        'role': user['role'],
                        'permissions': user['permissions'] or {},
                        'telegram_username': user['telegram_username'],
                        'last_active': datetime.now().isoformat()
                    }

                    # Store session with expiry
                    await self.redis_client.setex(
                        f"telegram_session:{telegram_chat_id}",
                        self.session_expiry_days * 24 * 3600,
                        json.dumps(session_data, default=str)
                    )

        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")

    async def _check_auth_rate_limit(self, telegram_chat_id: int) -> bool:
        """Check if auth attempts are within rate limit"""
        try:
            key = f"telegram_auth_attempts:{telegram_chat_id}"
            attempts = await self.redis_client.get(key)

            if attempts and int(attempts) >= self.auth_attempt_limit:
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to check rate limit: {str(e)}")
            return True  # Allow on error

    async def _increment_auth_attempts(self, telegram_chat_id: int):
        """Increment auth attempt counter"""
        try:
            key = f"telegram_auth_attempts:{telegram_chat_id}"

            # Increment counter
            await self.redis_client.incr(key)

            # Set expiry if new key
            ttl = await self.redis_client.ttl(key)
            if ttl == -1:  # No expiry set
                await self.redis_client.expire(key, self.auth_attempt_window)

        except Exception as e:
            logger.error(f"Failed to increment auth attempts: {str(e)}")

    async def log_command_execution(self, telegram_chat_id: int, command: str,
                                   parameters: Dict[str, Any], response_status: str,
                                   response_time_ms: int, error_message: str = None):
        """
        Log bot command execution to database for audit trail

        Args:
            telegram_chat_id: Telegram chat ID
            command: Command name
            parameters: Command parameters
            response_status: Response status (success/error/unauthorized)
            response_time_ms: Response time in milliseconds
            error_message: Optional error message
        """
        try:
            user = await self.get_user_by_chat_id(telegram_chat_id)
            user_id = user['id'] if user else None

            async with self.db_manager.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO bot_command_log
                    (user_id, telegram_chat_id, command, parameters, response_status,
                     response_time_ms, error_message, executed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """, user_id, telegram_chat_id, command, json.dumps(parameters),
                response_status, response_time_ms, error_message)

        except Exception as e:
            logger.error(f"Failed to log command execution: {str(e)}")


def require_auth(func):
    """
    Decorator to require authentication for command handlers.

    Works on both module-level functions (update, context) and instance methods
    (self, update, context) — update and context are always the last two positional args.

    Usage:
        @require_auth
        async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
            pass

        class Handlers:
            @require_auth
            async def cmd_signals(self, update, context):
                pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Support both standalone functions (update, context) and
        # instance methods (self, update, context).
        update = args[-2]
        context = args[-1]
        try:
            # Get auth manager from context
            auth_manager: TelegramAuthManager = context.bot_data.get('auth_manager')

            if not auth_manager:
                await update.message.reply_text(
                    "Authentication service unavailable. Please try again later."
                )
                return

            # Get chat ID
            chat_id = update.effective_chat.id

            # Check authentication
            user = await auth_manager.get_user_by_chat_id(chat_id)

            if not user:
                await update.message.reply_text(
                    "You are not authenticated. Please use /start to authenticate your account.\n\n"
                    "This will link your Telegram account to your trading account."
                )
                return

            # Store user in context for handler use
            context.user_data['authenticated_user'] = user

            # Call original handler with all original args
            return await func(*args, **kwargs)

        except Exception as e:
            logger.error(f"Auth middleware error: {str(e)}")
            await update.message.reply_text(
                "An error occurred during authentication. Please try again."
            )

    return wrapper


def require_permission(permission: str):
    """
    Decorator to require specific permission for command handlers

    Usage:
        @require_permission('portfolio.modify')
        async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # This will only execute if user has portfolio.modify permission
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Support both standalone functions (update, context) and
            # instance methods (self, update, context).
            update = args[-2]
            context = args[-1]
            try:
                # Get auth manager from context
                auth_manager: TelegramAuthManager = context.bot_data.get('auth_manager')

                if not auth_manager:
                    await update.message.reply_text(
                        "Authentication service unavailable. Please try again later."
                    )
                    return

                # Get chat ID
                chat_id = update.effective_chat.id

                # Check permission
                has_permission = await auth_manager.check_permission(chat_id, permission)

                if not has_permission:
                    await update.message.reply_text(
                        f"You do not have permission to use this command.\n\n"
                        f"Required permission: {permission}"
                    )
                    return

                # Call original handler with all original args
                return await func(*args, **kwargs)

            except Exception as e:
                logger.error(f"Permission check error: {str(e)}")
                await update.message.reply_text(
                    "An error occurred during permission check. Please try again."
                )

        return wrapper
    return decorator
