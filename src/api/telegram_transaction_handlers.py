"""
Telegram Transaction Handlers for Portfolio Management
Handles buy/sell/update commands with two-step confirmation
"""

import secrets
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from .database import DatabaseManager
from .signal_service import SignalService
from .telegram_auth import require_auth, require_permission

logger = logging.getLogger(__name__)


class TransactionManager:
    """Manages portfolio transactions with two-step confirmation"""

    def __init__(self, db_manager: DatabaseManager, signal_service: SignalService):
        self.db = db_manager
        self.signal_service = signal_service
        self.confirmation_timeout = 300  # 5 minutes

    async def create_pending_transaction(
        self,
        user_id: str,
        transaction_type: str,
        stock_code: str,
        quantity: int,
        price: float,
        meta_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a pending transaction requiring confirmation"""
        try:
            # Generate confirmation code
            confirmation_code = self._generate_confirmation_code()

            # Calculate expiry
            expires_at = datetime.now() + timedelta(seconds=self.confirmation_timeout)

            # Save to database
            query = """
                INSERT INTO pending_transactions (
                    user_id, transaction_type, stock_code, quantity, price,
                    confirmation_code, expires_at, meta_data
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, confirmation_code, expires_at
            """

            result = await self.db.fetch_one(
                query,
                user_id, transaction_type, stock_code, quantity, price,
                confirmation_code, expires_at, meta_data or {}
            )

            return {
                'transaction_id': result['id'],
                'confirmation_code': confirmation_code,
                'expires_at': expires_at,
                'type': transaction_type,
                'stock_code': stock_code,
                'quantity': quantity,
                'price': price
            }

        except Exception as e:
            logger.error(f"Failed to create pending transaction: {e}")
            raise

    async def confirm_transaction(
        self,
        user_id: str,
        confirmation_code: str
    ) -> Optional[Dict[str, Any]]:
        """Confirm and execute pending transaction"""
        try:
            # Get pending transaction
            query = """
                SELECT * FROM pending_transactions
                WHERE user_id = $1
                  AND confirmation_code = $2
                  AND status = 'pending'
                  AND expires_at > NOW()
            """

            transaction = await self.db.fetch_one(query, user_id, confirmation_code)

            if not transaction:
                return None

            # Execute transaction based on type
            if transaction['transaction_type'] == 'buy':
                result = await self._execute_buy(transaction)
            elif transaction['transaction_type'] == 'sell':
                result = await self._execute_sell(transaction)
            elif transaction['transaction_type'] == 'update':
                result = await self._execute_update(transaction)
            else:
                raise ValueError(f"Unknown transaction type: {transaction['transaction_type']}")

            # Mark transaction as confirmed
            update_query = """
                UPDATE pending_transactions
                SET status = 'confirmed', confirmed_at = NOW()
                WHERE id = $1
            """
            await self.db.execute(update_query, transaction['id'])

            return result

        except Exception as e:
            logger.error(f"Failed to confirm transaction: {e}")
            raise

    async def _execute_buy(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute buy transaction"""
        stock_code = transaction['stock_code']
        quantity = transaction['quantity']
        price = transaction['price']
        user_id = transaction['user_id']

        # Check if position exists
        check_query = """
            SELECT * FROM portfolio
            WHERE user_id = $1 AND stock_code = $2
        """
        existing_position = await self.db.fetch_one(check_query, user_id, stock_code)

        if existing_position:
            # Update existing position (average price calculation)
            old_quantity = existing_position['quantity']
            old_avg_price = existing_position['average_price']

            new_quantity = old_quantity + quantity
            new_avg_price = (
                (old_quantity * old_avg_price) + (quantity * price)
            ) / new_quantity

            update_query = """
                UPDATE portfolio
                SET quantity = $1,
                    average_price = $2,
                    last_updated = NOW()
                WHERE user_id = $3 AND stock_code = $4
                RETURNING *
            """

            position = await self.db.fetch_one(
                update_query,
                new_quantity, new_avg_price, user_id, stock_code
            )
        else:
            # Create new position
            # Get stock info
            stock_info = await self._get_stock_info(stock_code)

            insert_query = """
                INSERT INTO portfolio (
                    user_id, stock_code, quantity, average_price,
                    current_price, sector, market_value, last_updated
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                RETURNING *
            """

            market_value = quantity * price

            position = await self.db.fetch_one(
                insert_query,
                user_id, stock_code, quantity, price,
                price, stock_info.get('sector', 'Unknown'), market_value
            )

        return {
            'action': 'buy',
            'stock_code': stock_code,
            'quantity': quantity,
            'price': price,
            'total_cost': quantity * price,
            'new_position': position
        }

    async def _execute_sell(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute sell transaction"""
        stock_code = transaction['stock_code']
        quantity = transaction['quantity']
        price = transaction['price']
        user_id = transaction['user_id']

        # Get existing position
        query = """
            SELECT * FROM portfolio
            WHERE user_id = $1 AND stock_code = $2
        """
        position = await self.db.fetch_one(query, user_id, stock_code)

        if not position:
            raise ValueError(f"No position found for {stock_code}")

        if position['quantity'] < quantity:
            raise ValueError(f"Insufficient quantity. You have {position['quantity']}, trying to sell {quantity}")

        # Calculate realized P&L
        realized_pnl = (price - position['average_price']) * quantity

        if position['quantity'] == quantity:
            # Close entire position
            delete_query = """
                DELETE FROM portfolio
                WHERE user_id = $1 AND stock_code = $2
            """
            await self.db.execute(delete_query, user_id, stock_code)

            new_quantity = 0
        else:
            # Partial sell
            new_quantity = position['quantity'] - quantity

            update_query = """
                UPDATE portfolio
                SET quantity = $1,
                    last_updated = NOW()
                WHERE user_id = $2 AND stock_code = $3
                RETURNING *
            """

            position = await self.db.fetch_one(
                update_query,
                new_quantity, user_id, stock_code
            )

        return {
            'action': 'sell',
            'stock_code': stock_code,
            'quantity': quantity,
            'price': price,
            'total_proceeds': quantity * price,
            'realized_pnl': realized_pnl,
            'remaining_quantity': new_quantity
        }

    async def _execute_update(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute position update"""
        stock_code = transaction['stock_code']
        new_quantity = transaction['quantity']
        user_id = transaction['user_id']

        update_query = """
            UPDATE portfolio
            SET quantity = $1,
                last_updated = NOW()
            WHERE user_id = $2 AND stock_code = $3
            RETURNING *
        """

        position = await self.db.fetch_one(
            update_query,
            new_quantity, user_id, stock_code
        )

        if not position:
            raise ValueError(f"No position found for {stock_code}")

        return {
            'action': 'update',
            'stock_code': stock_code,
            'new_quantity': new_quantity,
            'position': position
        }

    async def _get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """Get stock information"""
        # Try to get from recent signals
        signals = await self.signal_service.get_daily_signals()

        for signal in signals:
            if signal.get('stock_code') == stock_code:
                return {
                    'sector': signal.get('sector', 'Unknown'),
                    'current_price': signal.get('current_price')
                }

        # Default if not found
        return {
            'sector': 'Unknown',
            'current_price': None
        }

    def _generate_confirmation_code(self) -> str:
        """Generate unique confirmation code"""
        # Generate random bytes and hash
        random_bytes = secrets.token_bytes(16)
        hash_obj = hashlib.sha256(random_bytes)
        # Take first 6 characters of hex digest
        return hash_obj.hexdigest()[:6].upper()


# Command Handlers

@require_auth
@require_permission('portfolio.modify')
async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command"""
    try:
        user_id = context.user_data['user_id']

        # Parse arguments: /buy <STOCK> <QUANTITY> <PRICE>
        if len(context.args) != 3:
            await update.message.reply_text(
                "❌ *Invalid format*\n\n"
                "Usage: `/buy <STOCK_CODE> <QUANTITY> <PRICE>`\n\n"
                "Example: `/buy BBCA 1000 4500`\n"
                "This will buy 1000 shares of BBCA at IDR 4500 per share",
                parse_mode='Markdown'
            )
            return

        stock_code = context.args[0].upper()

        try:
            quantity = int(context.args[1])
            price = float(context.args[2])
        except ValueError:
            await update.message.reply_text(
                "❌ Quantity must be an integer and price must be a number",
                parse_mode='Markdown'
            )
            return

        if quantity <= 0 or price <= 0:
            await update.message.reply_text(
                "❌ Quantity and price must be positive numbers",
                parse_mode='Markdown'
            )
            return

        # Create pending transaction
        transaction_manager = context.bot_data['transaction_manager']

        pending = await transaction_manager.create_pending_transaction(
            user_id=user_id,
            transaction_type='buy',
            stock_code=stock_code,
            quantity=quantity,
            price=price
        )

        # Calculate total cost
        total_cost = quantity * price

        # Create confirmation message
        message = f"""
💰 *BUY ORDER CONFIRMATION*

📊 *Stock:* {stock_code}
🔢 *Quantity:* {quantity:,} shares
💵 *Price:* IDR {price:,.2f}
💰 *Total Cost:* IDR {total_cost:,.2f}

⏰ *Expires in:* 5 minutes

To confirm this transaction, reply with:
`/confirm {pending['confirmation_code']}`

To cancel, just ignore this message or use /cancel
        """.strip()

        await update.message.reply_text(message, parse_mode='Markdown')

        # Log command
        await context.bot_data['db_manager'].log_bot_command(
            user_id=user_id,
            telegram_chat_id=update.effective_chat.id,
            command='buy',
            parameters={'stock_code': stock_code, 'quantity': quantity, 'price': price},
            response_status='pending_confirmation'
        )

    except Exception as e:
        logger.error(f"Error in /buy command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while creating your buy order. Please try again.",
            parse_mode='Markdown'
        )


@require_auth
@require_permission('portfolio.modify')
async def cmd_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sell command"""
    try:
        user_id = context.user_data['user_id']

        # Parse arguments: /sell <STOCK> <QUANTITY> <PRICE>
        if len(context.args) != 3:
            await update.message.reply_text(
                "❌ *Invalid format*\n\n"
                "Usage: `/sell <STOCK_CODE> <QUANTITY> <PRICE>`\n\n"
                "Example: `/sell BBCA 500 4600`\n"
                "This will sell 500 shares of BBCA at IDR 4600 per share",
                parse_mode='Markdown'
            )
            return

        stock_code = context.args[0].upper()

        try:
            quantity = int(context.args[1])
            price = float(context.args[2])
        except ValueError:
            await update.message.reply_text(
                "❌ Quantity must be an integer and price must be a number",
                parse_mode='Markdown'
            )
            return

        if quantity <= 0 or price <= 0:
            await update.message.reply_text(
                "❌ Quantity and price must be positive numbers",
                parse_mode='Markdown'
            )
            return

        # Check if user has the position
        db_manager = context.bot_data['db_manager']
        check_query = """
            SELECT quantity FROM portfolio
            WHERE user_id = $1 AND stock_code = $2
        """
        position = await db_manager.fetch_one(check_query, user_id, stock_code)

        if not position:
            await update.message.reply_text(
                f"❌ You don't have any position in {stock_code}",
                parse_mode='Markdown'
            )
            return

        if position['quantity'] < quantity:
            await update.message.reply_text(
                f"❌ Insufficient quantity\n\n"
                f"You have: {position['quantity']:,} shares\n"
                f"Trying to sell: {quantity:,} shares",
                parse_mode='Markdown'
            )
            return

        # Create pending transaction
        transaction_manager = context.bot_data['transaction_manager']

        pending = await transaction_manager.create_pending_transaction(
            user_id=user_id,
            transaction_type='sell',
            stock_code=stock_code,
            quantity=quantity,
            price=price
        )

        # Calculate total proceeds
        total_proceeds = quantity * price

        # Create confirmation message
        message = f"""
📉 *SELL ORDER CONFIRMATION*

📊 *Stock:* {stock_code}
🔢 *Quantity:* {quantity:,} shares
💵 *Price:* IDR {price:,.2f}
💰 *Total Proceeds:* IDR {total_proceeds:,.2f}

⏰ *Expires in:* 5 minutes

To confirm this transaction, reply with:
`/confirm {pending['confirmation_code']}`

To cancel, just ignore this message or use /cancel
        """.strip()

        await update.message.reply_text(message, parse_mode='Markdown')

        # Log command
        await db_manager.log_bot_command(
            user_id=user_id,
            telegram_chat_id=update.effective_chat.id,
            command='sell',
            parameters={'stock_code': stock_code, 'quantity': quantity, 'price': price},
            response_status='pending_confirmation'
        )

    except Exception as e:
        logger.error(f"Error in /sell command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while creating your sell order. Please try again.",
            parse_mode='Markdown'
        )


@require_auth
async def cmd_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /confirm command"""
    try:
        user_id = context.user_data['user_id']

        # Parse confirmation code
        if len(context.args) != 1:
            await update.message.reply_text(
                "❌ *Invalid format*\n\n"
                "Usage: `/confirm <CODE>`\n\n"
                "Example: `/confirm ABC123`",
                parse_mode='Markdown'
            )
            return

        confirmation_code = context.args[0].upper()

        # Confirm transaction
        transaction_manager = context.bot_data['transaction_manager']
        result = await transaction_manager.confirm_transaction(user_id, confirmation_code)

        if not result:
            await update.message.reply_text(
                "❌ *Invalid or expired confirmation code*\n\n"
                "The transaction may have already been confirmed or expired.\n"
                "Please create a new order if needed.",
                parse_mode='Markdown'
            )
            return

        # Format success message based on action type
        if result['action'] == 'buy':
            message = f"""
✅ *BUY ORDER EXECUTED*

📊 *Stock:* {result['stock_code']}
🔢 *Quantity:* {result['quantity']:,} shares
💵 *Price:* IDR {result['price']:,.2f}
💰 *Total Cost:* IDR {result['total_cost']:,.2f}

Your position has been updated successfully!
Use /portfolio to see your updated holdings.
            """.strip()

        elif result['action'] == 'sell':
            pnl_emoji = "📈" if result['realized_pnl'] >= 0 else "📉"
            pnl_color = "gain" if result['realized_pnl'] >= 0 else "loss"

            message = f"""
✅ *SELL ORDER EXECUTED*

📊 *Stock:* {result['stock_code']}
🔢 *Quantity:* {result['quantity']:,} shares
💵 *Price:* IDR {result['price']:,.2f}
💰 *Total Proceeds:* IDR {result['total_proceeds']:,.2f}

{pnl_emoji} *Realized P&L:* IDR {result['realized_pnl']:,.2f}
📦 *Remaining:* {result['remaining_quantity']:,} shares

Use /portfolio to see your updated holdings.
            """.strip()

        else:
            message = f"""
✅ *POSITION UPDATED*

📊 *Stock:* {result['stock_code']}
🔢 *New Quantity:* {result['new_quantity']:,} shares

Use /portfolio to see your updated holdings.
            """.strip()

        await update.message.reply_text(message, parse_mode='Markdown')

        # Log command
        await context.bot_data['db_manager'].log_bot_command(
            user_id=user_id,
            telegram_chat_id=update.effective_chat.id,
            command='confirm',
            parameters={'confirmation_code': confirmation_code},
            response_status='success'
        )

    except ValueError as e:
        logger.warning(f"Validation error in /confirm: {e}")
        await update.message.reply_text(
            f"❌ {str(e)}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in /confirm command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while confirming your transaction. Please try again.",
            parse_mode='Markdown'
        )


@require_auth
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command - cancel pending transactions"""
    try:
        user_id = context.user_data['user_id']

        # Cancel all pending transactions for this user
        query = """
            UPDATE pending_transactions
            SET status = 'cancelled'
            WHERE user_id = $1 AND status = 'pending'
            RETURNING stock_code, transaction_type, quantity
        """

        cancelled = await context.bot_data['db_manager'].fetch_all(query, user_id)

        if not cancelled:
            await update.message.reply_text(
                "ℹ️ You don't have any pending transactions",
                parse_mode='Markdown'
            )
            return

        # Format cancelled transactions
        cancelled_list = "\n".join([
            f"• {t['transaction_type'].upper()} {t['quantity']:,} shares of {t['stock_code']}"
            for t in cancelled
        ])

        message = f"""
✅ *TRANSACTIONS CANCELLED*

The following pending transactions have been cancelled:

{cancelled_list}

You can create new orders anytime using /buy or /sell
        """.strip()

        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in /cancel command: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again.",
            parse_mode='Markdown'
        )


@require_auth
async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pending command - show pending transactions"""
    try:
        user_id = context.user_data['user_id']

        query = """
            SELECT * FROM pending_transactions
            WHERE user_id = $1
              AND status = 'pending'
              AND expires_at > NOW()
            ORDER BY created_at DESC
        """

        pending = await context.bot_data['db_manager'].fetch_all(query, user_id)

        if not pending:
            await update.message.reply_text(
                "ℹ️ You don't have any pending transactions",
                parse_mode='Markdown'
            )
            return

        # Format pending transactions
        transactions_text = []
        for t in pending:
            type_emoji = "💰" if t['transaction_type'] == 'buy' else "📉"
            total = t['quantity'] * t['price']

            transactions_text.append(
                f"{type_emoji} *{t['transaction_type'].upper()}* {t['stock_code']}\n"
                f"   Quantity: {t['quantity']:,} @ IDR {t['price']:,.2f}\n"
                f"   Total: IDR {total:,.2f}\n"
                f"   Code: `{t['confirmation_code']}`\n"
                f"   Expires: {t['expires_at'].strftime('%H:%M:%S')}"
            )

        message = f"""
⏳ *PENDING TRANSACTIONS*

{chr(10).join(transactions_text)}

Use `/confirm <CODE>` to confirm any transaction
Use `/cancel` to cancel all pending transactions
        """.strip()

        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in /pending command: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again.",
            parse_mode='Markdown'
        )
