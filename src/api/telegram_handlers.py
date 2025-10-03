"""
Telegram Bot Command Handlers for Indonesian Quantitative Trading System
Implements all bot commands with proper error handling and logging
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .telegram_auth import TelegramAuthManager, require_auth, require_permission
from .signal_service import SignalService
from .database import DatabaseManager
from .alert_engine import AlertEngine
from .config import settings

logger = logging.getLogger(__name__)


class TelegramCommandHandlers:
    """
    Telegram bot command handlers
    """

    def __init__(self, db_manager: DatabaseManager, signal_service: SignalService,
                 alert_engine: AlertEngine, auth_manager: TelegramAuthManager):
        self.db_manager = db_manager
        self.signal_service = signal_service
        self.alert_engine = alert_engine
        self.auth_manager = auth_manager

    # ==================== Authentication Commands ====================

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command - Initialize bot and authenticate user
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id
        username = update.effective_user.username

        try:
            # Check if already authenticated
            user = await self.auth_manager.get_user_by_chat_id(chat_id)

            if user:
                welcome_message = f"""
Welcome back, *{user['username']}*! 👋

Your Telegram account is already linked to your trading account.

Use /help to see available commands.
                """.strip()

                await update.message.reply_text(
                    welcome_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Generate authentication token
                auth_data = await self.auth_manager.generate_auth_token(chat_id, username)

                auth_message = f"""
Welcome to *Indonesian Quantitative Trading System*! 🚀

To use this bot, you need to link your Telegram account to your trading account.

*Authentication Steps:*
1. Click the link below to authenticate
2. Log in with your trading account credentials
3. Your Telegram will be linked automatically

*Authentication URL:*
{auth_data['auth_url']}

⏱️ This link expires in *{auth_data['expires_in_minutes']} minutes*.

After authentication, use /help to see available commands.
                """.strip()

                await update.message.reply_text(
                    auth_message,
                    parse_mode=ParseMode.MARKDOWN
                )

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/start', {}, 'success', response_time
            )

        except Exception as e:
            logger.error(f"Error in /start command: {str(e)}")
            await update.message.reply_text(
                "An error occurred. Please try again later."
            )

            # Log error
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/start', {}, 'error', response_time, str(e)
            )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /help command - Show available commands
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id

        try:
            user = await self.auth_manager.get_user_by_chat_id(chat_id)

            if not user:
                help_text = """
*Indonesian Quantitative Trading System Bot*

You are not authenticated. Use /start to link your account.

*Public Commands:*
/start - Authenticate your account
/help - Show this help message
/ping - Check bot status
                """.strip()
            else:
                help_text = """
*Indonesian Quantitative Trading System Bot*

*Signal Commands:*
/signals - Get today's top trading signals
/signals <STOCK> - Get signal for specific stock (e.g., /signals BBCA)

*Portfolio Commands:*
/portfolio - View your portfolio overview
/positions - View detailed positions

*Risk Commands:*
/risk - View risk metrics and alerts

*Market Commands:*
/market - Get market status

*Utility Commands:*
/help - Show this help message
/ping - Check bot status
/logout - Unlink your Telegram account

*Examples:*
• `/signals` - Get top 10 signals for today
• `/signals BBCA` - Get signal for Bank BCA
• `/portfolio` - View your portfolio summary
• `/risk` - Check portfolio risk metrics

For more information, visit the dashboard.
                """.strip()

            await update.message.reply_text(
                help_text,
                parse_mode=ParseMode.MARKDOWN
            )

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/help', {}, 'success', response_time
            )

        except Exception as e:
            logger.error(f"Error in /help command: {str(e)}")
            await update.message.reply_text(
                "An error occurred. Please try again later."
            )

    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /ping command - Check bot status
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id

        try:
            # Check database health
            db_healthy = await self.db_manager.health_check()

            # Check signal service health
            signal_health = await self.signal_service.health_check()

            status_emoji = "✅" if db_healthy and signal_health['status'] == 'healthy' else "⚠️"

            ping_message = f"""
{status_emoji} *Bot Status*

*Database:* {'✅ Connected' if db_healthy else '❌ Disconnected'}
*Signal Service:* {'✅ Healthy' if signal_health['status'] == 'healthy' else '❌ Unhealthy'}
*Model Loaded:* {'✅ Yes' if signal_health.get('model_loaded') else '❌ No'}

*Response Time:* {int((datetime.now() - start_time).total_seconds() * 1000)}ms

All systems operational! 🚀
            """.strip()

            await update.message.reply_text(
                ping_message,
                parse_mode=ParseMode.MARKDOWN
            )

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/ping', {}, 'success', response_time
            )

        except Exception as e:
            logger.error(f"Error in /ping command: {str(e)}")
            await update.message.reply_text(
                "⚠️ Bot is experiencing issues. Please try again later."
            )

    @require_auth
    async def cmd_logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /logout command - Unlink Telegram account
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id

        try:
            success = await self.auth_manager.revoke_session(chat_id)

            if success:
                await update.message.reply_text(
                    "✅ Your Telegram account has been unlinked.\n\n"
                    "Use /start to authenticate again."
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to unlink your account. Please try again."
                )

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/logout', {}, 'success' if success else 'error', response_time
            )

        except Exception as e:
            logger.error(f"Error in /logout command: {str(e)}")
            await update.message.reply_text(
                "An error occurred. Please try again later."
            )

    # ==================== Signal Commands ====================

    @require_auth
    async def cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /signals command - Get today's trading signals or specific stock signal
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id
        user = context.user_data.get('authenticated_user')

        try:
            # Check if stock code provided
            args = context.args
            stock_code = args[0].upper() if args else None

            if stock_code:
                # Get signal for specific stock
                await self._send_stock_signal(update, stock_code)
            else:
                # Get today's top signals
                await self._send_daily_signals(update)

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/signals', {'stock_code': stock_code}, 'success', response_time
            )

        except Exception as e:
            logger.error(f"Error in /signals command: {str(e)}")
            await update.message.reply_text(
                "An error occurred while fetching signals. Please try again later."
            )

            # Log error
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/signals', {'stock_code': stock_code if 'stock_code' in locals() else None},
                'error', response_time, str(e)
            )

    async def _send_daily_signals(self, update: Update):
        """Send today's top 10 signals"""
        try:
            # Get today's signals
            today = date.today()
            signals = await self.signal_service.get_daily_signals(today)

            if not signals:
                await update.message.reply_text(
                    "No signals available for today.\n\n"
                    "Signals are generated daily before market open."
                )
                return

            # Sort by confidence and take top 10
            top_signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)[:10]

            # Format message
            message_parts = [
                f"📊 *Top Trading Signals for {today.strftime('%d %b %Y')}*\n"
            ]

            for i, signal in enumerate(top_signals, 1):
                signal_emoji = self._get_signal_emoji(signal['signal_type'])
                confidence_bar = self._get_confidence_bar(signal['confidence'])

                signal_text = f"""
{i}. {signal_emoji} *{signal['stock_code']}* - {signal['signal_type']}
   Confidence: {confidence_bar} {signal['confidence']:.1%}
   Price: Rp {signal['current_price']:,.0f}
   Position Size: {signal['position_size']:.1%}
                """.strip()

                message_parts.append(signal_text)

            message_parts.append(f"\n📈 Total signals: {len(signals)}")
            message_parts.append(f"⏰ Generated: {datetime.now().strftime('%H:%M WIB')}")

            message = "\n\n".join(message_parts)

            # Add inline keyboard for filtering
            keyboard = [
                [
                    InlineKeyboardButton("💰 BUY Signals", callback_data='filter_buy'),
                    InlineKeyboardButton("📉 SELL Signals", callback_data='filter_sell')
                ],
                [
                    InlineKeyboardButton("⭐ High Confidence", callback_data='filter_high_conf')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error sending daily signals: {str(e)}")
            raise

    async def _send_stock_signal(self, update: Update, stock_code: str):
        """Send signal for specific stock"""
        try:
            # Get today's signals
            today = date.today()
            signals = await self.signal_service.get_daily_signals(today)

            # Find signal for requested stock
            stock_signal = next(
                (s for s in signals if s['stock_code'] == stock_code),
                None
            )

            if not stock_signal:
                await update.message.reply_text(
                    f"No signal found for *{stock_code}* today.\n\n"
                    f"Use /signals to see all available signals.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Format detailed signal message
            signal_emoji = self._get_signal_emoji(stock_signal['signal_type'])
            confidence_bar = self._get_confidence_bar(stock_signal['confidence'])

            message = f"""
{signal_emoji} *{stock_code} - {stock_signal['signal_type']}*

*Signal Details:*
• Confidence: {confidence_bar} {stock_signal['confidence']:.1%}
• Position Size: {stock_signal['position_size']:.1%}
• Current Price: Rp {stock_signal['current_price']:,.0f}
• Sector: {stock_signal.get('sector', 'N/A')}

*Scores:*
• Technical: {stock_signal.get('technical_score', 0):.2f}
• Fundamental: {stock_signal.get('fundamental_score', 0):.2f}
• Sentiment: {stock_signal.get('sentiment_score', 0):.2f}
• Composite: {stock_signal['composite_score']:.2f}

*Risk:*
• Risk Adjusted: {'✅ Yes' if stock_signal.get('risk_adjusted') else '❌ No'}

⏰ Generated: {stock_signal['generated_at'][:16]}
            """.strip()

            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error(f"Error sending stock signal: {str(e)}")
            raise

    # ==================== Portfolio Commands ====================

    @require_auth
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /portfolio command - Get portfolio summary
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id
        user = context.user_data.get('authenticated_user')

        try:
            # Get portfolio summary
            portfolio = await self.signal_service.get_portfolio_summary()

            if not portfolio or portfolio.get('total_positions', 0) == 0:
                await update.message.reply_text(
                    "📊 Your portfolio is empty.\n\n"
                    "Start trading to see your positions here."
                )
                return

            # Format portfolio message
            pnl_emoji = "📈" if portfolio['total_unrealized_pnl'] >= 0 else "📉"
            pnl_color = "🟢" if portfolio['total_unrealized_pnl'] >= 0 else "🔴"

            message = f"""
💼 *Portfolio Summary*

*Overview:*
• Total Positions: {portfolio['total_positions']}
• Market Value: Rp {portfolio['total_market_value']:,.0f}
• Cost Basis: Rp {portfolio['total_cost_basis']:,.0f}

*Performance:*
{pnl_emoji} Unrealized P&L: {pnl_color} Rp {portfolio['total_unrealized_pnl']:,.0f}
{pnl_emoji} Return: {pnl_color} {portfolio['total_unrealized_pnl_percent']:.2%}

*Sector Allocation:*
            """.strip()

            # Add sector breakdown
            for sector, allocation in sorted(
                portfolio.get('sector_breakdown', {}).items(),
                key=lambda x: x[1],
                reverse=True
            ):
                allocation_bar = self._get_allocation_bar(allocation)
                message += f"\n{allocation_bar} {sector}: {allocation:.1%}"

            message += f"\n\n⏰ Last Updated: {portfolio.get('last_updated', datetime.now()).strftime('%d %b %Y %H:%M')}"

            # Add keyboard for detailed view
            keyboard = [
                [InlineKeyboardButton("📋 Detailed Positions", callback_data='portfolio_details')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/portfolio', {}, 'success', response_time
            )

        except Exception as e:
            logger.error(f"Error in /portfolio command: {str(e)}")
            await update.message.reply_text(
                "An error occurred while fetching portfolio. Please try again later."
            )

            # Log error
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/portfolio', {}, 'error', response_time, str(e)
            )

    @require_auth
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /positions command - Get detailed positions
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id

        try:
            # Get current positions
            positions = await self.signal_service.get_current_positions()

            if not positions:
                await update.message.reply_text(
                    "📊 No positions found.\n\n"
                    "Your portfolio is currently empty."
                )
                return

            # Sort by market value descending
            positions.sort(key=lambda x: x.get('market_value', 0), reverse=True)

            # Format positions message
            message = f"📋 *Detailed Positions* ({len(positions)} stocks)\n"

            for pos in positions[:15]:  # Limit to 15 positions to avoid message length issues
                pnl_emoji = "🟢" if pos.get('unrealized_pnl', 0) >= 0 else "🔴"

                pos_text = f"""
*{pos['stock_code']}*
• Qty: {pos['quantity']:,} @ Rp {pos['average_price']:,.0f}
• Current: Rp {pos.get('current_price', pos['average_price']):,.0f}
• Market Value: Rp {pos.get('market_value', 0):,.0f}
• P&L: {pnl_emoji} Rp {pos.get('unrealized_pnl', 0):,.0f} ({pos.get('unrealized_pnl_percent', 0):.2%})
                """.strip()

                message += f"\n\n{pos_text}"

            if len(positions) > 15:
                message += f"\n\n... and {len(positions) - 15} more positions"

            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/positions', {}, 'success', response_time
            )

        except Exception as e:
            logger.error(f"Error in /positions command: {str(e)}")
            await update.message.reply_text(
                "An error occurred while fetching positions. Please try again later."
            )

    # ==================== Risk Commands ====================

    @require_auth
    async def cmd_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /risk command - Get risk metrics and alerts
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id

        try:
            # Get portfolio metrics
            portfolio = await self.signal_service.get_portfolio_summary()

            # Get active risk alerts
            alerts = await self.alert_engine.get_alerts(
                limit=10,
                status='active',
                priority='high'
            )

            # Get risk limits
            risk_limits = settings.get_risk_limits()

            # Format risk message
            message = "⚠️ *Risk Metrics & Alerts*\n"

            # Portfolio risk overview
            if portfolio:
                sector_breakdown = portfolio.get('sector_breakdown', {})
                max_sector = max(sector_breakdown.values()) if sector_breakdown else 0

                message += f"""
*Portfolio Risk:*
• Total Positions: {portfolio['total_positions']}
• Max Sector Concentration: {max_sector:.1%} / {risk_limits['max_sector_concentration']:.0%}
• Portfolio Value at Risk: {abs(portfolio['total_unrealized_pnl']):.0f}

*Risk Limits:*
• Max Position Size: {risk_limits['max_position_size']:.0%}
• Max Sector Concentration: {risk_limits['max_sector_concentration']:.0%}
• Max Drawdown: {risk_limits['max_drawdown']:.0%}
                """.strip()

            # Active risk alerts
            if alerts:
                message += f"\n\n*Active Alerts ({len(alerts)}):*"

                for alert in alerts[:5]:
                    alert_emoji = "🔴" if alert['priority'] == 'critical' else "🟡"
                    message += f"\n{alert_emoji} {alert['message']}"

                if len(alerts) > 5:
                    message += f"\n\n... and {len(alerts) - 5} more alerts"
            else:
                message += "\n\n✅ No active risk alerts"

            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/risk', {}, 'success', response_time
            )

        except Exception as e:
            logger.error(f"Error in /risk command: {str(e)}")
            await update.message.reply_text(
                "An error occurred while fetching risk metrics. Please try again later."
            )

    # ==================== Market Commands ====================

    @require_auth
    async def cmd_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /market command - Get market status
        """
        start_time = datetime.now()
        chat_id = update.effective_chat.id

        try:
            is_market_hours = settings.is_market_hours()
            current_time = datetime.now()

            status_emoji = "🟢" if is_market_hours else "🔴"
            status_text = "OPEN" if is_market_hours else "CLOSED"

            message = f"""
{status_emoji} *Indonesian Stock Exchange Status*

*Current Status:* {status_text}
*Time:* {current_time.strftime('%H:%M:%S WIB')}
*Date:* {current_time.strftime('%d %B %Y')}

*Trading Hours:*
• Morning: {settings.MARKET_OPEN_TIME} - {settings.MARKET_LUNCH_START} WIB
• Afternoon: {settings.MARKET_LUNCH_END} - {settings.MARKET_CLOSE_TIME} WIB

*Trading Days:* Monday - Friday
            """.strip()

            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )

            # Log command
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.auth_manager.log_command_execution(
                chat_id, '/market', {}, 'success', response_time
            )

        except Exception as e:
            logger.error(f"Error in /market command: {str(e)}")
            await update.message.reply_text(
                "An error occurred while fetching market status. Please try again later."
            )

    # ==================== Helper Methods ====================

    def _get_signal_emoji(self, signal_type: str) -> str:
        """Get emoji for signal type"""
        emoji_map = {
            'STRONG_BUY': '🚀',
            'BUY': '📈',
            'HOLD': '⏸️',
            'SELL': '📉',
            'STRONG_SELL': '💥'
        }
        return emoji_map.get(signal_type, '➡️')

    def _get_confidence_bar(self, confidence: float) -> str:
        """Generate visual confidence bar"""
        filled = int(confidence * 5)
        empty = 5 - filled
        return '█' * filled + '░' * empty

    def _get_allocation_bar(self, allocation: float) -> str:
        """Generate visual allocation bar"""
        filled = int(allocation * 10)
        empty = 10 - filled
        return '█' * filled + '░' * empty
