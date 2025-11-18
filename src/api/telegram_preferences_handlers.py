"""
Telegram Preference Handlers for Alert Customization and Watchlists
Handles /subscribe and /watchlist commands
"""

from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from .database import DatabaseManager
from .telegram_auth import require_auth

logger = logging.getLogger(__name__)


class PreferenceManager:
    """Manages user preferences for alerts and watchlists"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's Telegram preferences"""
        query = """
            SELECT * FROM telegram_preferences
            WHERE user_id = $1
        """

        prefs = await self.db.fetch_one(query, user_id)

        if not prefs:
            # Create default preferences
            prefs = await self.create_default_preferences(user_id)

        return prefs

    async def create_default_preferences(self, user_id: str) -> Dict[str, Any]:
        """Create default preferences for user"""
        query = """
            INSERT INTO telegram_preferences (
                user_id, alert_types, signal_filter, notification_hours,
                watchlist, language
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """

        default_alert_types = ['high_confidence', 'risk_breach', 'large_position']
        default_hours = [9, 10, 11, 14, 15]  # WIB hours
        default_watchlist = []

        return await self.db.fetch_one(
            query,
            user_id,
            default_alert_types,
            'all',
            default_hours,
            default_watchlist,
            'id'  # Indonesian
        )

    async def update_alert_types(self, user_id: str, alert_types: List[str]) -> Dict[str, Any]:
        """Update user's alert type preferences"""
        query = """
            UPDATE telegram_preferences
            SET alert_types = $1, updated_at = NOW()
            WHERE user_id = $2
            RETURNING *
        """

        return await self.db.fetch_one(query, alert_types, user_id)

    async def update_signal_filter(self, user_id: str, signal_filter: str) -> Dict[str, Any]:
        """Update user's signal filter preference"""
        query = """
            UPDATE telegram_preferences
            SET signal_filter = $1, updated_at = NOW()
            WHERE user_id = $2
            RETURNING *
        """

        return await self.db.fetch_one(query, signal_filter, user_id)

    async def update_notification_hours(self, user_id: str, hours: List[int]) -> Dict[str, Any]:
        """Update user's notification hour preferences"""
        query = """
            UPDATE telegram_preferences
            SET notification_hours = $1, updated_at = NOW()
            WHERE user_id = $2
            RETURNING *
        """

        return await self.db.fetch_one(query, hours, user_id)

    async def add_to_watchlist(self, user_id: str, stock_code: str) -> Dict[str, Any]:
        """Add stock to user's watchlist"""
        # Get current watchlist
        prefs = await self.get_preferences(user_id)
        watchlist = prefs.get('watchlist', [])

        if stock_code in watchlist:
            raise ValueError(f"{stock_code} is already in your watchlist")

        watchlist.append(stock_code)

        query = """
            UPDATE telegram_preferences
            SET watchlist = $1, updated_at = NOW()
            WHERE user_id = $2
            RETURNING *
        """

        return await self.db.fetch_one(query, watchlist, user_id)

    async def remove_from_watchlist(self, user_id: str, stock_code: str) -> Dict[str, Any]:
        """Remove stock from user's watchlist"""
        prefs = await self.get_preferences(user_id)
        watchlist = prefs.get('watchlist', [])

        if stock_code not in watchlist:
            raise ValueError(f"{stock_code} is not in your watchlist")

        watchlist.remove(stock_code)

        query = """
            UPDATE telegram_preferences
            SET watchlist = $1, updated_at = NOW()
            WHERE user_id = $2
            RETURNING *
        """

        return await self.db.fetch_one(query, watchlist, user_id)

    async def clear_watchlist(self, user_id: str) -> Dict[str, Any]:
        """Clear user's watchlist"""
        query = """
            UPDATE telegram_preferences
            SET watchlist = $1, updated_at = NOW()
            WHERE user_id = $2
            RETURNING *
        """

        return await self.db.fetch_one(query, [], user_id)


# Command Handlers

@require_auth
async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command - manage alert preferences"""
    try:
        user_id = context.user_data['user_id']
        preference_manager = context.bot_data['preference_manager']

        # Get current preferences
        prefs = await preference_manager.get_preferences(user_id)

        # If no arguments, show current settings
        if not context.args:
            # Format current preferences
            alert_types_text = ", ".join(prefs.get('alert_types', []))
            signal_filter = prefs.get('signal_filter', 'all')
            hours = prefs.get('notification_hours', [])
            hours_text = ", ".join([f"{h}:00" for h in sorted(hours)])

            message = f"""
🔔 *ALERT PREFERENCES*

*Current Settings:*

📊 *Alert Types:*
{alert_types_text}

📈 *Signal Filter:*
{signal_filter}

⏰ *Notification Hours (WIB):*
{hours_text}

*To change settings:*
• `/subscribe alerts <types>` - Set alert types
• `/subscribe filter <type>` - Set signal filter
• `/subscribe hours <hours>` - Set notification hours

*Available Alert Types:*
• high_confidence
• risk_breach
• large_position
• position_loss
• sector_concentration

*Available Filters:*
• all - All signals
• buy_only - Buy signals only
• sell_only - Sell signals only
• high_confidence - High confidence only

*Example:*
`/subscribe alerts high_confidence risk_breach`
`/subscribe filter buy_only`
`/subscribe hours 9 10 11 14 15`
            """.strip()

            await update.message.reply_text(message, parse_mode='Markdown')
            return

        # Parse subcommand
        subcommand = context.args[0].lower()

        if subcommand == 'alerts':
            # Set alert types
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Please specify at least one alert type\n\n"
                    "Example: `/subscribe alerts high_confidence risk_breach`",
                    parse_mode='Markdown'
                )
                return

            valid_types = [
                'high_confidence', 'risk_breach', 'large_position',
                'position_loss', 'sector_concentration', 'system_error'
            ]

            alert_types = [t.lower() for t in context.args[1:]]

            # Validate alert types
            invalid_types = [t for t in alert_types if t not in valid_types]
            if invalid_types:
                await update.message.reply_text(
                    f"❌ Invalid alert types: {', '.join(invalid_types)}\n\n"
                    f"Valid types: {', '.join(valid_types)}",
                    parse_mode='Markdown'
                )
                return

            # Update preferences
            await preference_manager.update_alert_types(user_id, alert_types)

            message = f"""
✅ *Alert preferences updated!*

You will now receive alerts for:
{', '.join(alert_types)}
            """.strip()

            await update.message.reply_text(message, parse_mode='Markdown')

        elif subcommand == 'filter':
            # Set signal filter
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Please specify a signal filter\n\n"
                    "Example: `/subscribe filter buy_only`",
                    parse_mode='Markdown'
                )
                return

            signal_filter = context.args[1].lower()
            valid_filters = ['all', 'buy_only', 'sell_only', 'high_confidence']

            if signal_filter not in valid_filters:
                await update.message.reply_text(
                    f"❌ Invalid filter: {signal_filter}\n\n"
                    f"Valid filters: {', '.join(valid_filters)}",
                    parse_mode='Markdown'
                )
                return

            # Update preferences
            await preference_manager.update_signal_filter(user_id, signal_filter)

            filter_descriptions = {
                'all': 'all signals',
                'buy_only': 'buy signals only',
                'sell_only': 'sell signals only',
                'high_confidence': 'high confidence signals only'
            }

            message = f"""
✅ *Signal filter updated!*

You will now receive: {filter_descriptions[signal_filter]}
            """.strip()

            await update.message.reply_text(message, parse_mode='Markdown')

        elif subcommand == 'hours':
            # Set notification hours
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Please specify at least one hour\n\n"
                    "Example: `/subscribe hours 9 10 11 14 15`",
                    parse_mode='Markdown'
                )
                return

            try:
                hours = [int(h) for h in context.args[1:]]
            except ValueError:
                await update.message.reply_text(
                    "❌ Hours must be integers (0-23)",
                    parse_mode='Markdown'
                )
                return

            # Validate hours (0-23)
            invalid_hours = [h for h in hours if h < 0 or h > 23]
            if invalid_hours:
                await update.message.reply_text(
                    f"❌ Invalid hours: {', '.join(map(str, invalid_hours))}\n\n"
                    "Hours must be between 0 and 23",
                    parse_mode='Markdown'
                )
                return

            # Update preferences
            await preference_manager.update_notification_hours(user_id, hours)

            hours_text = ", ".join([f"{h}:00" for h in sorted(hours)])

            message = f"""
✅ *Notification hours updated!*

You will receive notifications during:
{hours_text} WIB
            """.strip()

            await update.message.reply_text(message, parse_mode='Markdown')

        else:
            await update.message.reply_text(
                "❌ Unknown subcommand\n\n"
                "Use: `/subscribe alerts`, `/subscribe filter`, or `/subscribe hours`",
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error in /subscribe command: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again.",
            parse_mode='Markdown'
        )


@require_auth
async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /watchlist command - manage stock watchlist"""
    try:
        user_id = context.user_data['user_id']
        preference_manager = context.bot_data['preference_manager']

        # Get current watchlist
        prefs = await preference_manager.get_preferences(user_id)
        watchlist = prefs.get('watchlist', [])

        # If no arguments, show current watchlist
        if not context.args:
            if not watchlist:
                message = """
📋 *YOUR WATCHLIST*

Your watchlist is empty.

*Add stocks:*
`/watchlist add <STOCK_CODE>`

*Example:*
`/watchlist add BBCA`
`/watchlist add BMRI TLKM ASII`
                """.strip()
            else:
                watchlist_text = ", ".join(watchlist)
                message = f"""
📋 *YOUR WATCHLIST*

*Stocks ({len(watchlist)}):*
{watchlist_text}

*Commands:*
• `/watchlist add <STOCK>` - Add stocks
• `/watchlist remove <STOCK>` - Remove stocks
• `/watchlist clear` - Clear all
• `/watchlist signals` - Get signals for watchlist

*Example:*
`/watchlist add UNVR`
`/watchlist remove BBCA`
                """.strip()

            await update.message.reply_text(message, parse_mode='Markdown')
            return

        # Parse subcommand
        subcommand = context.args[0].lower()

        if subcommand == 'add':
            # Add stocks to watchlist
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Please specify at least one stock code\n\n"
                    "Example: `/watchlist add BBCA BMRI`",
                    parse_mode='Markdown'
                )
                return

            stocks = [s.upper() for s in context.args[1:]]
            added = []
            already_exists = []

            for stock in stocks:
                try:
                    await preference_manager.add_to_watchlist(user_id, stock)
                    added.append(stock)
                except ValueError:
                    already_exists.append(stock)

            message_parts = []

            if added:
                message_parts.append(f"✅ Added to watchlist: {', '.join(added)}")

            if already_exists:
                message_parts.append(f"ℹ️ Already in watchlist: {', '.join(already_exists)}")

            # Get updated watchlist count
            prefs = await preference_manager.get_preferences(user_id)
            watchlist = prefs.get('watchlist', [])
            message_parts.append(f"\n📋 Total stocks in watchlist: {len(watchlist)}")

            await update.message.reply_text("\n\n".join(message_parts), parse_mode='Markdown')

        elif subcommand == 'remove':
            # Remove stocks from watchlist
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Please specify at least one stock code\n\n"
                    "Example: `/watchlist remove BBCA`",
                    parse_mode='Markdown'
                )
                return

            stocks = [s.upper() for s in context.args[1:]]
            removed = []
            not_found = []

            for stock in stocks:
                try:
                    await preference_manager.remove_from_watchlist(user_id, stock)
                    removed.append(stock)
                except ValueError:
                    not_found.append(stock)

            message_parts = []

            if removed:
                message_parts.append(f"✅ Removed from watchlist: {', '.join(removed)}")

            if not_found:
                message_parts.append(f"ℹ️ Not in watchlist: {', '.join(not_found)}")

            # Get updated watchlist count
            prefs = await preference_manager.get_preferences(user_id)
            watchlist = prefs.get('watchlist', [])
            message_parts.append(f"\n📋 Total stocks in watchlist: {len(watchlist)}")

            await update.message.reply_text("\n\n".join(message_parts), parse_mode='Markdown')

        elif subcommand == 'clear':
            # Clear entire watchlist
            if not watchlist:
                await update.message.reply_text(
                    "ℹ️ Your watchlist is already empty",
                    parse_mode='Markdown'
                )
                return

            await preference_manager.clear_watchlist(user_id)

            await update.message.reply_text(
                "✅ Watchlist cleared successfully",
                parse_mode='Markdown'
            )

        elif subcommand == 'signals':
            # Get signals for watchlist stocks
            if not watchlist:
                await update.message.reply_text(
                    "ℹ️ Your watchlist is empty. Add stocks first using:\n"
                    "`/watchlist add <STOCK_CODE>`",
                    parse_mode='Markdown'
                )
                return

            # Get daily signals
            signal_service = context.bot_data['signal_service']
            all_signals = await signal_service.get_daily_signals()

            # Filter signals for watchlist stocks
            watchlist_signals = [
                s for s in all_signals
                if s.get('stock_code') in watchlist
            ]

            if not watchlist_signals:
                await update.message.reply_text(
                    "ℹ️ No signals found for your watchlist stocks today",
                    parse_mode='Markdown'
                )
                return

            # Format signals
            signals_text = []
            for signal in watchlist_signals[:10]:  # Limit to 10
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
📋 *WATCHLIST SIGNALS*

{chr(10).join(signals_text)}

Use `/signals <STOCK>` for detailed signal info
            """.strip()

            await update.message.reply_text(message, parse_mode='Markdown')

        else:
            await update.message.reply_text(
                "❌ Unknown subcommand\n\n"
                "Use: `/watchlist add`, `/watchlist remove`, `/watchlist clear`, or `/watchlist signals`",
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error in /watchlist command: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again.",
            parse_mode='Markdown'
        )
