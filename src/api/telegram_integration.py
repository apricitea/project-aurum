"""
Telegram Bot Integration with FastAPI
Integrates Telegram bot service with the main FastAPI application
"""

import logging
from typing import Optional
from fastapi import FastAPI, Request
from telegram import Update

from .database import DatabaseManager
from .signal_service import SignalService
from .alert_engine import AlertEngine
from .telegram_bot_service import TelegramBotService
from .telegram_auth import TelegramAuthManager
from .telegram_transaction_handlers import TransactionManager
from .telegram_preferences_handlers import PreferenceManager
from .config import settings

logger = logging.getLogger(__name__)

# Global bot service instance
telegram_bot: Optional[TelegramBotService] = None


async def initialize_telegram_bot(
    db_manager: DatabaseManager,
    signal_service: SignalService,
    alert_engine: AlertEngine
) -> Optional[TelegramBotService]:
    """
    Initialize Telegram bot service

    Args:
        db_manager: Database manager instance
        signal_service: Signal service instance
        alert_engine: Alert engine instance

    Returns:
        Initialized TelegramBotService or None if disabled
    """
    global telegram_bot

    if not settings.TELEGRAM_ENABLED:
        logger.info("Telegram bot is disabled in configuration")
        return None

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return None

    try:
        logger.info("Initializing Telegram bot service...")

        # Initialize managers
        auth_manager = TelegramAuthManager(db_manager)
        transaction_manager = TransactionManager(db_manager, signal_service)
        preference_manager = PreferenceManager(db_manager)

        # Create bot service
        telegram_bot = TelegramBotService(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            db_manager=db_manager,
            signal_service=signal_service,
            alert_engine=alert_engine,
            auth_manager=auth_manager,
            transaction_manager=transaction_manager,
            preference_manager=preference_manager,
            webhook_url=settings.TELEGRAM_WEBHOOK_URL if hasattr(settings, 'TELEGRAM_WEBHOOK_URL') else None,
            web_app_url=settings.WEB_APP_URL if hasattr(settings, 'WEB_APP_URL') else 'http://localhost:3000'
        )

        # Start bot (polling or webhook)
        await telegram_bot.start()

        logger.info("✅ Telegram bot service started successfully")
        return telegram_bot

    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")
        return None


async def shutdown_telegram_bot():
    """Shutdown Telegram bot service"""
    global telegram_bot

    if telegram_bot:
        try:
            logger.info("Shutting down Telegram bot service...")
            await telegram_bot.stop()
            telegram_bot = None
            logger.info("✅ Telegram bot service stopped successfully")
        except Exception as e:
            logger.error(f"Error shutting down Telegram bot: {e}")


def register_telegram_routes(app: FastAPI):
    """
    Register Telegram-related routes with FastAPI

    Args:
        app: FastAPI application instance
    """

    @app.post("/telegram/webhook", tags=["Telegram"])
    async def telegram_webhook(request: Request):
        """
        Telegram webhook endpoint
        Receives updates from Telegram when webhook mode is enabled
        """
        if not telegram_bot:
            return {"status": "error", "message": "Telegram bot not initialized"}

        try:
            # Parse update from request
            update_data = await request.json()
            update = Update.de_json(update_data, telegram_bot.application.bot)

            # Process update
            await telegram_bot.application.process_update(update)

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            return {"status": "error", "message": str(e)}


    @app.get("/telegram/status", tags=["Telegram"])
    async def telegram_status():
        """Get Telegram bot status"""
        if not telegram_bot:
            return {
                "enabled": False,
                "status": "not_initialized",
                "message": "Telegram bot is not enabled or failed to initialize"
            }

        try:
            bot_info = await telegram_bot.application.bot.get_me()

            # Get user count
            query = """
                SELECT COUNT(*) as count
                FROM users
                WHERE telegram_chat_id IS NOT NULL
            """
            result = await telegram_bot.db_manager.fetch_one(query)
            user_count = result['count'] if result else 0

            # Get command stats (last 24 hours)
            stats_query = """
                SELECT
                    COUNT(*) as total_commands,
                    COUNT(DISTINCT user_id) as active_users,
                    AVG(response_time_ms) as avg_response_time
                FROM bot_command_log
                WHERE executed_at > NOW() - INTERVAL '24 hours'
            """
            stats = await telegram_bot.db_manager.fetch_one(stats_query)

            return {
                "enabled": True,
                "status": "running",
                "mode": "webhook" if telegram_bot.webhook_url else "polling",
                "bot_info": {
                    "id": bot_info.id,
                    "username": bot_info.username,
                    "name": bot_info.first_name
                },
                "statistics": {
                    "total_users": user_count,
                    "active_users_24h": stats.get('active_users', 0) if stats else 0,
                    "total_commands_24h": stats.get('total_commands', 0) if stats else 0,
                    "avg_response_time_ms": float(stats.get('avg_response_time', 0)) if stats and stats.get('avg_response_time') else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {
                "enabled": True,
                "status": "error",
                "message": str(e)
            }


    @app.post("/telegram/broadcast", tags=["Telegram"])
    async def broadcast_message(message: str, priority: str = "medium"):
        """
        Broadcast message to all Telegram users
        Requires admin authentication
        """
        if not telegram_bot:
            return {"status": "error", "message": "Telegram bot not initialized"}

        try:
            await telegram_bot.broadcast_alert({
                'message': message,
                'priority': priority,
                'alert_type': 'system_announcement'
            })

            return {
                "status": "success",
                "message": "Broadcast queued successfully"
            }

        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return {"status": "error", "message": str(e)}


    @app.get("/telegram/link/{user_id}", tags=["Telegram"])
    async def get_telegram_link_status(user_id: str):
        """Check if user has linked their Telegram account"""
        try:
            query = """
                SELECT telegram_chat_id, telegram_username, telegram_linked_at
                FROM users
                WHERE id = $1
            """

            result = await telegram_bot.db_manager.fetch_one(query, user_id)

            if not result:
                return {
                    "status": "error",
                    "message": "User not found"
                }

            is_linked = result.get('telegram_chat_id') is not None

            return {
                "status": "success",
                "is_linked": is_linked,
                "telegram_username": result.get('telegram_username'),
                "linked_at": result.get('telegram_linked_at').isoformat() if result.get('telegram_linked_at') else None
            }

        except Exception as e:
            logger.error(f"Error checking link status: {e}")
            return {"status": "error", "message": str(e)}


    @app.post("/telegram/auth/complete", tags=["Telegram"])
    async def complete_telegram_auth(token: str, user_id: str):
        """
        Complete Telegram authentication from web app
        Called by frontend after user logs in
        """
        if not telegram_bot:
            return {"status": "error", "message": "Telegram bot not initialized"}

        try:
            # Get auth token from database
            query = """
                SELECT * FROM telegram_auth_tokens
                WHERE token = $1
                  AND status = 'pending'
                  AND expires_at > NOW()
            """

            auth_token = await telegram_bot.db_manager.fetch_one(query, token)

            if not auth_token:
                return {
                    "status": "error",
                    "message": "Invalid or expired authentication token"
                }

            # Link Telegram account to user
            update_user_query = """
                UPDATE users
                SET telegram_chat_id = $1,
                    telegram_linked_at = NOW()
                WHERE id = $2
                RETURNING telegram_chat_id
            """

            result = await telegram_bot.db_manager.fetch_one(
                update_user_query,
                auth_token['telegram_chat_id'],
                user_id
            )

            if not result:
                return {
                    "status": "error",
                    "message": "User not found"
                }

            # Mark token as used
            update_token_query = """
                UPDATE telegram_auth_tokens
                SET status = 'used',
                    used_at = NOW(),
                    user_id = $1
                WHERE token = $2
            """

            await telegram_bot.db_manager.execute(update_token_query, user_id, token)

            # Send confirmation to Telegram
            try:
                await telegram_bot.application.bot.send_message(
                    chat_id=auth_token['telegram_chat_id'],
                    text="✅ *Authentication Successful!*\n\n"
                         "Your Telegram account has been linked successfully.\n"
                         "You can now use all bot commands.\n\n"
                         "Try `/help` to see available commands.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Failed to send confirmation to Telegram: {e}")

            return {
                "status": "success",
                "message": "Telegram account linked successfully",
                "telegram_chat_id": auth_token['telegram_chat_id']
            }

        except Exception as e:
            logger.error(f"Error completing auth: {e}")
            return {"status": "error", "message": str(e)}

    logger.info("Telegram routes registered successfully")


async def send_signal_alerts_via_telegram(signals: list):
    """
    Send signal alerts to Telegram users based on their preferences
    Called by signal generation service
    """
    if not telegram_bot:
        return

    try:
        # Get all users with Telegram linked
        query = """
            SELECT u.id, u.telegram_chat_id, tp.signal_filter, tp.watchlist
            FROM users u
            LEFT JOIN telegram_preferences tp ON u.id = tp.user_id
            WHERE u.telegram_chat_id IS NOT NULL
        """

        users = await telegram_bot.db_manager.fetch_all(query)

        for user in users:
            # Filter signals based on user preferences
            signal_filter = user.get('signal_filter', 'all')
            watchlist = user.get('watchlist', [])

            user_signals = []
            for signal in signals:
                # Apply signal filter
                if signal_filter == 'buy_only' and signal['signal_type'] not in ['BUY', 'STRONG_BUY']:
                    continue
                if signal_filter == 'sell_only' and signal['signal_type'] not in ['SELL', 'STRONG_SELL']:
                    continue
                if signal_filter == 'high_confidence' and signal.get('confidence', 0) < 0.8:
                    continue

                # Apply watchlist filter
                if watchlist and signal['stock_code'] not in watchlist:
                    continue

                user_signals.append(signal)

            # Send personalized signals
            if user_signals:
                await _send_signals_to_user(user['telegram_chat_id'], user_signals)

    except Exception as e:
        logger.error(f"Error sending signal alerts via Telegram: {e}")


async def _send_signals_to_user(chat_id: int, signals: list):
    """Send formatted signals to a specific user"""
    if not telegram_bot:
        return

    try:
        # Format signals
        signals_text = []
        for signal in signals[:10]:  # Limit to 10
            signal_emoji = {
                'BUY': '🟢',
                'STRONG_BUY': '🟢🟢',
                'SELL': '🔴',
                'STRONG_SELL': '🔴🔴',
                'HOLD': '🟡'
            }.get(signal.get('signal_type'), '⚪')

            confidence = signal.get('confidence', 0)
            conf_percent = confidence * 100

            signals_text.append(
                f"{signal_emoji} *{signal.get('stock_code')}* - "
                f"{signal.get('signal_type')} ({conf_percent:.0f}%)"
            )

        message = f"""
📊 *DAILY SIGNALS UPDATE*

{chr(10).join(signals_text)}

Use `/signals` for full list
Use `/signals <STOCK>` for details
        """.strip()

        await telegram_bot.application.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error sending signals to user {chat_id}: {e}")
