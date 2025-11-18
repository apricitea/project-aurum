# Telegram Bot Implementation Guide

## Overview

This implementation adds a comprehensive Telegram bot service to the Indonesian Quantitative Trading System, allowing users to interactively query signals, manage portfolios, and receive alerts through Telegram.

## Files Created

### 1. `src/api/telegram_auth.py`
**Purpose**: Authentication and authorization system for Telegram bot

**Key Features**:
- Token-based authentication linking Telegram accounts to user accounts
- Session management with Redis caching
- Permission-based access control
- Rate limiting for authentication attempts
- Comprehensive audit logging
- Decorators for protecting command handlers

**Key Classes**:
- `TelegramAuthManager`: Main authentication manager
  - `generate_auth_token()`: Generate authentication tokens
  - `verify_auth_token()`: Verify and link accounts
  - `get_user_by_chat_id()`: Retrieve user information
  - `check_permission()`: Check user permissions
  - `log_command_execution()`: Audit trail logging

**Decorators**:
- `@require_auth`: Require authentication for commands
- `@require_permission(permission)`: Require specific permissions

### 2. `src/api/telegram_handlers.py`
**Purpose**: Command handlers for all bot interactions

**Key Features**:
- All command handlers with proper error handling
- Rich formatting with emojis and visual indicators
- Inline keyboards for interactive navigation
- Integration with SignalService, DatabaseManager, and AlertEngine

**Commands Implemented**:

#### Authentication Commands
- `/start` - Initialize bot and authenticate user
- `/help` - Show available commands
- `/ping` - Check bot status
- `/logout` - Unlink Telegram account

#### Signal Commands
- `/signals` - Get today's top 10 trading signals
- `/signals <STOCK>` - Get signal for specific stock (e.g., `/signals BBCA`)

#### Portfolio Commands
- `/portfolio` - View portfolio summary
- `/positions` - View detailed positions

#### Risk Commands
- `/risk` - View risk metrics and active alerts

#### Market Commands
- `/market` - Get current market status

**Key Classes**:
- `TelegramCommandHandlers`: All command handler implementations

### 3. `src/api/telegram_bot_service.py`
**Purpose**: Main bot service with lifecycle management

**Key Features**:
- Bot initialization and lifecycle management
- Support for both webhook and polling modes
- Rate limiting per user (60 req/min general, 100 req/hour signals)
- Global error handling
- Alert broadcasting to all users
- Health check endpoint

**Key Classes**:
- `TelegramBotService`: Main bot service
  - `initialize()`: Initialize bot service
  - `start()`: Start bot in polling or webhook mode
  - `stop()`: Gracefully stop bot
  - `send_alert_to_user()`: Send alert to specific user
  - `broadcast_alert()`: Broadcast to all users
  - `health_check()`: Service health status

- `RateLimiter`: Rate limiting for commands
  - `check_rate_limit()`: Check if request allowed
  - `get_remaining_requests()`: Get rate limit status

### 4. `src/api/migrations/add_telegram_bot_tables.sql`
**Purpose**: Database schema for Telegram bot functionality

**Tables Created**:

#### `telegram_auth_tokens`
Stores authentication tokens for linking Telegram accounts
- `token_hash`: SHA-256 hash of token
- `telegram_chat_id`: Telegram chat ID
- `telegram_username`: Telegram username
- `user_id`: Linked user ID
- `expires_at`: Token expiration time

#### `telegram_preferences`
Stores user preferences for bot notifications
- `user_id`: User ID
- `alert_types`: Array of alert types to receive
- `signal_filter`: Filter for signals (all/buy_only/sell_only/high_confidence)
- `notification_hours`: Hours to receive notifications (WIB)
- `watchlist`: Array of stock codes
- `language`: Preferred language (id/en)
- `notifications_enabled`: Enable/disable notifications

#### `bot_command_log`
Audit log for all bot command executions
- `user_id`: User who executed command
- `telegram_chat_id`: Telegram chat ID
- `command`: Command name
- `parameters`: Command parameters (JSONB)
- `response_status`: success/error/unauthorized
- `response_time_ms`: Response time in milliseconds
- `error_message`: Error details if failed

#### `pending_transactions`
Stores pending transactions requiring 2-step confirmation (future use)
- `user_id`: User ID
- `transaction_type`: buy/sell/update
- `stock_code`: Stock code
- `quantity`: Transaction quantity
- `price`: Transaction price
- `confirmation_code`: Unique confirmation code
- `expires_at`: Transaction expiration time

**Additional Database Objects**:
- Indexes for performance optimization
- Triggers for automatic timestamp updates
- Functions for cleanup of expired records
- View `active_telegram_users` for active Telegram users

## Setup Instructions

### 1. Prerequisites

- PostgreSQL database (already configured)
- Redis server (already configured)
- Python 3.9+ (already installed)
- `python-telegram-bot` version 21.8 (already installed)

### 2. Database Migration

Run the migration to create necessary tables:

```bash
# Connect to your PostgreSQL database
psql -U postgres -d trading_system

# Run the migration
\i src/api/migrations/add_telegram_bot_tables.sql
```

### 3. Configuration

Add the following settings to your `.env` file or `src/api/config.py`:

```env
# Telegram Bot Configuration
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_WEBHOOK_URL=  # Optional: for webhook mode (e.g., https://yourdomain.com/telegram/webhook)
WEB_APP_URL=http://localhost:3000  # Your frontend URL for authentication

# Redis Configuration (if not already set)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Optional
```

### 4. Update config.py

Add these two lines to `src/api/config.py` after line 90:

```python
TELEGRAM_WEBHOOK_URL: str = ""
WEB_APP_URL: str = "http://localhost:3000"
```

### 5. Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the bot token provided
5. Add token to your `.env` file

### 6. Integration with Existing Code

The bot service integrates with existing services. Example integration:

```python
from src.api.database import DatabaseManager
from src.api.signal_service import SignalService
from src.api.alert_engine import AlertEngine
from src.api.telegram_bot_service import create_telegram_bot_service

# Initialize existing services
db_manager = DatabaseManager()
await db_manager.initialize()

signal_service = SignalService(db_manager)
await signal_service.initialize()

alert_engine = AlertEngine(db_manager)
await alert_engine.initialize()

# Create and start Telegram bot service
telegram_bot = await create_telegram_bot_service(
    db_manager,
    signal_service,
    alert_engine
)

# Start the bot
await telegram_bot.start()

# Bot is now running and accepting commands
```

### 7. FastAPI Integration (Optional)

Add bot service to your FastAPI application:

```python
from fastapi import FastAPI
from src.api.telegram_bot_service import TelegramBotService

app = FastAPI()
telegram_bot: Optional[TelegramBotService] = None

@app.on_event("startup")
async def startup():
    global telegram_bot
    # Initialize services...
    telegram_bot = await create_telegram_bot_service(
        db_manager, signal_service, alert_engine
    )
    await telegram_bot.start()

@app.on_event("shutdown")
async def shutdown():
    if telegram_bot:
        await telegram_bot.stop()

@app.get("/health/telegram")
async def telegram_health():
    if telegram_bot:
        return await telegram_bot.health_check()
    return {"status": "not_initialized"}
```

## Usage Flow

### 1. User Authentication Flow

1. User starts bot: `/start`
2. Bot generates authentication token and URL
3. User clicks URL, redirected to web app
4. User logs in with trading account credentials
5. Web app calls `auth_manager.verify_auth_token(token, user_id)`
6. Telegram account linked to user account
7. User can now use all bot commands

### 2. Querying Signals

```
User: /signals
Bot: Shows top 10 signals with confidence, price, position size
     Includes inline buttons to filter by BUY/SELL/High Confidence

User: /signals BBCA
Bot: Shows detailed signal for BBCA stock with technical/fundamental/sentiment scores
```

### 3. Checking Portfolio

```
User: /portfolio
Bot: Shows portfolio summary with total value, P&L, sector allocation

User: /positions
Bot: Shows detailed list of all positions with individual P&L
```

### 4. Risk Monitoring

```
User: /risk
Bot: Shows risk metrics, sector concentration, active alerts
```

## Security Features

### 1. Authentication
- Secure token-based authentication with SHA-256 hashing
- Tokens expire in 15 minutes
- Sessions cached in Redis for performance
- Sessions expire in 7 days

### 2. Rate Limiting
- General commands: 60 requests/minute
- Signal queries: 100 requests/hour
- Portfolio updates: 10 requests/minute
- Tracked per chat_id in Redis

### 3. Authorization
- Role-based access control (admin, trader, viewer)
- Permission-based command restrictions
- Audit logging for all commands

### 4. Error Handling
- Never expose internal errors to users
- Comprehensive error logging
- User-friendly error messages
- Automatic error recovery

## Monitoring & Logging

### 1. Command Audit Log

All commands are logged to `bot_command_log` table:
- User ID and chat ID
- Command and parameters
- Response status and time
- Error messages if failed

Query example:
```sql
SELECT command, COUNT(*) as usage_count,
       AVG(response_time_ms) as avg_response_time
FROM bot_command_log
WHERE executed_at > NOW() - INTERVAL '24 hours'
GROUP BY command
ORDER BY usage_count DESC;
```

### 2. Health Check

Monitor bot health:
```python
health = await telegram_bot.health_check()
# Returns:
# {
#   'service': 'telegram_bot',
#   'status': 'healthy',
#   'mode': 'polling',
#   'bot_initialized': True,
#   'redis_connected': True,
#   'bot_api_connected': True
# }
```

### 3. Metrics to Track

- Commands per user per day
- Average response time
- Error rate by command
- Authentication success rate
- Active users count

## Best Practices

### 1. Message Formatting

Use Markdown formatting for rich messages:
```python
message = f"""
*Bold Title*
• Bullet point
`Code or stock symbol`
[Link](https://example.com)
"""
await update.message.reply_text(message, parse_mode='Markdown')
```

### 2. Error Handling

Always wrap handlers in try-except:
```python
@require_auth
async def cmd_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = datetime.now()
    chat_id = update.effective_chat.id

    try:
        # Your command logic
        pass
    except Exception as e:
        logger.error(f"Error in command: {str(e)}")
        await update.message.reply_text("An error occurred...")
    finally:
        # Log command execution
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        await auth_manager.log_command_execution(
            chat_id, '/example', {}, 'success', response_time
        )
```

### 3. Rate Limiting

Commands are automatically rate limited by the middleware. To check rate limit status:
```python
limit_info = await rate_limiter.get_remaining_requests(chat_id, 'signals')
# Returns: {'limit': 100, 'remaining': 95, 'reset_in_seconds': 3456}
```

### 4. Broadcasting Alerts

Send alerts to all authenticated users:
```python
alert = {
    'alert_type': 'high_confidence_signal',
    'priority': 'high',
    'message': 'High confidence BUY signal for BBCA',
    'stock_code': 'BBCA',
    'created_at': datetime.now()
}

await telegram_bot.broadcast_alert(alert)
```

## Troubleshooting

### Bot not responding

1. Check bot is running:
```python
health = await telegram_bot.health_check()
```

2. Check Redis connection:
```bash
redis-cli ping
```

3. Check Telegram API:
```python
bot_info = await bot.get_me()
```

### Authentication failing

1. Check token hasn't expired (15 min expiry)
2. Verify web app can access database
3. Check Redis is caching sessions
4. Verify user exists and is active

### Rate limiting issues

1. Check Redis for rate limit keys:
```bash
redis-cli KEYS "rate_limit:*"
```

2. Clear rate limit for user:
```bash
redis-cli DEL "rate_limit:general:123456789"
```

### Database issues

1. Verify migration ran successfully:
```sql
SELECT COUNT(*) FROM telegram_auth_tokens;
```

2. Check indexes exist:
```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'bot_command_log';
```

## Future Enhancements

### Phase 2: Portfolio Updates (Ready for Implementation)
- `/buy <STOCK> <QTY> <PRICE>` - Initiate buy transaction
- `/sell <STOCK> <QTY> <PRICE>` - Initiate sell transaction
- `/confirm <CODE>` - Confirm pending transaction
- Two-step confirmation using `pending_transactions` table

### Phase 3: Advanced Features
- `/subscribe` - Manage alert preferences
- `/watchlist` - Manage personal watchlist
- `/performance` - Portfolio performance charts
- `/backtest` - Quick strategy backtests
- Multi-language support (Indonesian/English)

### Phase 4: Production Optimizations
- Webhook mode for lower latency
- Message queuing for high volume
- Advanced analytics dashboard
- Integration with broker APIs

## API Reference

### TelegramAuthManager

```python
# Generate authentication token
auth_data = await auth_manager.generate_auth_token(
    telegram_chat_id=123456789,
    telegram_username="john_trader"
)
# Returns: {'token': '...', 'auth_url': '...', 'expires_in_minutes': 15}

# Verify token and link account
success = await auth_manager.verify_auth_token(
    token="abc123...",
    user_id="uuid-here"
)
# Returns: True if successful

# Get user by chat ID
user = await auth_manager.get_user_by_chat_id(123456789)
# Returns: {'id': '...', 'username': '...', 'role': 'trader', ...}

# Check permission
has_perm = await auth_manager.check_permission(123456789, 'portfolio.modify')
# Returns: True if user has permission
```

### TelegramBotService

```python
# Initialize bot
bot = await create_telegram_bot_service(db_manager, signal_service, alert_engine)

# Start bot
await bot.start()

# Send alert to user
await bot.send_alert_to_user(
    chat_id=123456789,
    alert={'alert_type': 'high_confidence_signal', 'message': '...', ...}
)

# Broadcast alert
await bot.broadcast_alert(alert)

# Health check
health = await bot.health_check()

# Stop bot
await bot.stop()
```

## Support

For issues or questions:
1. Check logs: `logs/trading_system.log`
2. Review audit log: `SELECT * FROM bot_command_log ORDER BY executed_at DESC LIMIT 100;`
3. Check bot health: Call health_check endpoint
4. Verify configuration: Ensure all settings are correct

## License

This Telegram bot implementation is part of the Indonesian Quantitative Trading System.

---

**Implementation Status**: ✅ Complete - Ready for Testing
**Version**: 1.0.0
**Date**: October 2, 2025
**Python Version**: 3.9+
**Dependencies**: python-telegram-bot 21.8, aioredis, asyncpg
