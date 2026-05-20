"""
Telegram Bot Service for Indonesian Quantitative Trading System
Main bot service with webhook/polling support, rate limiting, and error handling
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import json
import os

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.error import TelegramError
import aioredis

from .database import DatabaseManager
from .signal_service import SignalService
from .alert_engine import AlertEngine
from .telegram_auth import TelegramAuthManager
from .telegram_handlers import TelegramCommandHandlers
from .config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for Telegram bot commands
    """

    def __init__(self, redis_client):
        self.redis_client = redis_client

        # Rate limit configuration
        self.limits = {
            'general': {'requests': 60, 'window': 60},  # 60 requests per minute
            'signals': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'portfolio': {'requests': 10, 'window': 60}  # 10 requests per minute
        }

    async def check_rate_limit(self, chat_id: int, command_type: str = 'general') -> bool:
        """
        Check if request is within rate limit

        Args:
            chat_id: Telegram chat ID
            command_type: Type of command (general, signals, portfolio)

        Returns:
            bool: True if request allowed, False if rate limited
        """
        try:
            limit_config = self.limits.get(command_type, self.limits['general'])
            key = f"rate_limit:{command_type}:{chat_id}"

            # Get current count
            count = await self.redis_client.get(key)

            if count is None:
                # First request, set counter
                await self.redis_client.setex(
                    key,
                    limit_config['window'],
                    1
                )
                return True

            count = int(count)

            if count >= limit_config['requests']:
                # Rate limit exceeded
                logger.warning(f"Rate limit exceeded for chat_id {chat_id}, type {command_type}")
                return False

            # Increment counter
            await self.redis_client.incr(key)
            return True

        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            # Allow request on error
            return True

    async def get_remaining_requests(self, chat_id: int, command_type: str = 'general') -> Dict[str, Any]:
        """Get remaining requests for user"""
        try:
            limit_config = self.limits.get(command_type, self.limits['general'])
            key = f"rate_limit:{command_type}:{chat_id}"

            count = await self.redis_client.get(key)
            ttl = await self.redis_client.ttl(key)

            if count is None:
                remaining = limit_config['requests']
                reset_in = 0
            else:
                remaining = max(0, limit_config['requests'] - int(count))
                reset_in = ttl if ttl > 0 else 0

            return {
                'limit': limit_config['requests'],
                'remaining': remaining,
                'reset_in_seconds': reset_in,
                'window_seconds': limit_config['window']
            }

        except Exception as e:
            logger.error(f"Error getting remaining requests: {str(e)}")
            return {
                'limit': 0,
                'remaining': 0,
                'reset_in_seconds': 0,
                'window_seconds': 0
            }


class TelegramBotService:
    """
    Main Telegram bot service
    Handles bot lifecycle, command routing, and middleware
    """

    def __init__(self, db_manager: DatabaseManager, signal_service: SignalService,
                 alert_engine: AlertEngine):
        self.db_manager = db_manager
        self.signal_service = signal_service
        self.alert_engine = alert_engine

        # Bot components
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        self.redis_client = None
        self.rate_limiter: Optional[RateLimiter] = None

        # Service components
        self.auth_manager: Optional[TelegramAuthManager] = None
        self.command_handlers: Optional[TelegramCommandHandlers] = None

        # Service state
        self.is_running = False
        self.webhook_mode = False

    async def initialize(self):
        """Initialize Telegram bot service"""
        try:
            logger.info("Initializing Telegram bot service...")

            # Validate configuration
            if not settings.TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN not configured")

            # Connect to Redis — from_url is synchronous in redis-py
            self.redis_client = aioredis.from_url(
                settings.get_redis_url(),
                encoding="utf-8",
                decode_responses=True
            )

            # Initialize rate limiter
            self.rate_limiter = RateLimiter(self.redis_client)

            # Initialize authentication manager
            self.auth_manager = TelegramAuthManager(self.db_manager)
            await self.auth_manager.initialize(self.redis_client)

            # Initialize command handlers
            self.command_handlers = TelegramCommandHandlers(
                self.db_manager,
                self.signal_service,
                self.alert_engine,
                self.auth_manager
            )

            # Create bot application
            self.application = (
                Application.builder()
                .token(settings.TELEGRAM_BOT_TOKEN)
                .build()
            )

            # Store services in bot_data for access in handlers
            self.application.bot_data['db_manager'] = self.db_manager
            self.application.bot_data['signal_service'] = self.signal_service
            self.application.bot_data['alert_engine'] = self.alert_engine
            self.application.bot_data['auth_manager'] = self.auth_manager
            self.application.bot_data['rate_limiter'] = self.rate_limiter

            # Register handlers
            await self._register_handlers()

            # Register error handler
            self.application.add_error_handler(self._error_handler)

            # Get bot instance
            self.bot = self.application.bot

            # Set bot info
            bot_info = await self.bot.get_me()
            logger.info(f"Bot initialized: @{bot_info.username} ({bot_info.id})")

            # Check if webhook mode
            webhook_url = getattr(settings, 'TELEGRAM_WEBHOOK_URL', None)
            self.webhook_mode = bool(webhook_url)

            logger.info(f"Telegram bot service initialized (mode: {'webhook' if self.webhook_mode else 'polling'})")

        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot service: {str(e)}")
            raise

    async def _register_handlers(self):
        """Register all command handlers"""
        try:
            # Command handlers - wrapped with rate limiting
            commands = [
                ('start', self.command_handlers.cmd_start, 'general'),
                ('help', self.command_handlers.cmd_help, 'general'),
                ('ping', self.command_handlers.cmd_ping, 'general'),
                ('logout', self.command_handlers.cmd_logout, 'general'),
                ('signals', self.command_handlers.cmd_signals, 'signals'),
                ('portfolio', self.command_handlers.cmd_portfolio, 'portfolio'),
                ('positions', self.command_handlers.cmd_positions, 'portfolio'),
                ('risk', self.command_handlers.cmd_risk, 'general'),
                ('market', self.command_handlers.cmd_market, 'general'),
            ]

            for command, handler, rate_limit_type in commands:
                # Wrap handler with rate limiting
                wrapped_handler = self._rate_limit_middleware(handler, rate_limit_type)
                self.application.add_handler(
                    CommandHandler(command, wrapped_handler)
                )

            # Callback query handler for inline buttons
            self.application.add_handler(
                CallbackQueryHandler(self._handle_callback_query)
            )

            # Message handler for unknown commands
            self.application.add_handler(
                MessageHandler(
                    filters.COMMAND,
                    self._handle_unknown_command
                )
            )

            logger.info(f"Registered {len(commands)} command handlers")

        except Exception as e:
            logger.error(f"Failed to register handlers: {str(e)}")
            raise

    def _rate_limit_middleware(self, handler, rate_limit_type: str):
        """
        Middleware to apply rate limiting to handlers

        Args:
            handler: Command handler function
            rate_limit_type: Type of rate limit to apply

        Returns:
            Wrapped handler with rate limiting
        """
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id

            # Check rate limit
            allowed = await self.rate_limiter.check_rate_limit(chat_id, rate_limit_type)

            if not allowed:
                # Get rate limit info
                limit_info = await self.rate_limiter.get_remaining_requests(chat_id, rate_limit_type)

                await update.message.reply_text(
                    f"⚠️ Rate limit exceeded.\n\n"
                    f"You can make {limit_info['limit']} requests per {limit_info['window_seconds']} seconds.\n"
                    f"Please try again in {limit_info['reset_in_seconds']} seconds."
                )
                return

            # Call original handler
            return await handler(update, context)

        return wrapped

    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        try:
            query = update.callback_query
            await query.answer()

            chat_id = update.effective_chat.id
            data = query.data

            # Handle different callback types
            if data == 'filter_buy':
                # Filter for BUY signals
                today = datetime.now().date()
                signals = await self.signal_service.get_daily_signals(today)
                buy_signals = [s for s in signals if 'BUY' in s['signal_type']]

                message = f"💰 *BUY Signals ({len(buy_signals)})*\n"
                for i, signal in enumerate(buy_signals[:10], 1):
                    message += f"\n{i}. {signal['stock_code']} - Confidence: {signal['confidence']:.1%}"

                await query.edit_message_text(
                    message,
                    parse_mode='Markdown'
                )

            elif data == 'filter_sell':
                # Filter for SELL signals
                today = datetime.now().date()
                signals = await self.signal_service.get_daily_signals(today)
                sell_signals = [s for s in signals if 'SELL' in s['signal_type']]

                message = f"📉 *SELL Signals ({len(sell_signals)})*\n"
                for i, signal in enumerate(sell_signals[:10], 1):
                    message += f"\n{i}. {signal['stock_code']} - Confidence: {signal['confidence']:.1%}"

                await query.edit_message_text(
                    message,
                    parse_mode='Markdown'
                )

            elif data == 'filter_high_conf':
                # Filter for high confidence signals
                today = datetime.now().date()
                signals = await self.signal_service.get_daily_signals(today)
                high_conf = [s for s in signals if s['confidence'] > 0.75]

                message = f"⭐ *High Confidence Signals ({len(high_conf)})*\n"
                for i, signal in enumerate(high_conf[:10], 1):
                    message += f"\n{i}. {signal['stock_code']} - {signal['signal_type']} ({signal['confidence']:.1%})"

                await query.edit_message_text(
                    message,
                    parse_mode='Markdown'
                )

            elif data == 'portfolio_details':
                # Show detailed portfolio positions
                positions = await self.signal_service.get_current_positions()

                message = f"📋 *Detailed Positions ({len(positions)})*\n"
                for pos in positions[:10]:
                    pnl_emoji = "🟢" if pos.get('unrealized_pnl', 0) >= 0 else "🔴"
                    message += f"\n{pos['stock_code']}: {pnl_emoji} Rp {pos.get('unrealized_pnl', 0):,.0f}"

                await query.edit_message_text(
                    message,
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error handling callback query: {str(e)}")
            await query.answer("An error occurred. Please try again.")

    async def _handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands"""
        await update.message.reply_text(
            "Unknown command. Use /help to see available commands."
        )

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Global error handler"""
        try:
            logger.error(f"Telegram bot error: {context.error}", exc_info=context.error)

            # Send user-friendly error message
            if isinstance(update, Update) and update.effective_message:
                await update.effective_message.reply_text(
                    "An error occurred while processing your request. "
                    "Please try again later or contact support if the issue persists."
                )

        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")

    async def start(self):
        """Start the Telegram bot"""
        try:
            if self.is_running:
                logger.warning("Bot is already running")
                return

            logger.info("Starting Telegram bot...")

            # Initialize the application
            await self.application.initialize()

            if self.webhook_mode:
                # Start webhook mode
                webhook_url = settings.TELEGRAM_WEBHOOK_URL
                await self.application.start()
                await self.application.bot.set_webhook(url=webhook_url)
                logger.info(f"Bot started in webhook mode: {webhook_url}")
            else:
                # Start polling mode
                await self.application.start()
                await self.application.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES
                )
                logger.info("Bot started in polling mode")

            self.is_running = True
            logger.info("Telegram bot started successfully")

        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {str(e)}")
            raise

    async def stop(self):
        """Stop the Telegram bot"""
        try:
            if not self.is_running:
                logger.warning("Bot is not running")
                return

            logger.info("Stopping Telegram bot...")

            if self.webhook_mode:
                # Stop webhook
                await self.application.bot.delete_webhook()
            else:
                # Stop polling
                await self.application.updater.stop()

            await self.application.stop()
            await self.application.shutdown()

            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()

            self.is_running = False
            logger.info("Telegram bot stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {str(e)}")
            raise

    async def send_alert_to_user(self, chat_id: int, alert: Dict[str, Any]):
        """
        Send alert to specific user via Telegram

        Args:
            chat_id: Telegram chat ID
            alert: Alert data dictionary
        """
        try:
            if not self.bot:
                logger.error("Bot not initialized")
                return False

            # Format alert message
            priority_emoji = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🟠',
                'critical': '🔴'
            }

            emoji = priority_emoji.get(alert.get('priority', 'medium'), '⚪')

            message = f"""
{emoji} *TRADING ALERT*

*Type:* {alert['alert_type'].replace('_', ' ').title()}
*Priority:* {alert['priority'].upper()}
*Stock:* {alert.get('stock_code', 'N/A')}

*Message:*
{alert['message']}

*Time:* {alert.get('created_at', datetime.now()).strftime('%d %b %Y %H:%M')}
            """.strip()

            # Send message
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )

            logger.info(f"Alert sent to chat_id {chat_id}")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send alert to chat_id {chat_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
            return False

    async def broadcast_alert(self, alert: Dict[str, Any]):
        """
        Broadcast alert to all authenticated users

        Args:
            alert: Alert data dictionary
        """
        try:
            # Get all users with Telegram linked
            async with self.db_manager.get_connection() as conn:
                users = await conn.fetch("""
                    SELECT telegram_chat_id
                    FROM users
                    WHERE telegram_chat_id IS NOT NULL
                    AND is_active = TRUE
                """)

            # Send to each user
            success_count = 0
            for user in users:
                chat_id = user['telegram_chat_id']
                success = await self.send_alert_to_user(chat_id, alert)
                if success:
                    success_count += 1

            logger.info(f"Alert broadcast to {success_count}/{len(users)} users")

        except Exception as e:
            logger.error(f"Error broadcasting alert: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Health check for Telegram bot service"""
        try:
            health = {
                'service': 'telegram_bot',
                'status': 'healthy' if self.is_running else 'stopped',
                'mode': 'webhook' if self.webhook_mode else 'polling',
                'bot_initialized': self.bot is not None,
                'redis_connected': self.redis_client is not None,
                'timestamp': datetime.now().isoformat()
            }

            # Check bot API connection
            if self.bot:
                try:
                    await self.bot.get_me()
                    health['bot_api_connected'] = True
                except Exception as e:
                    health['bot_api_connected'] = False
                    health['bot_api_error'] = str(e)

            return health

        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return {
                'service': 'telegram_bot',
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Factory function to create bot service
async def create_telegram_bot_service(db_manager: DatabaseManager,
                                     signal_service: SignalService,
                                     alert_engine: AlertEngine) -> TelegramBotService:
    """
    Factory function to create and initialize Telegram bot service

    Args:
        db_manager: Database manager instance
        signal_service: Signal service instance
        alert_engine: Alert engine instance

    Returns:
        Initialized TelegramBotService instance
    """
    bot_service = TelegramBotService(db_manager, signal_service, alert_engine)
    await bot_service.initialize()
    return bot_service
