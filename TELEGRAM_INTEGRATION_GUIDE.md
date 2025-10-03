# Telegram Bot Integration Guide

## How to Integrate Telegram Bot with FastAPI

This guide shows you how to integrate the Telegram bot service with your existing FastAPI application.

## Step 1: Update main.py

Add the following changes to `src/api/main.py`:

### 1.1 Add Import Statements (after line 28)

```python
# Add these imports after existing imports
from src.api.telegram_integration import (
    initialize_telegram_bot,
    shutdown_telegram_bot,
    register_telegram_routes
)
```

### 1.2 Add Global Telegram Bot Variable (after line 41)

```python
# Add this after the existing global variables
telegram_bot: TelegramBotService = None
```

### 1.3 Update Lifespan Function (modify lines 44-75)

Replace the existing lifespan function with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global alert_engine, signal_service, risk_monitor, db_manager, telegram_bot

    # Startup
    logger.info("Starting Indonesian Quantitative Trading Alert System...")

    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()

    # Initialize services
    alert_engine = AlertEngine(db_manager)
    signal_service = SignalService(db_manager)
    risk_monitor = RiskMonitor(db_manager)

    # Start background tasks
    await alert_engine.initialize()
    await risk_monitor.start_monitoring()

    # Initialize Telegram bot
    telegram_bot = await initialize_telegram_bot(
        db_manager=db_manager,
        signal_service=signal_service,
        alert_engine=alert_engine
    )

    logger.info("Alert system initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down alert system...")

    # Stop Telegram bot first
    if telegram_bot:
        await shutdown_telegram_bot()

    if risk_monitor:
        await risk_monitor.stop_monitoring()
    if db_manager:
        await db_manager.close()
```

### 1.4 Register Telegram Routes (after app initialization, around line 98)

Add this after the middleware setup:

```python
# Register Telegram routes
register_telegram_routes(app)
```

### 1.5 Update Health Check to Include Telegram (modify lines 116-147)

Add Telegram health check to the detailed health endpoint:

```python
@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with service status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }

    # Check database connection
    try:
        await db_manager.health_check()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check alert engine
    if alert_engine and alert_engine.is_running:
        health_status["services"]["alert_engine"] = "healthy"
    else:
        health_status["services"]["alert_engine"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check risk monitor
    if risk_monitor and risk_monitor.is_monitoring:
        health_status["services"]["risk_monitor"] = "healthy"
    else:
        health_status["services"]["risk_monitor"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Telegram bot (NEW)
    if telegram_bot:
        try:
            bot_info = await telegram_bot.application.bot.get_me()
            health_status["services"]["telegram_bot"] = "healthy"
        except Exception as e:
            health_status["services"]["telegram_bot"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["telegram_bot"] = "disabled"

    return health_status
```

## Step 2: Update config.py

Add the following configuration variables to `src/api/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Telegram Bot Settings
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""  # Leave empty for polling mode
    WEB_APP_URL: str = "http://localhost:3000"  # Frontend URL for auth

    # ... rest of settings ...
```

## Step 3: Update .env File

Add these variables to your `.env` file:

```env
# Telegram Bot Configuration
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_WEBHOOK_URL=  # Leave empty for polling, or set to https://yourdomain.com/telegram/webhook
WEB_APP_URL=http://localhost:3000
```

## Step 4: Run Database Migration

Execute the database migration to create Telegram tables:

```bash
# Using psql
psql -U postgres -d project_aurum -f migrations/versions/001_telegram_bot_schema.sql

# Or using your migration tool
python -m alembic upgrade head
```

## Step 5: Get Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token provided
5. Add the token to your `.env` file

## Step 6: Test the Integration

### 6.1 Start the Application

```bash
# Start FastAPI
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6.2 Check Bot Status

```bash
# Check if bot is running
curl http://localhost:8000/telegram/status
```

Expected response:
```json
{
  "enabled": true,
  "status": "running",
  "mode": "polling",
  "bot_info": {
    "id": 123456789,
    "username": "your_bot_username",
    "name": "Your Bot Name"
  },
  "statistics": {
    "total_users": 0,
    "active_users_24h": 0,
    "total_commands_24h": 0,
    "avg_response_time_ms": 0
  }
}
```

### 6.3 Test the Bot

1. Open Telegram
2. Search for your bot by username
3. Send `/start` command
4. You should receive a welcome message with authentication link

## Step 7: Frontend Integration (Optional)

To complete the authentication flow, add this to your frontend:

```typescript
// Handle Telegram auth callback
const handleTelegramAuth = async (token: string) => {
  const response = await fetch('http://localhost:8000/telegram/auth/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token: token,
      user_id: currentUser.id
    })
  });

  const result = await response.json();

  if (result.status === 'success') {
    alert('Telegram linked successfully!');
  }
};

// Parse URL params for token
const urlParams = new URLSearchParams(window.location.search);
const authToken = urlParams.get('token');

if (authToken && currentUser) {
  handleTelegramAuth(authToken);
}
```

## Complete Integration Checklist

- [ ] Update `main.py` with Telegram imports and initialization
- [ ] Update `config.py` with Telegram settings
- [ ] Add Telegram configuration to `.env`
- [ ] Run database migration
- [ ] Get bot token from BotFather
- [ ] Start FastAPI application
- [ ] Test bot with `/telegram/status` endpoint
- [ ] Test bot in Telegram with `/start` command
- [ ] (Optional) Implement frontend auth flow
- [ ] (Optional) Set up webhook for production

## Production Deployment

### Webhook Mode (Recommended for Production)

1. Set up HTTPS domain with SSL certificate
2. Configure webhook URL in `.env`:
   ```env
   TELEGRAM_WEBHOOK_URL=https://yourdomain.com/telegram/webhook
   ```

3. The bot will automatically switch to webhook mode

4. Telegram will send updates to your webhook endpoint instead of polling

### Polling Mode (Development/Testing)

Leave `TELEGRAM_WEBHOOK_URL` empty to use polling mode. The bot will continuously poll Telegram for updates.

## Troubleshooting

### Bot Not Responding

1. Check if `TELEGRAM_ENABLED=true` in `.env`
2. Verify bot token is correct
3. Check logs for errors: `tail -f logs/app.log`
4. Verify database migration ran successfully
5. Check `/telegram/status` endpoint

### Authentication Not Working

1. Verify `WEB_APP_URL` is correct in `.env`
2. Check that frontend can reach the API
3. Verify database migration created `telegram_auth_tokens` table
4. Check browser console for errors

### Commands Not Working

1. Verify user is authenticated (`/start` → click auth link → login on web)
2. Check user permissions in database
3. Verify services are initialized (check `/health/detailed`)
4. Check command logs in `bot_command_log` table

### Performance Issues

1. Switch to webhook mode for production
2. Increase database connection pool size
3. Enable Redis caching for responses
4. Check response time metrics in `/telegram/status`

## Advanced Configuration

### Custom Command Prefix

Currently uses `/` prefix. To change:

```python
# In telegram_bot_service.py
application.add_handler(CommandHandler("signals", cmd_signals, filters=...))
```

### Rate Limit Customization

Adjust rate limits in `telegram_bot_service.py`:

```python
# General commands: 60/min
# Signal queries: 100/hour
# Portfolio updates: 10/min
```

### Custom Alert Routing

Modify `send_signal_alerts_via_telegram()` in `telegram_integration.py` to customize which users receive which alerts.

## Security Best Practices

1. ✅ Never commit bot token to git
2. ✅ Use environment variables for sensitive data
3. ✅ Implement rate limiting (already done)
4. ✅ Validate all user inputs (already done)
5. ✅ Use HTTPS for webhooks in production
6. ✅ Regularly rotate bot tokens
7. ✅ Monitor for unusual activity
8. ✅ Implement audit logging (already done)

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log`
2. Review bot command logs: `SELECT * FROM bot_command_log ORDER BY executed_at DESC LIMIT 100`
3. Check Telegram API status: https://core.telegram.org/
4. Review this documentation

---

**Integration Complete! 🎉**

Your Telegram bot is now fully integrated with your FastAPI application. Users can manage their portfolios, view signals, and receive alerts directly in Telegram.
